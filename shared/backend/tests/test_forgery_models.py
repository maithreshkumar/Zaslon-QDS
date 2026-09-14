from __future__ import annotations

import json

import pytest

from zaslon_shared.attacks import _full_forgery, get_experiment, run_attack
from zaslon_shared.db import AttackExperiment, session_scope
from zaslon_shared.protocol import create_qds_session
from zaslon_shared.schemas import AttackRunRequest


def _session() -> dict:
    return create_qds_session(
        document=b"independent forgery target",
        filename="target.bin",
        signer_id="Alice",
        verifier_id="Bob",
        seed=260900,
    )


def test_full_forgery_generates_every_declaration_without_legitimate_key_bits() -> None:
    created = _session()
    legitimate = created["signature"]
    forged = _full_forgery(
        legitimate,
        seed=260901,
        scenario="OBSERVED_SIGNATURE",
    )
    assert forged is not legitimate
    assert forged["declarations"] is not legitimate["declarations"]
    assert len(forged["declarations"]) == 512
    assert all(
        forged_item["key_bits"] is not legitimate_item["key_bits"]
        for forged_item, legitimate_item in zip(
            forged["declarations"], legitimate["declarations"], strict=True
        )
    )
    assert any(
        forged_item["key_bits"] != legitimate_item["key_bits"]
        for forged_item, legitimate_item in zip(
            forged["declarations"], legitimate["declarations"], strict=True
        )
    )


def test_independent_full_forgery_is_rejected_and_reported_empirically() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="FULL_FORGERY",
            target="SIGNATURE",
            attack_strength=1.0,
            seed=260902,
            parameters={"scenario": "OBSERVED_SIGNATURE", "forgery_trials": 16},
        )
    )
    assert result["verification"]["status"] == "INVALID"
    assert result["forgery"]["experiment_class"] == "FULL_FORGERY"
    assert result["forgery"]["started_from_legitimate_artifact_copy"] is False
    assert result["observations"]["legitimate_declaration_key_bits_copied"] == 0
    estimate = result["forgery"]["empirical_success_estimate"]
    assert estimate["accepted_trials"] == 0
    assert estimate["trials"] == 16
    assert estimate["estimated_probability"] == 0.0
    assert estimate["universal_security_bound"] is False
    reference = result["forgery"]["theoretical_or_reference_analysis"]
    assert reference["label"] == "REFERENCE BOUND"
    assert reference["formally_applies_to_zaslon"] is False


def test_partial_tampering_is_distinct_and_rejected() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="PARTIAL_SIGNATURE_TAMPERING",
            target="SIGNATURE",
            attack_strength=0.10,
            seed=260903,
            parameters={"forgery_trials": 16},
        )
    )
    assert result["verification"]["status"] == "INVALID"
    assert result["forgery"]["experiment_class"] == "PARTIAL_SIGNATURE_TAMPERING"
    assert result["forgery"]["independent_full_forgery"] is False
    assert result["observations"]["forged_declarations"] > 0


def test_phase_attack_is_detected_by_x_basis_control_states() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="PAULI_MANIPULATION",
            target="QUANTUM_STATE",
            attack_strength=1.0,
            seed=260904,
            parameters={"pauli_operation": "Z", "diagnostic_shots_per_basis": 64},
        )
    )
    diagnostic = result["observations"]["channel_diagnostic"]
    assert result["verification"]["mismatch_rate"] == 0.5
    assert result["verification"]["basis_statistics"]["Z"]["error_rate"] == 0.0
    assert result["verification"]["basis_statistics"]["X"]["error_rate"] == 1.0
    assert result["verification"]["status"] == "INVALID"
    assert diagnostic["z_basis_error_rate"] == 0.0
    assert diagnostic["x_basis_error_rate"] == 1.0
    assert result["detection"]["decision"] == "ATTACK_DETECTED"


def test_persisted_experiment_record_fails_closed_after_database_tampering() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="BASELINE",
            target="PROTOCOL",
            attack_strength=0.0,
            seed=260905,
        )
    )
    with session_scope() as db:
        row = db.get(AttackExperiment, result["experiment_id"])
        payload = json.loads(row.result_json)
        payload["status"] = "TAMPERED"
        row.result_json = json.dumps(payload)
    with pytest.raises(RuntimeError, match="EXPERIMENT_RECORD_INTEGRITY_FAILED"):
        get_experiment(result["experiment_id"])


def test_experiment_integrity_metadata_is_authenticated() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="BASELINE",
            target="PROTOCOL",
            attack_strength=0.0,
            seed=260906,
        )
    )
    with session_scope() as db:
        row = db.get(AttackExperiment, result["experiment_id"])
        payload = json.loads(row.result_json)
        payload["record_integrity"]["key_id"] = "local-attestation-deadbeefdeadbeef"
        row.result_json = json.dumps(payload)
    with pytest.raises(RuntimeError, match="EXPERIMENT_RECORD_INTEGRITY_FAILED"):
        get_experiment(result["experiment_id"])


def test_unknown_experiment_integrity_scheme_is_rejected() -> None:
    created = _session()
    result = run_attack(
        AttackRunRequest(
            qds_session_id=created["session"]["id"],
            attack_type="BASELINE",
            target="PROTOCOL",
            attack_strength=0.0,
            seed=260907,
        )
    )
    with session_scope() as db:
        row = db.get(AttackExperiment, result["experiment_id"])
        payload = json.loads(row.result_json)
        payload["record_integrity"]["scheme"] = "UNRECOGNIZED-SCHEME"
        row.result_json = json.dumps(payload)
    with pytest.raises(RuntimeError, match="EXPERIMENT_RECORD_INTEGRITY_FAILED"):
        get_experiment(result["experiment_id"])
