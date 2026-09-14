import pytest

from zaslon_shared.attacks import run_attack
from zaslon_shared.protocol import create_qds_session, get_session_quantum_status
from zaslon_shared.quantum import QiskitAerEngine, ReferenceStatevectorEngine
from zaslon_shared.schemas import AttackRunRequest


def test_phi_plus_is_verified_by_two_basis_correlations_and_state_metrics():
    diagnostic = ReferenceStatevectorEngine(seed=101).diagnose_bell_pair(
        shots=2048, preparation="PHI_PLUS"
    )

    assert diagnostic["verified"] is True
    assert diagnostic["status"] == "ENTANGLEMENT_VERIFIED"
    assert diagnostic["z_basis"]["correlation"] == 1.0
    assert diagnostic["x_basis"]["correlation"] == 1.0
    assert abs(diagnostic["state_metrics"]["reduced_alice_purity"] - 0.5) < 1e-12
    assert abs(diagnostic["state_metrics"]["entanglement_entropy_bits"] - 1.0) < 1e-12
    assert abs(diagnostic["state_metrics"]["concurrence"] - 1.0) < 1e-12
    assert abs(diagnostic["state_metrics"]["bell_state_fidelity"] - 1.0) < 1e-12
    assert diagnostic["non_destructive"] is True
    assert diagnostic["production_pair_measured"] is False


@pytest.mark.parametrize(
    ("bell_state", "expected_zz", "expected_xx"),
    [
        ("PHI_PLUS", 1.0, 1.0),
        ("PHI_MINUS", 1.0, -1.0),
        ("PSI_PLUS", -1.0, 1.0),
        ("PSI_MINUS", -1.0, -1.0),
    ],
)
def test_all_four_bell_states_are_classified_from_z_and_x_correlations(
    bell_state, expected_zz, expected_xx
):
    diagnostic = ReferenceStatevectorEngine(seed=110).diagnose_bell_pair(
        shots=2048, preparation=bell_state
    )

    assert diagnostic["z_basis"]["correlation"] == expected_zz
    assert diagnostic["x_basis"]["correlation"] == expected_xx
    assert diagnostic["observed_state"] == bell_state
    assert diagnostic["matches_expected"] is True
    assert diagnostic["bell_preparation_status"] == "EXPECTED"
    assert diagnostic["verified"] is True
    assert abs(diagnostic["state_metrics"]["bell_state_fidelity"] - 1.0) < 1e-12


def test_matching_independent_zero_qubits_are_not_misclassified_as_entangled():
    diagnostic = ReferenceStatevectorEngine(seed=102).diagnose_bell_pair(
        shots=2048, preparation="INDEPENDENT"
    )

    assert diagnostic["z_basis"]["00"] == 2048
    assert diagnostic["z_basis"]["correlation"] == 1.0
    assert diagnostic["x_basis"]["correlation"] < 0.10
    assert diagnostic["verified"] is False
    assert diagnostic["status"] == "ENTANGLEMENT_NOT_VERIFIED"


def test_h_without_cnot_is_not_verified_as_a_bell_pair():
    diagnostic = ReferenceStatevectorEngine(seed=103).diagnose_bell_pair(
        shots=2048, preparation="BROKEN_NO_CNOT"
    )

    assert diagnostic["z_basis"]["correlation"] < 0.10
    assert diagnostic["x_basis"]["correlation"] < 0.10
    assert diagnostic["state_metrics"]["concurrence"] == 0.0
    assert diagnostic["verified"] is False


def test_qiskit_independently_validates_phi_plus_state_metrics():
    diagnostic = QiskitAerEngine(seed=104).diagnose_bell_pair(
        shots=512, preparation="PHI_PLUS"
    )

    assert diagnostic["verified"] is True
    assert diagnostic["z_basis"]["correlation"] == 1.0
    assert diagnostic["x_basis"]["correlation"] == 1.0
    assert abs(diagnostic["state_metrics"]["reduced_alice_purity"] - 0.5) < 1e-12
    assert abs(diagnostic["state_metrics"]["entanglement_entropy_bits"] - 1.0) < 1e-12
    assert abs(diagnostic["state_metrics"]["concurrence"] - 1.0) < 1e-12
    assert abs(diagnostic["state_metrics"]["bell_state_fidelity"] - 1.0) < 1e-12


def test_session_lifecycle_and_bell_result_attack_preserve_initial_diagnosis():
    created = create_qds_session(
        document=b"Bell lifecycle",
        filename="bell.txt",
        signer_id="Alice",
        verifier_id="Bob",
        seed=105,
    )
    session_id = created["session"]["id"]
    status = get_session_quantum_status(session_id)

    assert status["entanglement"]["status"] == "ENTANGLEMENT_VERIFIED"
    assert status["bell_pair"]["status"] == "ENTANGLEMENT_CONSUMED_BY_TELEPORTATION"
    assert status["teleportation"]["status"] == "COMPLETED"
    assert status["teleportation"]["diagnostic_pair_reused"] is False
    analysis = status["bell_state_analysis"]
    assert analysis["preparation_mode"] == "UNIFORM"
    assert analysis["configured_states"] == ["PHI_PLUS"]
    assert analysis["distinct_bell_states_used"] == 1
    assert analysis["all_same"] is True
    assert analysis["states_used"] == {
        "PHI_PLUS": 4096,
        "PHI_MINUS": 0,
        "PSI_PLUS": 0,
        "PSI_MINUS": 0,
    }
    assert analysis["observed_state"] == "PHI_PLUS"
    assert analysis["matches_expected"] is True
    assert analysis["unexpected_behaviour_detected"] is False
    assert analysis["total_diagnostic_shots"] == 4096
    assert analysis["diagnostic_copies_are_production_pairs"] is False
    assert created["signature"]["bell_state_analysis"] == analysis
    assert [entry["status"] for entry in status["lifecycle"]] == [
        "NOT_YET_CREATED",
        "ENTANGLEMENT_CREATED",
        "ENTANGLEMENT_VERIFIED",
        "ENTANGLEMENT_CONSUMED_BY_TELEPORTATION",
        "TELEPORTATION_COMPLETED",
    ]

    attacked = run_attack(
        AttackRunRequest(
            qds_session_id=session_id,
            attack_type="BELL_RESULT_MANIPULATION",
            target="BELL_RESULTS",
            attack_strength=1.0,
            seed=106,
        )
    )
    interpretation = attacked["bell_result_attack_interpretation"]
    assert interpretation["bell_pair_creation"] == "VALID"
    assert interpretation["initial_entanglement"] == "ENTANGLEMENT_VERIFIED"
    assert interpretation["attacked_component"] == "CLASSICAL_BELL_MEASUREMENT_RESULTS"
    assert interpretation["original_bell_preparation_failed"] is False
    assert interpretation["teleportation_verification"] == "INVALID"
    assert interpretation["attack_detection"] == "ATTACK_DETECTED"
    assert attacked["quantum_status"]["entanglement"]["verified"] is True
