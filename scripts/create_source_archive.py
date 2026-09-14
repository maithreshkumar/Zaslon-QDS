from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_FILES = {
    ".dockerignore",
    ".env.auth.example",
    ".env.example",
    ".gitignore",
    "BASELINE.md",
    "CUDA_VALIDATION_RESULTS.json",
    "FINAL_VALIDATION_RESULTS.json",
    "HARDENING_CHECKPOINT.md",
    "IMPLEMENTATION_AUDIT.md",
    "README.md",
    "SCIENTIFIC_HARDENING_REPORT.md",
    "SECURITY_MODEL.md",
    "START.md",
    "compose.yaml",
    "design-system.css",
    "package-lock.json",
    "package.json",
    "requirements.txt",
    "requirements-api.txt",
    "requirements-worker.txt",
    "walkthrough.md",
}
ALLOWED_ROOT_DIRECTORIES = {"Alice", "Attack", "Bob", "docker", "scripts", "shared"}
DENIED_NAMES = {
    ".env",
    ".env.auth",
    ".env.local",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".venv-wsl",
    "release",
}
DENIED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".tsbuildinfo"}


def source_files() -> list[Path]:
    files: list[Path] = []
    for filename in sorted(ALLOWED_ROOT_FILES):
        candidate = ROOT / filename
        if candidate.is_file():
            files.append(candidate)
    for directory_name in sorted(ALLOWED_ROOT_DIRECTORIES):
        directory = ROOT / directory_name
        for candidate in directory.rglob("*"):
            relative = candidate.relative_to(ROOT)
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if any(part in DENIED_NAMES for part in relative.parts):
                continue
            if candidate.suffix.lower() in DENIED_SUFFIXES:
                continue
            files.append(candidate)
    for candidate in files:
        relative = candidate.relative_to(ROOT)
        if any(part in DENIED_NAMES for part in relative.parts):
            raise RuntimeError(f"Sensitive path reached archive allowlist: {relative}")
        if candidate.suffix.lower() in DENIED_SUFFIXES:
            raise RuntimeError(f"Database/cache file reached archive allowlist: {relative}")
    return sorted(set(files))


def create_archive() -> Path:
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = release / f"zaslon-qds-source-{timestamp}.zip"
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in source_files():
            archive.write(source, source.relative_to(ROOT).as_posix())
    return destination


if __name__ == "__main__":
    print(create_archive())
