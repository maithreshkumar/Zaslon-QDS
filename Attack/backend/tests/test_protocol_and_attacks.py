from __future__ import annotations

from zaslon_shared.attacks import _forge_signature, run_attack
from zaslon_shared.protocol import (
    create_qds_session,
    signature_artifact_filename,
    verify_document,
)
from zaslon_shared.schemas import AttackRunRequest


def make_session():
    return create_qds_session(
        document=b"ZASLON quantum document",
        filename="evidence.txt",
        signer_id="Alice",
        verifier_id="Bob",
        seed=1234,
    )


def test_signature_artifact_filename_blocks_path_components():
    assert signature_artifact_filename("../../report final.pdf") == "report_final.pdf.qds.json"
    assert signature_artifact_filename(r"C:\private\report.pdf") == "report.pdf.qds.json"


def test_sign_verify_and_one_time_replay_protection():
    created = make_session()
    assert created["signature"]["format"] == "zaslon.qds.signature.v3"
    assert created["signature"]["protocol"] == "Teleportation-Based-QDS-Research-Simulation"
    assert all(
        declaration["encoding"] == "PAULI_XZ_EIGENSTATES"
        and declaration["bases"] == ["Z", "X", "Z", "X"]
        and "alice_bases" not in declaration
        for declaration in created["signature"]["declarations"]
    )
    first = verify_document(
        document=b"ZASLON quantum document", signature=created["signature"], consume=True
    )
    assert first.status == "VALID"
    assert first.mismatch_rate == 0.0
    assert first.usable_measurements == 512 * 4
    assert first.basis_statistics["Z"]["usable_measurements"] == 512 * 2
    assert first.basis_statistics["X"]["usable_measurements"] == 512 * 2
    assert first.basis_statistics["phase_sensitive_evidence"] is True
    second = verify_document(
        document=b"ZASLON quantum document", signature=created["signature"], consume=True
    )
    assert second.status == "INVALID"
    assert second.replay_detected is True


def test_document_tampering_fails_hash_binding():
    created = make_session()
    result = verify_document(
        document=b"modified document", signature=created["signature"], consume=False
    )
    assert result.status == "INVALID"
    assert result.document_hash_match is False


def test_forgery_generator_has_only_public_signature_view():
    created = make_session()
    forged, positions = _forge_signature(created["signature"], 0.35, 88)
    assert len(positions) == round(512 * 0.35)
    serialized = str(forged)
    for forbidden in (
        "bob_bases",
        "bob_outcomes",
        "private_verifier_record",
        "undisclosed_alice_material",
        "candidates",
    ):
        assert forbidden not in serialized


def test_full_random_basis_intercept_resend_disturbs_teleported_bits():
    created = make_session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="INTERCEPT_RESEND",
            target="QUANTUM_CHANNEL",
            attack_strength=1.0,
            seed=2026,
        )
    )
    qber = result["verification"]["mismatch_rate"]
    assert qber is not None
    assert 0.19 < qber < 0.31
    assert result["observations"]["mismatches"] / result["observations"]["usable_measurements"] == qber
    assert result["detection"]["decision"] == "ATTACK_DETECTED"


def test_signature_forgery_uses_normal_verifier():
    created = make_session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="SIGNATURE_FORGERY",
            target="SIGNATURE",
            attack_strength=0.35,
            seed=7,
        )
    )
    assert result["verification"]["status"] in {"VALID", "INVALID", "UNVERIFIABLE"}
    estimate = result["forgery"]["success_estimate"]
    assert estimate["trials"] == 64
    assert 0.0 <= estimate["estimated_probability"] <= 1.0
    assert len(estimate["wilson_95_percent_interval"]) == 2
    assert result["detection"]["decision"] == "NOT_APPLICABLE"
    assert result["forgery"]["original_artifact_unchanged"] is True


def test_phase_only_attack_is_visible_in_normal_signature_verification():
    created = make_session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="PAULI_MANIPULATION",
            target="QUANTUM_STATE",
            attack_strength=1.0,
            seed=2027,
            parameters={"pauli_operation": "Z"},
        )
    )
    basis = result["verification"]["basis_statistics"]
    assert basis["Z"]["error_rate"] == 0.0
    assert basis["X"]["error_rate"] == 1.0
    assert result["verification"]["status"] == "INVALID"
