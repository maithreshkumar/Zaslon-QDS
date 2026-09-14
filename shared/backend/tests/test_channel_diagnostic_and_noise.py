from __future__ import annotations

import pytest

from zaslon_shared.quantum import (
    CudaQEngine,
    NoiseConfig,
    QiskitAerEngine,
    ReferenceStatevectorEngine,
    run_channel_diagnostic,
)


@pytest.mark.parametrize(
    ("operation", "z_min", "x_min"),
    [
        ("X", 0.99, 0.0),
        ("Z", 0.0, 0.99),
        ("Y", 0.99, 0.99),
    ],
)
def test_randomized_basis_diagnostic_observes_pauli_disturbance(
    operation: str, z_min: float, x_min: float
) -> None:
    result = run_channel_diagnostic(
        ReferenceStatevectorEngine(seed=901),
        shots_per_basis=64,
        master_seed=902,
        attack_strength=1.0,
        output_pauli=operation,  # type: ignore[arg-type]
    )
    assert result["production_signature_evidence_used"] is False
    assert result["production_signature_evidence_modified"] is False
    assert result["z_basis_error_rate"] >= z_min
    assert result["x_basis_error_rate"] >= x_min
    assert result["decision"] == "CHANNEL_DISTURBANCE_DETECTED"


def test_honest_channel_diagnostic_has_no_disturbance() -> None:
    result = run_channel_diagnostic(
        ReferenceStatevectorEngine(seed=903),
        shots_per_basis=64,
        master_seed=904,
    )
    assert result["z_basis_error_rate"] == 0.0
    assert result["x_basis_error_rate"] == 0.0
    assert result["decision"] == "NO_CHANNEL_DISTURBANCE_DETECTED"


def test_measurement_noise_affects_both_diagnostic_bases_at_configured_rate() -> None:
    result = run_channel_diagnostic(
        ReferenceStatevectorEngine(seed=905),
        shots_per_basis=2000,
        master_seed=906,
        noise=NoiseConfig(measurement_error=0.20),
    )
    assert 0.16 <= result["z_basis_error_rate"] <= 0.24
    assert 0.16 <= result["x_basis_error_rate"] <= 0.24


def _basis_rates(engine, noise: NoiseConfig) -> tuple[float, float]:
    result = run_channel_diagnostic(
        engine,
        shots_per_basis=512,
        master_seed=908,
        noise=noise,
        disturbance_threshold=1.0,
    )
    return result["z_basis_error_rate"], result["x_basis_error_rate"]


def test_reference_and_qiskit_share_combined_noise_semantics() -> None:
    noise = NoiseConfig(
        bit_flip=0.17,
        phase_flip=0.13,
        depolarizing=0.11,
        output_bit_flip=0.07,
        output_phase_flip=0.05,
        output_depolarizing=0.09,
        measurement_error=0.08,
    )
    reference = _basis_rates(ReferenceStatevectorEngine(seed=907), noise)
    qiskit = _basis_rates(QiskitAerEngine(seed=907), noise)
    assert abs(reference[0] - qiskit[0]) <= 0.08
    assert abs(reference[1] - qiskit[1]) <= 0.08


def test_cudaq_shares_combined_noise_semantics_when_available() -> None:
    try:
        cudaq_engine = CudaQEngine(seed=909)
    except (ImportError, RuntimeError):
        pytest.skip("CUDA-Q is tested in the configured WSL/Linux environment")
    noise = NoiseConfig(
        bit_flip=0.12,
        phase_flip=0.10,
        depolarizing=0.08,
        output_bit_flip=0.06,
        output_phase_flip=0.04,
        output_depolarizing=0.07,
        measurement_error=0.05,
    )
    reference = _basis_rates(ReferenceStatevectorEngine(seed=909), noise)
    cudaq_rates = _basis_rates(cudaq_engine, noise)
    assert abs(reference[0] - cudaq_rates[0]) <= 0.10
    assert abs(reference[1] - cudaq_rates[1]) <= 0.10

