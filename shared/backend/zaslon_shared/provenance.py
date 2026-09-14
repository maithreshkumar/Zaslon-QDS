from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib import metadata
import json
import os
import platform
from pathlib import Path
import sys
from typing import Any


_PACKAGES = {
    "cudaq": "cuda-quantum",
    "qiskit": "qiskit",
    "qiskit_aer": "qiskit-aer",
    "sequence": "sequence",
    "numpy": "numpy",
    "scipy": "scipy",
    "fastapi": "fastapi",
}

_GENERATED_SOURCE_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    ".venv-wsl",
}


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def canonical_sha512(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha512(encoded).hexdigest()


@lru_cache(maxsize=1)
def _source_tree_sha512() -> str:
    """Digest active Python/application sources without including data or secrets."""

    root = Path(__file__).resolve().parents[3]
    digest = hashlib.sha512()
    found = False
    for relative_root in ("shared", "Alice", "Bob", "Attack", "scripts", "docker"):
        folder = root / relative_root
        if not folder.exists():
            continue
        for path in sorted(
            candidate for candidate in folder.rglob("*")
            if candidate.is_file()
            and not any(
                part in _GENERATED_SOURCE_PARTS or part.startswith(".venv")
                for part in candidate.parts
            )
            and candidate.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml", ".sh"}
        ):
            found = True
            relative = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            content = path.read_bytes()
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    return digest.hexdigest() if found else "SOURCE_TREE_UNAVAILABLE"


def runtime_provenance(
    *, component: str, seed: int, quantum: dict[str, Any]
) -> dict[str, Any]:
    """Return a machine-readable reproducibility manifest without host secrets."""

    manifest: dict[str, Any] = {
        "schema": "zaslon.reproducibility.v1",
        "component": component,
        "experiment_seed": seed,
        "protocol_implementation": "0.3.0-basis-aware-teleportation",
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "container_image": os.getenv("ZASLON_CONTAINER_IMAGE", "UNDECLARED"),
        "source_tree_sha512": _source_tree_sha512(),
        "dependencies": {name: _version(dist) for name, dist in _PACKAGES.items()},
        "quantum_execution": quantum,
        "randomness_policy": {
            "seeded_classical_selection": True,
            "quantum_measurements_from_engine": True,
            "python_hash_seed": os.getenv("PYTHONHASHSEED", "UNDECLARED"),
        },
    }
    manifest["manifest_sha512"] = canonical_sha512(manifest)
    return manifest
