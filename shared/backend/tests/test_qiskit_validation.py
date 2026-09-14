import importlib.util
import pytest

from zaslon_shared.quantum import (
    CudaQEngine, NoiseConfig, QiskitAerEngine, ReferenceStatevectorEngine,
    validate_qiskit_aer,
)


def test_qiskit_executes_ideal_computational_basis_teleportation():
    engine = QiskitAerEngine(seed=123)
    for bit in (0, 1):
        results = [engine.teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z"
        ) for _ in range(8)]
        assert all(result.bob_outcome == bit for result in results)
        assert engine.metadata.engine == "QISKIT_AER"


def test_qiskit_random_basis_intercept_resend_has_expected_disturbance():
    report = validate_qiskit_aer(shots=256, seed=2026)
    assert report["ideal"]["qber"] == 0.0
    assert 0.15 <= report["intercept_resend"]["qber"] <= 0.35
    assert report["passed"] is True


@pytest.mark.skipif(importlib.util.find_spec("cudaq") is None, reason="CUDA-Q not installed on this host")
def test_cudaq_executes_without_silent_fallback():
    engine = CudaQEngine(seed=7)
    result = engine.teleport_and_measure(bit=1, preparation_basis="Z", measurement_basis="Z")
    assert result.bob_outcome == 1
    assert engine.metadata.engine == "CUDA-Q"
    assert engine.metadata.fallback_used is False


def test_configured_measurement_noise_is_not_hidden_as_an_attack():
    engine = ReferenceStatevectorEngine(seed=99)
    result = engine.teleport_and_measure(
        bit=0, preparation_basis="Z", measurement_basis="Z",
        noise=NoiseConfig(measurement_error=1.0),
    )
    assert result.bob_outcome == 1


def test_invalid_noise_probability_is_rejected():
    with pytest.raises(ValueError):
        NoiseConfig(depolarizing=1.01)


@pytest.mark.skipif(importlib.util.find_spec("cudaq") is not None, reason="CUDA-Q is installed")
def test_selecting_missing_cudaq_fails_instead_of_falling_back():
    with pytest.raises(RuntimeError, match="explicitly selected"):
        CudaQEngine(seed=7)
