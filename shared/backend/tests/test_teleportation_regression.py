import importlib.util

import pytest

from zaslon_shared.quantum import CudaQEngine, QiskitAerEngine, ReferenceStatevectorEngine


@pytest.mark.parametrize("engine_type", [ReferenceStatevectorEngine, QiskitAerEngine])
def test_all_four_bell_measurement_outcomes_apply_the_correct_correction(engine_type):
    engine = engine_type(seed=260831)
    seen: set[tuple[int, int]] = set()

    for _ in range(256):
        result = engine.teleport_and_measure(
            bit=1,
            preparation_basis="X",
            measurement_basis="X",
        )
        seen.add(result.bell_bits)
        assert result.bob_outcome == 1
        if result.fidelity is not None:
            assert result.fidelity > 1 - 1e-12

    assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}


@pytest.mark.parametrize(
    ("pauli", "basis"),
    [
        ("X", "Z"),
        ("Z", "X"),
        ("Y", "Z"),
        ("Y", "X"),
    ],
)
def test_pauli_disturbance_is_visible_in_a_sensitive_basis(pauli, basis):
    engine = ReferenceStatevectorEngine(seed=260832)
    results = [
        engine.teleport_and_measure(
            bit=0,
            preparation_basis=basis,
            measurement_basis=basis,
            output_pauli=pauli,
        )
        for _ in range(32)
    ]

    assert all(result.bob_outcome == 1 for result in results)
    assert all(result.fidelity is not None and result.fidelity < 1e-12 for result in results)


def test_z_phase_is_invisible_in_z_basis_and_must_not_be_claimed_detectable_there():
    engine = ReferenceStatevectorEngine(seed=260833)
    results = [
        engine.teleport_and_measure(
            bit=0,
            preparation_basis="Z",
            measurement_basis="Z",
            output_pauli="Z",
        )
        for _ in range(32)
    ]

    assert all(result.bob_outcome == 0 for result in results)


def test_staged_receiver_correction_is_driven_by_delivered_network_bits():
    engine = ReferenceStatevectorEngine(seed=260834)
    pending = engine.begin_networked_teleportation(
        bit=0,
        preparation_basis="X",
        measurement_basis="X",
    )
    honest = engine.complete_networked_teleportation(
        pending,
        delivered_bell_bits=pending.bell_bits,
    )
    phase_tampered = engine.complete_networked_teleportation(
        pending,
        delivered_bell_bits=(pending.bell_bits[0] ^ 1, pending.bell_bits[1]),
    )

    assert honest.bob_outcome == 0
    assert phase_tampered.bob_outcome == 1
    assert honest.fidelity is not None and honest.fidelity > 1 - 1e-12
    assert phase_tampered.fidelity is not None and phase_tampered.fidelity < 1e-12


@pytest.mark.skipif(importlib.util.find_spec("cudaq") is None, reason="CUDA-Q runs in the Docker worker")
def test_cudaq_staged_recovery_uses_delivered_network_controls():
    engine = CudaQEngine(seed=260835)
    pending = engine.begin_networked_teleportation(
        bit=0,
        preparation_basis="X",
        measurement_basis="X",
    )
    honest = engine.complete_networked_teleportation(
        pending,
        delivered_bell_bits=pending.bell_bits,
    )
    phase_tampered = engine.complete_networked_teleportation(
        pending,
        delivered_bell_bits=(pending.bell_bits[0] ^ 1, pending.bell_bits[1]),
    )

    assert honest.bob_outcome == 0
    assert phase_tampered.bob_outcome == 1
