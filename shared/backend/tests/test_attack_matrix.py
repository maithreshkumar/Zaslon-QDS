from zaslon_shared.attacks import VALID_TARGETS, run_attack
from zaslon_shared.protocol import create_qds_session
from zaslon_shared.schemas import AttackRunRequest


STRENGTHS = (0.0, 0.10, 0.25, 0.50, 0.75, 1.0)
STRENGTH_DEPENDENT = {
    "INTERCEPT_RESEND", "ENTANGLEMENT_MANIPULATION", "PAULI_MANIPULATION",
    "BELL_RESULT_MANIPULATION", "CORRECTION_MITM", "SIGNATURE_FORGERY",
}


def test_every_attack_runs_at_all_required_strengths_and_changes_scope():
    for attack_index, (attack_type, target) in enumerate(VALID_TARGETS.items()):
        created = create_qds_session(
            document=attack_type.encode(), filename="matrix.txt",
            signer_id="Alice", verifier_id="Bob", seed=31 + attack_index,
        )
        affected = []
        for strength in STRENGTHS:
            result = run_attack(AttackRunRequest(
                qds_session_id=created["session"]["id"], attack_type=attack_type,
                target=target, attack_strength=strength, seed=41,
            ))
            assert result["status"] == "COMPLETED"
            assert result["attack"]["strength"] == strength
            if "attacked_states" in result["observations"]:
                affected.append(result["observations"]["attacked_states"])
            elif "forged_declarations" in result["observations"]:
                affected.append(result["observations"]["forged_declarations"])
        if attack_type in STRENGTH_DEPENDENT:
            assert affected == sorted(affected)
            assert affected[0] == 0
            assert affected[-1] > 0
