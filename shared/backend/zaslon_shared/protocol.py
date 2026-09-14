from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import random
import re
import secrets
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update

from .config import settings
from .crypto import encrypt_payload, sha512_hex
from .db import Participant, QDSSession, session_scope
from .quantum import (
    PRODUCTION_BELL_STATE,
    NoiseConfig,
    QuantumEngine,
    create_quantum_engine,
    derive_simulation_seed,
)
from .provenance import runtime_provenance
from .schemas import SignatureArtifact


logger = logging.getLogger("zaslon.quantum")


def digest_bits(digest_hex: str) -> list[int]:
    return [int(bit) for char in digest_hex for bit in f"{int(char, 16):04b}"]


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str
    document_hash_match: bool
    usable_measurements: int
    mismatches: int
    mismatch_rate: float | None
    threshold: float
    threshold_source: str
    replay_detected: bool = False
    total_disclosed_measurements: int = 0
    raw_error_rate: float | None = None
    failure_code: str | None = None
    structural_valid: bool = True
    authenticated_verifier: str | None = None
    basis_statistics: dict[str, Any] | None = None

    def model_dump(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


def signature_artifact_filename(document_name: str) -> str:
    basename = str(document_name).replace("\\", "/").rsplit("/", 1)[-1]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip(" ._")
    return f"{(safe_name or 'document')[:220]}.qds.json"


def serialize_signature_artifact(signature: dict[str, Any]) -> bytes:
    return (json.dumps(signature, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _artifact_attestation_secret() -> bytes:
    secret = (
        settings.artifact_attestation_key
        or settings.job_payload_key
        or settings.alice_api_key
    )
    if len(secret) < 24:
        raise RuntimeError(
            "A server-side artifact attestation key of at least 24 characters is required."
        )
    return secret.encode("utf-8")


def _artifact_attestation_tag(signature: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in signature.items() if key != "server_attestation"}
    canonical = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hmac.new(_artifact_attestation_secret(), canonical, hashlib.sha512).hexdigest()


def _artifact_attestation_key_id() -> str:
    return (
        "local-attestation-"
        f"{hashlib.sha256(_artifact_attestation_secret()).hexdigest()[:16]}"
    )


def _attest_artifact(signature: dict[str, Any]) -> None:
    signature["server_attestation"] = {
        "scheme": "HMAC-SHA512-SERVER-ATTESTED-ROLE-BINDING",
        "key_id": _artifact_attestation_key_id(),
        "signed_fields": "ALL_ARTIFACT_FIELDS_EXCEPT_SERVER_ATTESTATION",
        "tag": _artifact_attestation_tag(signature),
        "security_scope": "TRUSTED_SERVER_INTEGRITY_AND_ROLE_BINDING",
        "non_repudiation_claim": False,
    }


def _uniform_bell_state_analysis(
    *, diagnostic: dict[str, Any], production_preparations: int
) -> dict[str, Any]:
    states_used = {
        "PHI_PLUS": production_preparations if PRODUCTION_BELL_STATE == "PHI_PLUS" else 0,
        "PHI_MINUS": production_preparations if PRODUCTION_BELL_STATE == "PHI_MINUS" else 0,
        "PSI_PLUS": production_preparations if PRODUCTION_BELL_STATE == "PSI_PLUS" else 0,
        "PSI_MINUS": production_preparations if PRODUCTION_BELL_STATE == "PSI_MINUS" else 0,
    }
    matches_expected = bool(diagnostic["matches_expected"])
    return {
        "preparation_mode": "UNIFORM",
        "total_preparation_configurations": 1,
        "configured_states": [PRODUCTION_BELL_STATE],
        "distinct_bell_states_used": 1,
        "all_same": True,
        "different_states_deliberately_used": False,
        "expected_state": PRODUCTION_BELL_STATE,
        "states_used": states_used,
        "total_production_preparations": production_preparations,
        "diagnostic_shots_per_basis": diagnostic["shots"],
        "total_diagnostic_shots": diagnostic["total_diagnostic_shots"],
        "diagnostic_copies_are_production_pairs": False,
        "observed_state": diagnostic["observed_state"],
        "zz_correlation": diagnostic["z_basis"]["correlation"],
        "xx_correlation": diagnostic["x_basis"]["correlation"],
        "matches_expected": matches_expected,
        "unexpected_behaviour_detected": not matches_expected,
        "status": "EXPECTED_BELL_STATE" if matches_expected else "UNEXPECTED_BELL_STATE_BEHAVIOUR",
        "preparation_circuit": ["H(q1)", "CNOT(q1,q2)"],
        "normal_post_creation_bell_state_gates": [],
    }


def _completed_quantum_status(
    *,
    session_id: str,
    diagnostic: dict[str, Any],
    bell_state_analysis: dict[str, Any],
    bell_pairs_consumed: int,
) -> dict[str, Any]:
    metadata = diagnostic["engine"]
    return {
        "session_id": session_id,
        "engine": metadata["engine"],
        "target": metadata["target"],
        "gpu": metadata["gpu"],
        "fallback_used": metadata["fallback_used"],
        "bell_pair": {
            "alice_qubit": "q1",
            "bob_qubit": "q2",
            "expected_state": "PHI_PLUS",
            "creation_status": "SUCCESS",
            "verification_status": diagnostic["status"],
            "status": "ENTANGLEMENT_CONSUMED_BY_TELEPORTATION",
        },
        "entanglement": diagnostic,
        "bell_state_analysis": bell_state_analysis,
        "teleportation": {
            "status": "COMPLETED",
            "bell_pairs_consumed": bell_pairs_consumed,
            "diagnostic_pair_reused": False,
        },
        "lifecycle": [
            {"stage": "BEFORE_BELL_PAIR_CREATION", "status": "NOT_YET_CREATED"},
            {"stage": "AFTER_BELL_PAIR_CREATION", "status": "ENTANGLEMENT_CREATED"},
            {"stage": "PRE_TELEPORTATION", "status": diagnostic["status"]},
            {
                "stage": "ALICE_BELL_MEASUREMENT_Q0_Q1",
                "status": "ENTANGLEMENT_CONSUMED_BY_TELEPORTATION",
            },
            {"stage": "BOB_PAULI_CORRECTION", "status": "TELEPORTATION_COMPLETED"},
        ],
    }


def _log_quantum_channel_diagnostic(
    diagnostic: dict[str, Any], bell_state_analysis: dict[str, Any]
) -> None:
    metadata = diagnostic["engine"]
    metrics = diagnostic["state_metrics"]
    fidelity = metrics.get("bell_state_fidelity")
    entropy = metrics.get("entanglement_entropy_bits")
    logger.info(
        "\n%s\nQDS QUANTUM CHANNEL DIAGNOSTIC\n%s\n"
        "Quantum Engine       : %s\nTarget               : %s\nGPU Execution        : %s\n"
        "Fallback Used        : %s\nAlice Bell Qubit     : q1\nBob Bell Qubit       : q2\n"
        "Bell Pair Creation   : SUCCESS\nExpected Bell State  : |Phi+>\n"
        "Entanglement Test\n-----------------\nShots per basis      : %d\n"
        "Z Correlation        : %.6f\nX Correlation        : %.6f\n"
        "Bell Fidelity        : %s\nEntanglement Entropy : %s\n"
        "ENTANGLEMENT STATUS  : %s\nReason               : %s\n\n"
        "BELL-STATE CONFIGURATION\n------------------------\n"
        "Preparation mode     : %s\nConfigured states    : %d\n"
        "Phi+ preparations    : %d\nPhi- preparations    : %d\n"
        "Psi+ preparations    : %d\nPsi- preparations    : %d\n"
        "Observed state       : %s\nMatches configuration: %s\n"
        "ALL BELL PAIRS SAME  : %s\n%s",
        "=" * 60,
        "=" * 60,
        metadata["engine"],
        metadata["target"],
        "YES" if metadata["gpu"] else "NO",
        "YES" if metadata["fallback_used"] else "NO",
        diagnostic["shots"],
        diagnostic["z_basis"]["correlation"],
        diagnostic["x_basis"]["correlation"],
        f"{fidelity:.6f}" if fidelity is not None else "UNAVAILABLE ON TARGET",
        f"{entropy:.6f} bits" if entropy is not None else "UNAVAILABLE ON TARGET",
        "VERIFIED" if diagnostic["verified"] else "NOT VERIFIED",
        diagnostic["reason"],
        bell_state_analysis["preparation_mode"],
        bell_state_analysis["total_preparation_configurations"],
        bell_state_analysis["states_used"]["PHI_PLUS"],
        bell_state_analysis["states_used"]["PHI_MINUS"],
        bell_state_analysis["states_used"]["PSI_PLUS"],
        bell_state_analysis["states_used"]["PSI_MINUS"],
        diagnostic["observed_state"] or "UNCLASSIFIED",
        "YES" if bell_state_analysis["matches_expected"] else "NO",
        "YES" if bell_state_analysis["all_same"] else "NO",
        "=" * 60,
    )


def create_qds_session(
    *,
    document: bytes,
    filename: str,
    signer_id: str,
    verifier_id: str,
    seed: int | None = None,
    encryption_passphrase: str | None = None,
    noise: NoiseConfig | None = None,
    verification_threshold: float | None = None,
    threshold_source: str | None = None,
    network_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experiment_seed = seed if seed is not None else secrets.randbits(31)
    rng = random.Random(experiment_seed)
    engine: QuantumEngine = create_quantum_engine(settings.quantum_engine, experiment_seed)
    document_hash = sha512_hex(document)
    bits = digest_bits(document_hash)
    session_id = _new_id("QDS")
    nonce = secrets.token_hex(24)
    candidates: list[dict[str, Any]] = []
    declarations: list[dict[str, Any]] = []
    baseline_usable = 0
    baseline_mismatches = 0
    baseline_basis = {
        "Z": {"usable_measurements": 0, "mismatches": 0},
        "X": {"usable_measurements": 0, "mismatches": 0},
    }
    fidelity_samples: list[float] = []
    bell_counts = {"00": 0, "01": 0, "10": 0, "11": 0}
    actual_correction_messages: list[tuple[int, int]] = []
    staged_recoveries: list[tuple[dict[str, Any], Any, bool, int, str]] = []
    networked_execution = (
        isinstance(network_context, dict)
        and network_context.get("engine") == "SeQUeNCe"
    )
    active_noise = noise or NoiseConfig()
    active_threshold = (
        settings.verification_threshold
        if verification_threshold is None
        else float(verification_threshold)
    )
    if not 0.0 <= active_threshold <= 1.0:
        raise ValueError("verification_threshold must be between 0 and 1")
    active_threshold_source = threshold_source or settings.threshold_source
    production_bell_pairs = len(bits) * 2 * settings.states_per_candidate
    bell_diagnostic = engine.diagnose_bell_pair(
        shots=settings.entanglement_diagnostic_shots,
        preparation=PRODUCTION_BELL_STATE,
        correlation_threshold=settings.entanglement_correlation_threshold,
    )
    bell_state_analysis = _uniform_bell_state_analysis(
        diagnostic=bell_diagnostic,
        production_preparations=production_bell_pairs,
    )
    _log_quantum_channel_diagnostic(bell_diagnostic, bell_state_analysis)
    if not bell_diagnostic["verified"]:
        raise RuntimeError(
            "Alice-Bob Bell-pair entanglement was not verified; teleportation was not started."
        )
    effective_diagnostic_engine = create_quantum_engine(
        settings.quantum_engine,
        derive_simulation_seed(experiment_seed, "EFFECTIVE_BELL_CHANNEL_DIAGNOSTIC"),
    )
    effective_channel_diagnostic = effective_diagnostic_engine.diagnose_bell_pair(
        shots=settings.entanglement_diagnostic_shots,
        preparation=PRODUCTION_BELL_STATE,
        correlation_threshold=settings.entanglement_correlation_threshold,
        noise=active_noise,
    )

    for position, signed_bit in enumerate(bits):
        candidate_record: dict[str, Any] = {"position": position, "values": {}}
        for candidate_bit in (0, 1):
            states: list[dict[str, Any]] = []
            for state_index in range(settings.states_per_candidate):
                key_bit = rng.getrandbits(1)
                basis = "Z" if state_index % 2 == 0 else "X"
                state_record = {
                    "index": state_index,
                    "key_bit": key_bit,
                    "encoding": "PAULI_XZ_EIGENSTATES",
                    "basis": basis,
                    "bob_outcome": None,
                    "bell_bits": None,
                    "fidelity": None,
                }
                states.append(state_record)
                if networked_execution:
                    pending = engine.begin_networked_teleportation(
                        bit=key_bit,
                        preparation_basis=basis,
                        measurement_basis=basis,
                        noise=active_noise,
                    )
                    state_record["bell_bits"] = list(pending.bell_bits)
                    actual_correction_messages.append(pending.bell_bits)
                    staged_recoveries.append(
                        (state_record, pending, candidate_bit == signed_bit, key_bit, basis)
                    )
                else:
                    result = engine.teleport_and_measure(
                        bit=key_bit,
                        preparation_basis=basis,
                        measurement_basis=basis,
                        noise=active_noise,
                    )
                    bell_counts[f"{result.bell_bits[0]}{result.bell_bits[1]}"] += 1
                    actual_correction_messages.append(result.bell_bits)
                    state_record["bob_outcome"] = result.bob_outcome
                    state_record["bell_bits"] = list(result.bell_bits)
                    state_record["fidelity"] = result.fidelity
                    if candidate_bit == signed_bit:
                        baseline_usable += 1
                        baseline_mismatches += int(result.bob_outcome != key_bit)
                        baseline_basis[basis]["usable_measurements"] += 1
                        baseline_basis[basis]["mismatches"] += int(
                            result.bob_outcome != key_bit
                        )
                    if candidate_bit == signed_bit and result.fidelity is not None:
                        fidelity_samples.append(result.fidelity)
            candidate_record["values"][str(candidate_bit)] = states
        selected = candidate_record["values"][str(signed_bit)]
        declarations.append(
            {
                "position": position,
                "digest_bit": signed_bit,
                "key_bits": [state["key_bit"] for state in selected],
                "encoding": "PAULI_XZ_EIGENSTATES",
                "bases": [state["basis"] for state in selected],
            }
        )
        candidates.append(candidate_record)

    if networked_execution:
        # Bell measurement completes first, SeQUeNCe delivers the actual control
        # bits, and only then does the receiver recovery stage execute.
        from .network import configured_network, simulate_sequence_network

        if signer_id not in {"Alice", "Bob"} or verifier_id not in {"Alice", "Bob", "Charlie"}:
            raise RuntimeError("UNSUPPORTED_NETWORK_PARTICIPANT_TOPOLOGY")
        correction_receiver = verifier_id
        integrated_network = simulate_sequence_network(
            requested_bell_pairs=production_bell_pairs,
            config=configured_network(
                seed=experiment_seed,
                include_charlie=correction_receiver == "Charlie",
                sample_pairs=production_bell_pairs,
            ),
            correction_messages=actual_correction_messages,
            correction_sender=signer_id,
            correction_receiver=correction_receiver,
            include_private_delivery_receipts=True,
        )
        if not integrated_network["gate_to_cudaq"]["allowed"]:
            raise RuntimeError("CLASSICAL_CORRECTION_DISTRIBUTION_FAILED")
        delivered_messages = integrated_network.pop(
            "_private_delivered_correction_messages"
        )
        if len(delivered_messages) != len(staged_recoveries):
            raise RuntimeError("CLASSICAL_CORRECTION_DELIVERY_COUNT_MISMATCH")
        for recovery, delivered in zip(staged_recoveries, delivered_messages, strict=True):
            state_record, pending, selected, key_bit, basis = recovery
            result = engine.complete_networked_teleportation(
                pending,
                delivered_bell_bits=(int(delivered[0]), int(delivered[1])),
            )
            state_record["bob_outcome"] = result.bob_outcome
            state_record["fidelity"] = result.fidelity
            bell_counts[f"{result.bell_bits[0]}{result.bell_bits[1]}"] += 1
            if selected:
                baseline_usable += 1
                baseline_mismatches += int(result.bob_outcome != key_bit)
                baseline_basis[basis]["usable_measurements"] += 1
                baseline_basis[basis]["mismatches"] += int(
                    result.bob_outcome != key_bit
                )
                if result.fidelity is not None:
                    fidelity_samples.append(result.fidelity)
        integrated_network["preflight"] = network_context
        integrated_network["integration"]["control_effect"] = (
            "SEQUENCE_DELIVERED_BITS_CAUSALLY_DRIVE_RECEIVER_RECOVERY_STAGE"
        )
        integrated_network["integration"]["execution_order"] = [
            "CUDA_Q_BELL_MEASUREMENT",
            "SEQUENCE_CLASSICAL_DELIVERY",
            "CUDA_Q_RECEIVER_CORRECTION_AND_MEASUREMENT",
        ]
        integrated_network["integration"]["receiver_state_continuity"] = (
            "PRESERVED_COLLAPSED_STATEVECTOR"
            if engine.metadata.engine == "REFERENCE_STATEVECTOR"
            else "CONDITIONAL_STATE_RECONSTRUCTION_ACROSS_CUDAQ_RUN_BOUNDARY"
        )
        network_context = integrated_network

    quantum_status = _completed_quantum_status(
        session_id=session_id,
        diagnostic=bell_diagnostic,
        bell_state_analysis=bell_state_analysis,
        bell_pairs_consumed=production_bell_pairs,
    )
    quantum_status["effective_bell_distribution"] = effective_channel_diagnostic
    logger.info(
        "QDS session %s: ENTANGLEMENT_CONSUMED_BY_TELEPORTATION; TELEPORTATION_COMPLETED",
        session_id,
    )

    public_signature = {
        "format": "zaslon.qds.signature.v3",
        "version": "3.0",
        "algorithm": "ZASLON-TELEPORTATION-QDS-RESEARCH",
        "protocol": settings.protocol_name,
        "protocol_version": settings.protocol_version,
        "signature_id": _new_id("SIG"),
        "session_id": session_id,
        "signer_id": signer_id,
        "verifier_id": verifier_id,
        "document_name": filename,
        "document_hash": document_hash,
        "hash_algorithm": "SHA-512",
        "nonce": nonce,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prepared_quantum_states": len(bits) * 2 * settings.states_per_candidate,
        "disclosed_quantum_states": len(bits) * settings.states_per_candidate,
        "maximum_simultaneous_circuit_qubits": engine.metadata.maximum_circuit_width,
        "verification_policy": {
            "mismatch_threshold": active_threshold,
            "source": active_threshold_source,
            "claim": "Configured experimental parameter; not a proven security bound.",
        },
        "verification_thresholds": {
            "mismatch_threshold": active_threshold,
            "source": active_threshold_source,
        },
        "quantum_parameters": {
            "states_per_candidate": settings.states_per_candidate,
            "digest_bits": len(bits),
            "message_encoding": "PAULI_XZ_EIGENSTATES",
            "verifier_measurement": "DECLARED_MATCHING_X_OR_Z_BASIS",
            "basis_schedule": "ALTERNATING_Z_X_PER_CANDIDATE",
            "phase_sensitive_evidence": True,
            "maximum_simultaneous_qubits": engine.metadata.maximum_circuit_width,
            "bell_pair_state": PRODUCTION_BELL_STATE,
            "bell_pair_preparation_mode": "UNIFORM",
        },
        "teleportation_metadata": {
            "bell_measurement_register_order": ["message", "alice_entangled"],
            "corrections": {"second_bit": "X", "first_bit": "Z"},
            "message_preparation": "Declared X/Z Pauli eigenstate",
            "verifier_measurement": "Matching declared X or Z basis",
            "bell_pair_preparation": ["H(q1)", "CNOT(q1,q2)"],
        },
        "quantum_diagnostic": bell_diagnostic,
        "effective_channel_diagnostic": effective_channel_diagnostic,
        "bell_state_analysis": bell_state_analysis,
        "noise_parameters": active_noise.model_dump(),
        "quantum_status": quantum_status,
        "network_metadata": network_context,
        "reproducibility": runtime_provenance(
            component="QDS_SIGNATURE_GENERATION",
            seed=experiment_seed,
            quantum=engine.metadata.model_dump(),
        ),
        "declarations": declarations,
        "signature_declarations": declarations,
    }
    _attest_artifact(public_signature)
    SignatureArtifact.model_validate(public_signature, strict=True)
    for basis_metrics in baseline_basis.values():
        count = basis_metrics["usable_measurements"]
        basis_metrics["error_rate"] = (
            basis_metrics["mismatches"] / count if count else None
        )
    private_evidence = {
        "experiment_seed": experiment_seed,
        "quantum_status": quantum_status,
        "effective_channel_diagnostic": effective_channel_diagnostic,
        "candidates": candidates,
        "baseline": {
            "usable_measurements": baseline_usable,
            "mismatches": baseline_mismatches,
            "mismatch_rate": baseline_mismatches / baseline_usable if baseline_usable else None,
            "mean_teleportation_fidelity": (
                sum(fidelity_samples) / len(fidelity_samples) if fidelity_samples else None
            ),
            "total_disclosed_measurements": len(bits) * settings.states_per_candidate,
            "raw_error_rate": baseline_mismatches / (len(bits) * settings.states_per_candidate),
            "bell_outcome_counts": bell_counts,
            "basis_statistics": baseline_basis,
            "phase_sensitive_evidence": baseline_basis["X"]["usable_measurements"] > 0,
        },
        "noise_parameters": active_noise.model_dump(),
        "network_metadata": network_context,
    }
    row = QDSSession(
        id=session_id,
        signer_id=signer_id,
        verifier_id=verifier_id,
        protocol=settings.protocol_name,
        protocol_version=settings.protocol_version,
        document_name=filename,
        document_hash=document_hash,
        public_signature_json=json.dumps(public_signature, separators=(",", ":")),
        private_evidence_json=json.dumps(private_evidence, separators=(",", ":")),
        prepared_state_count=public_signature["prepared_quantum_states"],
        max_circuit_width=engine.metadata.maximum_circuit_width,
        verification_threshold=active_threshold,
        threshold_source=active_threshold_source,
        quantum_engine=engine.metadata.engine,
        quantum_target=engine.metadata.target,
        nonce=nonce,
    )
    with session_scope() as db:
        for participant_id, role in ((signer_id, "SIGNER"), (verifier_id, "VERIFIER")):
            if db.get(Participant, participant_id) is None:
                db.add(Participant(id=participant_id, role=role))
        db.add(row)

    response: dict[str, Any] = {
        "session": {
            "id": session_id,
            "signer_id": signer_id,
            "verifier_id": verifier_id,
            "document_name": filename,
            "created_at": public_signature["created_at"],
        },
        "signature": public_signature,
        "quantum": engine.metadata.model_dump(),
        "quantum_status": quantum_status,
        "network": network_context,
        "baseline": private_evidence["baseline"],
        "artifact": {
            "filename": signature_artifact_filename(filename),
            "media_type": "application/json",
            "download_url": f"/api/v1/sessions/{session_id}/signature",
        },
        "encryption": None,
    }
    if encryption_passphrase:
        response["encryption"] = encrypt_payload(document, encryption_passphrase, filename)
    return response


def load_qds_session(session_id: str) -> tuple[QDSSession, dict[str, Any], dict[str, Any]]:
    with session_scope() as db:
        row = db.scalar(select(QDSSession).where(QDSSession.id == session_id))
        if row is None:
            raise LookupError("QDS session not found")
        db.expunge(row)
    return row, json.loads(row.public_signature_json), json.loads(row.private_evidence_json)


def _verification_failure(
    *,
    code: str,
    reason: str,
    row: QDSSession | None = None,
    document_hash_match: bool = False,
    structural_valid: bool = False,
    replay_detected: bool = False,
    authenticated_verifier: str | None = None,
) -> VerificationResult:
    return VerificationResult(
        status="INVALID",
        reason=reason,
        document_hash_match=document_hash_match,
        usable_measurements=0,
        mismatches=0,
        mismatch_rate=None,
        threshold=row.verification_threshold if row is not None else settings.verification_threshold,
        threshold_source=row.threshold_source if row is not None else settings.threshold_source,
        replay_detected=replay_detected,
        failure_code=code,
        structural_valid=structural_valid,
        authenticated_verifier=authenticated_verifier,
    )


def _strict_signature_validation(
    *,
    row: QDSSession,
    signature: dict[str, Any],
    document_hash: str,
    authenticated_verifier_id: str | None,
) -> tuple[dict[str, Any] | None, VerificationResult | None]:
    try:
        parsed = SignatureArtifact.model_validate(signature, strict=True)
        normalized = parsed.model_dump(exclude_none=parsed.version == "2.0")
    except ValidationError:
        return None, _verification_failure(
            code="MALFORMED_SIGNATURE_STRUCTURE",
            reason="The QDS artifact does not match the strict signature schema.",
            row=row,
        )

    stored = json.loads(row.public_signature_json)
    if normalized.get("version") == "3.0":
        provided_attestation = normalized.get("server_attestation", {})
        expected_tag = _artifact_attestation_tag(normalized)
        key_id_matches = hmac.compare_digest(
            str(provided_attestation.get("key_id", "")),
            _artifact_attestation_key_id(),
        )
        if not key_id_matches or not hmac.compare_digest(
            str(provided_attestation.get("tag", "")), expected_tag
        ):
            return None, _verification_failure(
                code="SERVER_ATTESTATION_FAILED",
                reason="The server-attested artifact integrity or signer-role binding failed.",
                row=row,
            )
    identity_fields = (
        ("signature_id", stored.get("signature_id"), "SIGNATURE_ID_MISMATCH"),
        ("session_id", row.id, "SESSION_ID_MISMATCH"),
        ("nonce", row.nonce, "NONCE_MISMATCH"),
        ("format", stored.get("format"), "FORMAT_MISMATCH"),
        ("version", stored.get("version"), "VERSION_MISMATCH"),
        ("algorithm", "ZASLON-TELEPORTATION-QDS-RESEARCH", "ALGORITHM_MISMATCH"),
        ("protocol", row.protocol, "PROTOCOL_MISMATCH"),
        ("protocol_version", row.protocol_version, "PROTOCOL_VERSION_MISMATCH"),
        ("signer_id", row.signer_id, "SIGNER_IDENTITY_MISMATCH"),
        ("verifier_id", row.verifier_id, "INTENDED_VERIFIER_MISMATCH"),
        ("hash_algorithm", "SHA-512", "HASH_ALGORITHM_MISMATCH"),
    )
    for field, expected, code in identity_fields:
        if normalized.get(field) != expected:
            return None, _verification_failure(
                code=code,
                reason=f"Security binding failed for signature field {field}.",
                row=row,
            )

    hash_match = normalized["document_hash"] == document_hash == row.document_hash
    if not hash_match:
        return None, _verification_failure(
            code="DOCUMENT_HASH_MISMATCH",
            reason="SHA-512 document binding failed.",
            row=row,
            structural_valid=True,
        )

    if authenticated_verifier_id is not None and authenticated_verifier_id != row.verifier_id:
        return None, _verification_failure(
            code="UNAUTHORIZED_VERIFIER",
            reason="The authenticated verifier is not the intended verifier for this signature.",
            row=row,
            document_hash_match=True,
            structural_valid=True,
            authenticated_verifier=authenticated_verifier_id,
        )

    declarations = normalized["declarations"]
    if len(declarations) != 512:
        return None, _verification_failure(
            code="DECLARATION_COUNT_MISMATCH",
            reason="A SHA-512 signature must contain exactly 512 declarations.",
            row=row,
        )
    if normalized["signature_declarations"] != declarations:
        return None, _verification_failure(
            code="DECLARATION_ALIAS_MISMATCH",
            reason="The two declaration representations are inconsistent.",
            row=row,
        )

    positions = [item["position"] for item in declarations]
    if positions != list(range(512)):
        code = "DUPLICATE_DECLARATION_POSITION" if len(set(positions)) != len(positions) else "NONCANONICAL_DECLARATION_POSITIONS"
        return None, _verification_failure(
            code=code,
            reason="Declaration positions must be unique, complete, and canonically ordered 0 through 511.",
            row=row,
        )

    actual_bits = digest_bits(document_hash)
    for position, declaration in enumerate(declarations):
        if declaration["digest_bit"] != actual_bits[position]:
            return None, _verification_failure(
                code="DECLARED_DIGEST_BIT_MISMATCH",
                reason=f"Declaration {position} does not match the uploaded document digest.",
                row=row,
            )
        if len(declaration["key_bits"]) != settings.states_per_candidate:
            return None, _verification_failure(
                code="DECLARATION_STATE_COUNT_MISMATCH",
                reason=f"Declaration {position} has the wrong number of state labels.",
                row=row,
            )
        bases = declaration.get("bases")
        if normalized["version"] == "3.0" and (
            not isinstance(bases, list)
            or len(bases) != len(declaration["key_bits"])
            or not {"X", "Z"} <= set(bases)
        ):
            return None, _verification_failure(
                code="BASIS_DECLARATION_INVALID",
                reason=f"Declaration {position} must contain both X- and Z-basis evidence.",
                row=row,
            )

    if declarations != stored.get("declarations"):
        return None, _verification_failure(
            code="DECLARATIONS_DO_NOT_MATCH_TRUSTED_SESSION",
            reason="Declarations were modified or mixed with another session.",
            row=row,
        )
    return normalized, None


def verify_against_evidence(
    *,
    row: QDSSession,
    signature: dict[str, Any],
    evidence: dict[str, Any],
    document_hash: str,
    authenticated_verifier_id: str | None = None,
) -> VerificationResult:
    signature, failure = _strict_signature_validation(
        row=row,
        signature=signature,
        document_hash=document_hash,
        authenticated_verifier_id=authenticated_verifier_id,
    )
    if failure is not None:
        return failure
    assert signature is not None
    candidates = {item["position"]: item for item in evidence["candidates"]}
    usable = 0
    mismatches = 0
    basis_counts: dict[str, dict[str, int]] = {
        "Z": {"usable_measurements": 0, "mismatches": 0},
        "X": {"usable_measurements": 0, "mismatches": 0},
    }
    try:
        for declaration in signature["declarations"]:
            position = int(declaration["position"])
            digest_bit = int(declaration["digest_bit"])
            states = candidates[position]["values"][str(digest_bit)]
            declared_bits = declaration["key_bits"]
            encoding = declaration.get("encoding")
            if encoding not in {"COMPUTATIONAL_BASIS", "PAULI_XZ_EIGENSTATES"}:
                raise ValueError("Unsupported teleportation message encoding")
            if len(states) != len(declared_bits):
                raise ValueError("Teleportation evidence length mismatch")
            declared_bases = declaration.get("bases") or ["Z"] * len(declared_bits)
            for index, state in enumerate(states):
                if state.get("encoding") not in {
                    "COMPUTATIONAL_BASIS", "PAULI_XZ_EIGENSTATES"
                }:
                    raise ValueError("Unsupported private evidence encoding")
                basis = str(state.get("basis", "Z"))
                if basis not in {"X", "Z"} or declared_bases[index] != basis:
                    raise ValueError("Declared and trusted measurement bases do not match")
                declared_bit = int(declared_bits[index])
                usable += 1
                mismatch = int(int(state["bob_outcome"]) != declared_bit)
                mismatches += mismatch
                basis_counts[basis]["usable_measurements"] += 1
                basis_counts[basis]["mismatches"] += mismatch
    except (KeyError, IndexError, TypeError, ValueError):
        return VerificationResult(
            "INVALID", "Trusted evidence does not match the active schema.", True,
            usable, mismatches, None, row.verification_threshold, row.threshold_source,
            failure_code="TRUSTED_EVIDENCE_SCHEMA_MISMATCH", structural_valid=False,
        )
    if usable == 0:
        return VerificationResult(
            "INVALID", "No trusted teleportation evidence is available.", True,
            0, 0, None, row.verification_threshold, row.threshold_source,
            failure_code="NO_TRUSTED_EVIDENCE", structural_valid=False,
        )
    mismatch_rate = mismatches / usable
    valid = mismatch_rate <= row.verification_threshold
    basis_statistics: dict[str, Any] = {}
    for basis, counts in basis_counts.items():
        count = counts["usable_measurements"]
        basis_statistics[basis] = {
            **counts,
            "error_rate": counts["mismatches"] / count if count else None,
        }
    basis_statistics["phase_sensitive_evidence"] = (
        basis_counts["X"]["usable_measurements"] > 0
    )
    return VerificationResult(
        "VALID" if valid else "INVALID",
        "Trusted teleportation evidence is within the configured experimental threshold."
        if valid
        else "Trusted teleportation evidence exceeds the configured experimental threshold.",
        True,
        usable,
        mismatches,
        mismatch_rate,
        row.verification_threshold,
        row.threshold_source,
        total_disclosed_measurements=len(signature.get("declarations", [])) * settings.states_per_candidate,
        raw_error_rate=mismatches / (len(signature.get("declarations", [])) * settings.states_per_candidate)
        if signature.get("declarations") else None,
        authenticated_verifier=authenticated_verifier_id,
        basis_statistics=basis_statistics,
    )


def verify_document(
    *,
    document: bytes,
    signature: dict[str, Any],
    consume: bool = True,
    authenticated_verifier_id: str | None = None,
) -> VerificationResult:
    session_id = str(signature.get("session_id", ""))
    try:
        row, _, evidence = load_qds_session(session_id)
    except LookupError:
        return _verification_failure(
            code="UNKNOWN_SESSION",
            reason="The signature does not reference a trusted QDS session.",
            authenticated_verifier=authenticated_verifier_id,
        )
    if consume and row.consumed_at is not None:
        return _verification_failure(
            code="REPLAY_REJECTED",
            reason="This one-time QDS session nonce has already been consumed.",
            row=row,
            document_hash_match=sha512_hex(document) == row.document_hash,
            structural_valid=True,
            replay_detected=True,
            authenticated_verifier=authenticated_verifier_id,
        )
    result = verify_against_evidence(
        row=row,
        signature=signature,
        evidence=evidence,
        document_hash=sha512_hex(document),
        authenticated_verifier_id=authenticated_verifier_id,
    )
    if consume and result.status == "VALID":
        with session_scope() as db:
            consumed = db.execute(
                update(QDSSession)
                .where(QDSSession.id == row.id, QDSSession.consumed_at.is_(None))
                .values(consumed_at=datetime.now(timezone.utc))
            )
            if consumed.rowcount != 1:
                return _verification_failure(
                    code="REPLAY_REJECTED",
                    reason="A concurrent verification already consumed this one-time signature.",
                    row=row,
                    document_hash_match=True,
                    structural_valid=True,
                    replay_detected=True,
                    authenticated_verifier=authenticated_verifier_id,
                )
    return result


def list_sessions(limit: int = 30) -> list[dict[str, Any]]:
    with session_scope() as db:
        rows = list(db.scalars(select(QDSSession).order_by(QDSSession.created_at.desc()).limit(limit)))
        return [
            {
                "id": row.id,
                "signer_id": row.signer_id,
                "verifier_id": row.verifier_id,
                "document_name": row.document_name,
                "created_at": row.created_at.isoformat(),
                "consumed": row.consumed_at is not None,
                "quantum_engine": row.quantum_engine,
                "quantum_target": row.quantum_target,
                "prepared_quantum_states": row.prepared_state_count,
            }
            for row in rows
        ]


def get_session_summary(session_id: str) -> dict[str, Any]:
    row, signature, evidence = load_qds_session(session_id)
    return {
        "id": row.id,
        "signer_id": row.signer_id,
        "verifier_id": row.verifier_id,
        "document_name": row.document_name,
        "document_hash": row.document_hash,
        "created_at": row.created_at.isoformat(),
        "consumed": row.consumed_at is not None,
        "quantum": {
            "engine": row.quantum_engine,
            "target": row.quantum_target,
            "maximum_circuit_width": row.max_circuit_width,
        },
        "noise_parameters": evidence.get("noise_parameters", {}),
        "baseline": evidence.get("baseline", {}),
        "quantum_status": evidence.get("quantum_status", {}),
        "signature": signature,
    }


def get_session_quantum_status(session_id: str) -> dict[str, Any]:
    _, _, evidence = load_qds_session(session_id)
    status = evidence.get("quantum_status")
    if not isinstance(status, dict) or not status:
        raise LookupError("Quantum status is unavailable for this legacy QDS session")
    return status
