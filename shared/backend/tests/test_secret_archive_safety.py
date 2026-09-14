import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _archive_module():
    path = ROOT / "scripts" / "create_source_archive.py"
    spec = importlib.util.spec_from_file_location("create_source_archive", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_archive_allowlist_excludes_secrets_databases_and_build_outputs() -> None:
    module = _archive_module()
    relative_paths = [path.relative_to(ROOT) for path in module.source_files()]
    serialized = "\n".join(path.as_posix() for path in relative_paths)
    assert ".env\n" not in serialized
    assert Path(".env.auth") not in relative_paths
    assert Path(".env.auth.example") in relative_paths
    assert ".env.local" not in serialized
    assert "zaslon_qds.db" not in serialized
    assert "/node_modules/" not in serialized
    assert "/dist/" not in serialized
    assert not any(path.suffix in {".db", ".sqlite", ".sqlite3"} for path in relative_paths)
    assert Path(".env.example") in relative_paths
