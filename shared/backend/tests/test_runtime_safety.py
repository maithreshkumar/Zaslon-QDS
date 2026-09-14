from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from zaslon_shared.quantum import CudaQEngine, QuantumExecutionMetadata, cross_validate_quantum_engines
from zaslon_shared.runtime import quantum_job_slot


ALICE_HEADERS = {"X-ZASLON-API-Key": os.environ["ZASLON_ALICE_API_KEY"]}


def test_health_is_read_only_and_checks_database_without_exposing_exception(monkeypatch) -> None:
    with TestClient(app) as client:
        monkeypatch.setattr(
            main_module,
            "database_readiness",
            lambda: False,
        )
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["database"].endswith(":unavailable")
        assert payload["quantum"]["health_check_mutates_configuration"] is False
        assert "error" not in payload["quantum"]


def test_quantum_admission_control_returns_429_with_retry_after() -> None:
    with TestClient(app) as client:
        with quantum_job_slot("test-holder"):
            response = client.post(
                "/api/v1/validate/qiskit",
                headers=ALICE_HEADERS,
                json={"shots": 32, "seed": 7},
            )
        assert response.status_code == 429
        assert response.headers["retry-after"] == "2"


def test_cross_validation_top_level_fails_when_primary_is_outside_tolerance(monkeypatch) -> None:
    import zaslon_shared.quantum as quantum

    class DummyEngine:
        metadata = QuantumExecutionMetadata(
            engine="DUMMY",
            target="test",
            gpu=False,
            fallback_used=False,
            fallback_reason=None,
        )

        def teleport_and_measure(self, **kwargs):
            bit = kwargs["bit"]
            return type("Result", (), {"bob_outcome": bit})()

    monkeypatch.setattr(quantum, "create_quantum_engine", lambda *_args, **_kwargs: DummyEngine())
    monkeypatch.setattr(
        quantum,
        "validate_qiskit_aer",
        lambda **_kwargs: {
            "validator": {"engine": "QISKIT_AER"},
            "ideal": {"qber": 0.0},
            "intercept_resend": {"qber": 0.25},
            "passed": True,
        },
    )
    report = cross_validate_quantum_engines(
        primary_engine_name="dummy", shots=32, seed=1, tolerance=0.01
    )
    assert report["passed"] is False
    assert report["comparison"]["within_configured_tolerance"] is False
    assert "statistical equivalence test" in report["comparison"]["interpretation"]


@pytest.mark.skipif(importlib.util.find_spec("cudaq") is None, reason="CUDA-Q runs in WSL/Linux")
def test_cudaq_concurrent_calls_are_serialized_and_correct() -> None:
    engines = [CudaQEngine(seed=261200), CudaQEngine(seed=261201)]

    def execute(index: int) -> int:
        bit = index & 1
        result = engines[index % 2].teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z"
        )
        return int(result.bob_outcome == bit)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(execute, range(16)))
    assert outcomes == [1] * 16

