from __future__ import annotations

from zaslon_shared.quantum import ReferenceStatevectorEngine


def test_teleportation_engine_preserves_computational_and_phase_states():
    engine = ReferenceStatevectorEngine(seed=17)
    for basis in ("Z", "X"):
        for bit in (0, 1):
            outcomes = [
                engine.teleport_and_measure(
                    bit=bit, preparation_basis=basis, measurement_basis=basis
                )
                for _ in range(30)
            ]
            assert all(item.bob_outcome == bit for item in outcomes)
            assert all(item.fidelity is not None and item.fidelity > 0.999 for item in outcomes)


def test_wrong_basis_measurement_is_statistically_balanced():
    engine = ReferenceStatevectorEngine(seed=99)
    outcomes = [
        engine.teleport_and_measure(
            bit=0, preparation_basis="Z", measurement_basis="X"
        ).bob_outcome
        for _ in range(2000)
    ]
    rate = sum(outcomes) / len(outcomes)
    assert 0.45 < rate < 0.55


def test_pauli_x_flips_a_z_basis_state():
    engine = ReferenceStatevectorEngine(seed=5)
    outcome = engine.teleport_and_measure(
        bit=0,
        preparation_basis="Z",
        measurement_basis="Z",
        output_pauli="X",
    )
    assert outcome.bob_outcome == 1
    assert outcome.fidelity is not None and outcome.fidelity < 1e-9
