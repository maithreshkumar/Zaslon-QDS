from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
for relative in ("shared/backend", "Alice/backend", "Bob/backend", "Attack/backend"):
    sys.path.insert(0, str(ROOT / relative))

TEST_DB_PATH = Path(tempfile.gettempdir()) / "zaslon-qds-tests.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH.as_posix()}")
os.environ["ZASLON_QUANTUM_ENGINE"] = "reference"
os.environ["ZASLON_EXECUTION_MODE"] = "direct"
os.environ["ZASLON_ALICE_API_KEY"] = "alice-test-key-000000000000000000000"
os.environ["ZASLON_BOB_API_KEY"] = "bob-test-key-00000000000000000000000"
os.environ["ZASLON_ATTACK_API_KEY"] = "attack-test-key-0000000000000000000"

import pytest

from zaslon_shared.config import settings
from zaslon_shared.db import Base, engine

@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)
