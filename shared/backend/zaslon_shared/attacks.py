from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import random
import time
import uuid
from typing import Any

from scipy.stats import fisher_exact

from .adversary import adversary_model_for_attack
from .config import settings
from .db import AttackExperiment, QDSSession, session_scope
from .protocol import load_qds_session, verify_against_evidence
from .provenance import canonical_sha512, runtime_provenance
from .quantum import (
    Basis,
    NoiseConfig,
    Pauli,
    create_quantum_engine,
    derive_simulation_seed,
    run_channel_diagnostic,
)
from .schemas import AttackRunRequest
from .security_analysis import holm_adjust, restricted_binomial_forgery_analysis


VALID_TARGETS = {
    "BASELINE": "PROTOCOL",
    "INTERCEPT_RESEND": "QUANTUM_CHANNEL",
    "ENTANGLEMENT_MANIPULATION": "ENTANGLEMENT_CHANNEL",
    "PAULI_MANIPULATION": "QUANTUM_STATE",
    "BELL_RESULT_MANIPULATION": "BELL_RESULTS",
    "CORRECTION_MITM": "CLASSICAL_CORRECTION_CHANNEL",
    "SIGNATURE_FORGERY": "SIGNATURE",
    "PARTIAL_SIGNATURE_TAMPERING": "SIGNATURE",
    "FULL_FORGERY": "SIGNATURE",
    "REPLAY": "PROTOCOL_SESSION",
    "IMPERSONATION": "IDENTITY",
}


def _experiment_attestation_secret() -> str:
    secret = (
        settings.artifact_attestation_key
        or settings.job_payload_key
        or settings.attack_api_key
    )
    if len(secret) < 24:
        raise RuntimeError("A server-side experiment attestation key is required")
    return secret


def _experiment_attestation_key_id() -> str:
    return f"local-attestation-{hashlib.sha256(_experiment_attestation_secret().encode()).hexdigest()[:16]}"


def _experiment_record_tag(result: dict[str, Any]) -> str:
    secret = _experiment_attestation_secret()
    unsigned = {key: value for key, value in result.items() if key != "record_integrity"}
    integrity = result.get("record_integrity")
    authenticated: Any = unsigned
    if isinstance(integrity, dict) and integrity.get("scheme") == (
        "HMAC-SHA512-TRUSTED-SERVER-RECORD-V2"
    ):
        authenticated = {
            "content": unsigned,
            "integrity_metadata": {
                key: value for key, value in integrity.items() if key != "tag"
            },
        }
    canonical = json.dumps(
        authenticated, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha512).hexdigest()


def _validate_experiment_record(result: dict[str, Any]) -> dict[str, Any]:
    integrity = result.get("record_integrity")
    unsigned = {key: value for key, value in result.items() if key != "record_integrity"}
    expected_content_digest = canonical_sha512(unsigned)
    allowed_schemes = {
        "HMAC-SHA512-TRUSTED-SERVER-RECORD",
        "HMAC-SHA512-TRUSTED-SERVER-RECORD-V2",
    }
    valid = isinstance(integrity, dict) and integrity.get("scheme") in allowed_schemes
    if valid:
        valid = hmac.compare_digest(
            str(integrity.get("content_sha512", "")), expected_content_digest
        ) and hmac.compare_digest(
            str(integrity.get("tag", "")), _experiment_record_tag(result)
        )
    if valid and integrity.get("scheme") == "HMAC-SHA512-TRUSTED-SERVER-RECORD-V2":
        valid = (
            hmac.compare_digest(
                str(integrity.get("key_id", "")), _experiment_attestation_key_id()
            )
            and integrity.get("scope")
            == "EXPERIMENT_CONTENT_AND_INTEGRITY_METADATA_EXCEPT_TAG"
            and integrity.get("tamper_evident_against_trusted_database_copy") is True
            and integrity.get("external_immutability_claim") is False
        )
    if not valid:
        raise RuntimeError("EXPERIMENT_RECORD_INTEGRITY_FAILED")
    if integrity.get("scheme") == "HMAC-SHA512-TRUSTED-SERVER-RECORD":
        result["record_integrity"] = {
            "scheme": "HMAC-SHA512-TRUSTED-SERVER-RECORD",
            "content_sha512": integrity["content_sha512"],
            "tag": integrity["tag"],
            "metadata_authentication": "LEGACY_CONTENT_ONLY",
        }
    return result


def _experiment_id() -> str:
    return f"EXP-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


def _blind_detection(
    baseline: dict[str, Any], observed: dict[str, Any]
) -> dict[str, Any]:
    base_n = int(baseline.get("usable_measurements") or 0)
    base_e = int(baseline.get("mismatches") or 0)
    obs_n = int(observed.get("usable_measurements") or 0)
    obs_e = int(observed.get("mismatches") or 0)
    if min(base_n, obs_n) == 0:
        return {
            "decision": "INCONCLUSIVE",
            "test_name": "Fisher exact test",
            "p_value": None,
            "alpha": 0.01,
            "reason": "Insufficient teleportation observations.",
        }
    table = [[obs_e, max(0, obs_n - obs_e)], [base_e, max(0, base_n - base_e)]]
    _, p_value = fisher_exact(table, alternative="greater")
    observed_rate = obs_e / obs_n
    baseline_rate = base_e / base_n
    detected = p_value < 0.01 and observed_rate > baseline_rate
    return {
        "decision": "ATTACK_DETECTED" if detected else "NO_ATTACK_DETECTED",
        "test_name": "One-sided Fisher exact test",
        "p_value": float(p_value),
        "alpha": 0.01,
        "reason": (
            "Observed teleportation errors are statistically elevated over the honest baseline."
            if detected
            else "Observed teleportation errors are not statistically elevated over the honest baseline."
        ),
    }


def _choose_pauli(rng: random.Random, requested: str) -> Pauli:
    normalized = requested.upper()
    if normalized == "RANDOM":
        return rng.choice(["X", "Y", "Z"])
    if normalized not in {"X", "Y", "Z"}:
        raise ValueError("INVALID_PAULI_OPERATION")
    return normalized  # type: ignore[return-value]


def _diagnostic_family_detection(
    honest: dict[str, Any], attacked: dict[str, Any], *, alpha: float = 0.01
) -> dict[str, Any]:
    raw_values: list[float] = []
    basis_rows: list[dict[str, Any]] = []
    for basis in ("Z", "X"):
        base = honest["bases"][basis]
        observed = attacked["bases"][basis]
        table = [
            [int(observed["errors"]), int(observed["shots"]) - int(observed["errors"])],
            [int(base["errors"]), int(base["shots"]) - int(base["errors"])],
        ]
        _, p_value = fisher_exact(table, alternative="greater")
        raw_values.append(float(p_value))
        basis_rows.append({
            "basis": basis,
            "honest_error_rate": base["error_rate"],
            "attacked_error_rate": observed["error_rate"],
        })
    corrected = holm_adjust(raw_values, alpha=alpha)
    for row, statistics in zip(basis_rows, corrected, strict=True):
        row.update(statistics)
    detected = any(
        row["decision"] == "REJECT_NULL"
        and row["attacked_error_rate"] > row["honest_error_rate"]
        for row in basis_rows
    )
    return {
        "decision": "ATTACK_DETECTED" if detected else "NO_ATTACK_DETECTED",
        "test_name": "One-sided Fisher exact tests with Holm family-wise correction",
        "family_size": 2,
        "alpha": alpha,
        "correction": "HOLM_FWER",
        "basis_tests": basis_rows,
        "reason": (
            "At least one pre-declared diagnostic basis has an adjusted significant error increase."
            if detected else
            "No pre-declared diagnostic basis has an adjusted significant error increase."
        ),
        "p_value_semantics": (
            "Tail probabilities under the honest-channel null; not attack probabilities."
        ),
    }


def _run_channel_attack(
    *,
    request: AttackRunRequest,
    row: QDSSession,
    signature: dict[str, Any],
    original_evidence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rng = random.Random(derive_simulation_seed(request.seed, "ATTACK_SELECTION"))
    engine = create_quantum_engine(
        settings.quantum_engine,
        derive_simulation_seed(request.seed, "ATTACK_QUANTUM_EXECUTION"),
    )
    evidence = deepcopy(original_evidence)
    noise = NoiseConfig(**evidence.get("noise_parameters", {}))
    fidelities: list[float] = []
    attacked_states = 0
    total_states = 0
    classical_attack_trace: list[dict[str, Any]] = []

    declaration_map = {item["position"]: item for item in signature["declarations"]}
    for candidate in evidence["candidates"]:
        position = int(candidate["position"])
        declaration = declaration_map[position]
        digest_bit = int(declaration["digest_bit"])
        states = candidate["values"][str(digest_bit)]
        for state in states:
            total_states += 1
            selected = rng.random() < request.attack_strength
            attacked_states += int(selected)
            intercept = selected and request.attack_type == "INTERCEPT_RESEND"
            eve_basis: Basis = "X" if rng.getrandbits(1) else "Z"
            entanglement_pauli: Pauli = "I"
            output_pauli: Pauli = "I"
            correction_flip_mask = 0
            if selected and request.attack_type == "ENTANGLEMENT_MANIPULATION":
                entanglement_pauli = _choose_pauli(
                    rng, str(request.parameters.get("pauli_operation", "RANDOM"))
                )
            if selected and request.attack_type == "PAULI_MANIPULATION":
                output_pauli = _choose_pauli(
                    rng, str(request.parameters.get("pauli_operation", "RANDOM"))
                )
            if selected and request.attack_type in {
                "BELL_RESULT_MANIPULATION", "CORRECTION_MITM"
            }:
                correction_flip_mask = rng.choice([1, 2, 3])
            result = engine.teleport_and_measure(
                bit=int(state["key_bit"]),
                preparation_basis=str(state.get("basis", "Z")),
                measurement_basis=str(state.get("basis", "Z")),
                intercept=intercept,
                eve_basis=eve_basis,
                entanglement_pauli=entanglement_pauli,
                correction_flip_mask=correction_flip_mask,
                output_pauli=output_pauli,
                noise=noise,
            )
            state["bob_outcome"] = result.bob_outcome
            state["bell_bits"] = list(result.bell_bits)
            state["fidelity"] = result.fidelity
            if selected and request.attack_type in {"BELL_RESULT_MANIPULATION", "CORRECTION_MITM"}:
                original = list(result.bell_bits)
                modified = [
                    original[0] ^ ((correction_flip_mask >> 1) & 1),
                    original[1] ^ (correction_flip_mask & 1),
                ]
                if len(classical_attack_trace) < 32:
                    if request.attack_type == "BELL_RESULT_MANIPULATION":
                        classical_attack_trace.append({
                            "stage": "INSIDE_ALICE_LOGICAL_BOUNDARY_BEFORE_TRANSMISSION",
                            "alice_measurement_bits": original,
                            "alice_transmitted_bits": modified,
                            "bob_received_bits": modified,
                            "mask": correction_flip_mask,
                        })
                    else:
                        classical_attack_trace.append({
                            "stage": "ALICE_TO_BOB_CLASSICAL_CORRECTION_CHANNEL",
                            "alice_measurement_bits": original,
                            "alice_transmitted_bits": original,
                            "mitm_modified_bits": modified,
                            "bob_received_bits": modified,
                            "mask": correction_flip_mask,
                        })
            if result.fidelity is not None:
                fidelities.append(result.fidelity)

    verification = verify_against_evidence(
        row=row,
        signature=signature,
        evidence=evidence,
        document_hash=row.document_hash,
    ).model_dump()
    diagnostic_pauli: Pauli = "I"
    diagnostic_entanglement_pauli: Pauli = "I"
    diagnostic_intercept = request.attack_type == "INTERCEPT_RESEND"
    diagnostic_correction_mask = 0
    if request.attack_type == "PAULI_MANIPULATION":
        diagnostic_pauli = _choose_pauli(
            random.Random(derive_simulation_seed(request.seed, "DIAGNOSTIC_PAULI")),
            str(request.parameters.get("pauli_operation", "RANDOM")),
        )
    elif request.attack_type == "ENTANGLEMENT_MANIPULATION":
        diagnostic_entanglement_pauli = _choose_pauli(
            random.Random(derive_simulation_seed(request.seed, "DIAGNOSTIC_PAULI")),
            str(request.parameters.get("pauli_operation", "RANDOM")),
        )
    elif request.attack_type in {"BELL_RESULT_MANIPULATION", "CORRECTION_MITM"}:
        diagnostic_correction_mask = 3
    diagnostic_engine = create_quantum_engine(
        settings.quantum_engine,
        derive_simulation_seed(request.seed, "CHANNEL_DIAGNOSTIC_QUANTUM"),
    )
    diagnostic = run_channel_diagnostic(
        diagnostic_engine,
        shots_per_basis=int(request.parameters.get("diagnostic_shots_per_basis", 128)),
        master_seed=request.seed,
        attack_strength=request.attack_strength,
        output_pauli=diagnostic_pauli,
        entanglement_pauli=diagnostic_entanglement_pauli,
        intercept=diagnostic_intercept,
        correction_flip_mask=diagnostic_correction_mask,
        noise=noise,
        disturbance_threshold=float(
            request.parameters.get("diagnostic_disturbance_threshold", 0.05)
        ),
    )
    honest_diagnostic_engine = create_quantum_engine(
        settings.quantum_engine,
        derive_simulation_seed(request.seed, "CHANNEL_DIAGNOSTIC_HONEST_QUANTUM"),
    )
    honest_diagnostic = run_channel_diagnostic(
        honest_diagnostic_engine,
        shots_per_basis=int(request.parameters.get("diagnostic_shots_per_basis", 128)),
        master_seed=derive_simulation_seed(request.seed, "CHANNEL_DIAGNOSTIC_HONEST_SELECTION"),
        attack_strength=0.0,
        noise=noise,
        disturbance_threshold=float(
            request.parameters.get("diagnostic_disturbance_threshold", 0.05)
        ),
    )
    diagnostic_statistics = _diagnostic_family_detection(honest_diagnostic, diagnostic)
    observations = {
        "total_disclosed_states": total_states,
        "attacked_states": attacked_states,
        "usable_measurements": verification["usable_measurements"],
        "mismatches": verification["mismatches"],
        "mismatch_rate": verification["mismatch_rate"],
        "basis_statistics": verification.get("basis_statistics"),
        "mean_state_fidelity": sum(fidelities) / len(fidelities) if fidelities else None,
        "normal_noise_parameters": noise.model_dump(),
        "channel_diagnostic": diagnostic,
        "honest_channel_diagnostic": honest_diagnostic,
        "channel_diagnostic_statistics": diagnostic_statistics,
    }
    if request.attack_type in {"BELL_RESULT_MANIPULATION", "CORRECTION_MITM"}:
        observations["classical_attack_boundary"] = (
            "ALICE_INTERNAL_BELL_RESULT_OUTPUT"
            if request.attack_type == "BELL_RESULT_MANIPULATION"
            else "ALICE_TO_BOB_CLASSICAL_CORRECTION_CHANNEL"
        )
        observations["classical_bit_trace_samples"] = classical_attack_trace
        observations["quantum_effect_equivalence_note"] = (
            "For a given XOR mask these two attack locations can induce the same final "
            "Pauli correction error, although their trust boundary and audit trace differ."
        )
    return verification, {
        "observations": observations,
        "quantum": engine.metadata.model_dump(),
    }


def _partially_tamper_signature(
    signature: dict[str, Any], strength: float, seed: int
) -> tuple[dict[str, Any], list[int]]:
    rng = random.Random(derive_simulation_seed(seed, "PARTIAL_SIGNATURE_TAMPERING"))
    candidate = deepcopy(signature)
    declarations = candidate["declarations"]
    count = round(len(declarations) * strength)
    positions = rng.sample(range(len(declarations)), count) if count else []
    for index in positions:
        declaration = declarations[index]
        declaration["key_bits"] = [rng.getrandbits(1) for _ in declaration["key_bits"]]
    candidate["signature_declarations"] = deepcopy(candidate["declarations"])
    return candidate, positions


def _forge_signature(
    signature: dict[str, Any], strength: float, seed: int
) -> tuple[dict[str, Any], list[int]]:
    """Backward-compatible name for the now accurately classified tampering model."""
    return _partially_tamper_signature(signature, strength, seed)


def _full_forgery(
    public_signature: dict[str, Any],
    *,
    seed: int,
    scenario: str,
    modified_message: str | None = None,
) -> dict[str, Any]:
    """Build an independent forged artifact without copying legitimate declarations.

    OBSERVED_SIGNATURE permits the public envelope (including public session identifiers)
    but still generates every declaration independently. UNOBSERVED creates independent
    identifiers as well. Neither scenario reads legitimate declaration key bits.
    """
    normalized = scenario.strip().upper()
    if normalized not in {"UNOBSERVED", "OBSERVED_SIGNATURE", "MODIFIED_MESSAGE"}:
        raise ValueError("full_forgery_scenario must be UNOBSERVED, OBSERVED_SIGNATURE, or MODIFIED_MESSAGE")
    rng = random.Random(derive_simulation_seed(seed, f"FULL_FORGERY|{normalized}"))
    source_hash = str(public_signature["document_hash"])
    document_hash = (
        hashlib.sha512((modified_message or "independent forged message").encode("utf-8")).hexdigest()
        if normalized == "MODIFIED_MESSAGE"
        else source_hash
    )
    states_per_candidate = int(public_signature["quantum_parameters"]["states_per_candidate"])
    digest_bits = "".join(f"{int(char, 16):04b}" for char in document_hash)
    declarations = [
        {
            "position": position,
            "digest_bit": int(digest_bits[position]),
            "key_bits": [rng.getrandbits(1) for _ in range(states_per_candidate)],
            "encoding": "COMPUTATIONAL_BASIS",
        }
        for position in range(512)
    ]
    observed_envelope = normalized in {"OBSERVED_SIGNATURE", "MODIFIED_MESSAGE"}
    forged_id = (
        public_signature["signature_id"]
        if observed_envelope
        else f"FORGED-{rng.getrandbits(64):016X}"
    )
    forged_session = (
        public_signature["session_id"]
        if observed_envelope
        else f"QDS-FORGED-{rng.getrandbits(64):016X}"
    )
    forged_nonce = (
        public_signature["nonce"]
        if observed_envelope
        else f"{rng.getrandbits(256):064x}"
    )
    # Construct field-by-field. In particular, no declaration or key-bit collection
    # from the legitimate artifact is reused.
    return {
        "format": "zaslon.qds.signature.v2",
        "version": "2.0",
        "algorithm": "ZASLON-TELEPORTATION-QDS-RESEARCH",
        "protocol": public_signature["protocol"],
        "protocol_version": public_signature["protocol_version"],
        "signature_id": forged_id,
        "session_id": forged_session,
        "signer_id": public_signature["signer_id"],
        "verifier_id": public_signature["verifier_id"],
        "document_name": (
            "forged-message.bin" if normalized == "MODIFIED_MESSAGE" else public_signature["document_name"]
        ),
        "document_hash": document_hash,
        "hash_algorithm": "SHA-512",
        "nonce": forged_nonce,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prepared_quantum_states": public_signature["prepared_quantum_states"],
        "disclosed_quantum_states": public_signature["disclosed_quantum_states"],
        "maximum_simultaneous_circuit_qubits": public_signature[
            "maximum_simultaneous_circuit_qubits"
        ],
        "verification_policy": dict(public_signature["verification_policy"]),
        "verification_thresholds": dict(public_signature["verification_thresholds"]),
        "quantum_parameters": dict(public_signature["quantum_parameters"]),
        "teleportation_metadata": dict(public_signature["teleportation_metadata"]),
        "quantum_diagnostic": dict(public_signature["quantum_diagnostic"]),
        "effective_channel_diagnostic": dict(
            public_signature.get("effective_channel_diagnostic") or {}
        ),
        "bell_state_analysis": dict(public_signature["bell_state_analysis"]),
        "noise_parameters": dict(public_signature["noise_parameters"]),
        "quantum_status": dict(public_signature["quantum_status"]),
        "declarations": declarations,
        "signature_declarations": [dict(item, key_bits=list(item["key_bits"])) for item in declarations],
    }


def _wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    if trials <= 0:
        raise ValueError("Forgery trial count must be positive")
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def run_attack(request: AttackRunRequest) -> dict[str, Any]:
    expected_target = VALID_TARGETS[request.attack_type]
    if request.target != expected_target:
        raise ValueError(f"INVALID_ATTACK_TARGET: expected {expected_target}")
    started = time.perf_counter()
    row, public_signature, private_evidence = load_qds_session(request.qds_session_id)
    experiment_id = _experiment_id()
    baseline = private_evidence["baseline"]
    quantum = {
        "engine": row.quantum_engine,
        "target": row.quantum_target,
        "maximum_circuit_width": row.max_circuit_width,
    }
    extra: dict[str, Any] = {}

    if request.attack_type == "BASELINE":
        verification = verify_against_evidence(
            row=row,
            signature=public_signature,
            evidence=private_evidence,
            document_hash=row.document_hash,
        ).model_dump()
        observations = {
            "total_disclosed_states": len(public_signature["declarations"])
            * settings.states_per_candidate,
            "attacked_states": 0,
            "usable_measurements": verification["usable_measurements"],
            "mismatches": verification["mismatches"],
            "mismatch_rate": verification["mismatch_rate"],
            "basis_statistics": verification.get("basis_statistics"),
            "mean_state_fidelity": baseline.get("mean_teleportation_fidelity"),
        }
        detection = _blind_detection(baseline, observations)
    elif request.attack_type in {
        "INTERCEPT_RESEND",
        "ENTANGLEMENT_MANIPULATION",
        "PAULI_MANIPULATION",
        "BELL_RESULT_MANIPULATION",
        "CORRECTION_MITM",
    }:
        verification, channel = _run_channel_attack(
            request=request,
            row=row,
            signature=public_signature,
            original_evidence=private_evidence,
        )
        observations = channel["observations"]
        quantum = channel["quantum"]
        detection = _blind_detection(baseline, observations)
        diagnostic = observations["channel_diagnostic"]
        diagnostic_statistics = observations["channel_diagnostic_statistics"]
        if (
            detection["decision"] != "ATTACK_DETECTED"
            and diagnostic_statistics["decision"] == "ATTACK_DETECTED"
        ):
            detection = diagnostic_statistics
        if request.attack_type == "BELL_RESULT_MANIPULATION":
            extra["bell_result_attack_interpretation"] = {
                "bell_pair_creation": "VALID",
                "initial_entanglement": private_evidence.get("quantum_status", {})
                .get("entanglement", {})
                .get("status", "UNKNOWN"),
                "attacked_component": "CLASSICAL_BELL_MEASUREMENT_RESULTS",
                "original_bell_preparation_failed": False,
                "teleportation_verification": verification["status"],
                "attack_detection": detection["decision"],
                "reason": (
                    "The attack modifies Alice's classical Bell-measurement information used "
                    "for Bob's Pauli correction. It does not retroactively invalidate the "
                    "verified Bell-pair preparation."
                ),
            }
    elif request.attack_type in {"SIGNATURE_FORGERY", "PARTIAL_SIGNATURE_TAMPERING"}:
        original_snapshot = json.dumps(public_signature, sort_keys=True, separators=(",", ":"))
        forged, positions = _partially_tamper_signature(
            public_signature, request.attack_strength, request.seed
        )
        verification = verify_against_evidence(
            row=row,
            signature=forged,
            evidence=private_evidence,
            document_hash=row.document_hash,
        ).model_dump()
        observations = {
            "total_declarations": len(public_signature["declarations"]),
            "forged_declarations": len(positions),
            "usable_measurements": verification["usable_measurements"],
            "mismatches": verification["mismatches"],
            "mismatch_rate": verification["mismatch_rate"],
        }
        detection = {
            "decision": "NOT_APPLICABLE",
            "test_name": None,
            "p_value": None,
            "alpha": None,
            "reason": "The channel anomaly detector is not used to classify a classical declaration forgery.",
        }
        trial_count = int(request.parameters.get("forgery_trials", 64))
        if not 16 <= trial_count <= 1000:
            raise ValueError("forgery_trials must be between 16 and 1000")
        accepted = 0
        for trial in range(trial_count):
            trial_signature, _ = _partially_tamper_signature(
                public_signature, request.attack_strength, request.seed + trial + 1
            )
            trial_result = verify_against_evidence(
                row=row, signature=trial_signature, evidence=private_evidence,
                document_hash=row.document_hash,
            )
            accepted += int(trial_result.status == "VALID")
        extra = {
            "forgery": {
                "experiment_class": "PARTIAL_SIGNATURE_TAMPERING",
                "legacy_attack_name_used": request.attack_type == "SIGNATURE_FORGERY",
                "strategy": "MODIFY_SELECTED_DECLARATIONS_IN_OBSERVED_VALID_ARTIFACT",
                "independent_full_forgery": False,
                "outcome": "FORGERY_ACCEPTED"
                if verification["status"] == "VALID"
                else "FORGERY_REJECTED"
                if verification["status"] == "INVALID"
                else "FORGERY_UNVERIFIABLE",
                "success_estimate": {
                    "method": "Empirical repeated partial tampering",
                    "accepted_trials": accepted,
                    "trials": trial_count,
                    "estimated_probability": accepted / trial_count,
                    "wilson_95_percent_interval": _wilson_interval(accepted, trial_count),
                },
                "original_artifact_unchanged": original_snapshot
                == json.dumps(public_signature, sort_keys=True, separators=(",", ":")),
            }
        }
    elif request.attack_type == "FULL_FORGERY":
        scenario = str(request.parameters.get("scenario", "UNOBSERVED"))
        modified_message = request.parameters.get("modified_message")
        forged = _full_forgery(
            public_signature,
            seed=request.seed,
            scenario=scenario,
            modified_message=str(modified_message) if modified_message is not None else None,
        )
        verification = verify_against_evidence(
            row=row,
            signature=forged,
            evidence=private_evidence,
            document_hash=row.document_hash,
        ).model_dump()
        observations = {
            "total_declarations": len(forged["declarations"]),
            "independently_generated_declarations": len(forged["declarations"]),
            "legitimate_declaration_key_bits_copied": 0,
            "usable_measurements": verification["usable_measurements"],
            "mismatches": verification["mismatches"],
            "mismatch_rate": verification["mismatch_rate"],
        }
        detection = {
            "decision": "ATTACK_DETECTED" if verification["status"] == "INVALID" else "INCONCLUSIVE",
            "test_name": "Fail-closed artifact/session binding",
            "p_value": None,
            "alpha": None,
            "reason": (
                "The independently generated artifact failed trusted session/signature binding."
                if verification["status"] == "INVALID"
                else "The independent-forgery outcome was not rejected conclusively."
            ),
        }
        trial_count = int(request.parameters.get("forgery_trials", 64))
        if not 16 <= trial_count <= 1000:
            raise ValueError("forgery_trials must be between 16 and 1000")
        accepted = 0
        for trial in range(trial_count):
            trial_signature = _full_forgery(
                public_signature,
                seed=request.seed + trial + 1,
                scenario=scenario,
                modified_message=str(modified_message) if modified_message is not None else None,
            )
            trial_result = verify_against_evidence(
                row=row,
                signature=trial_signature,
                evidence=private_evidence,
                document_hash=row.document_hash,
            )
            accepted += int(trial_result.status == "VALID")
        extra = {
            "forgery": {
                "experiment_class": "FULL_FORGERY",
                "adversary_model": "EXTERNAL_FORGER",
                "scenario": scenario.strip().upper(),
                "construction": "INDEPENDENT_FIELD_BY_FIELD_WITH_RANDOM_DECLARATIONS",
                "started_from_legitimate_artifact_copy": False,
                "legitimate_declaration_key_bits_available": False,
                "public_envelope_available": scenario.strip().upper() != "UNOBSERVED",
                "outcome": "FORGERY_ACCEPTED" if verification["status"] == "VALID" else "FORGERY_REJECTED",
                "empirical_success_estimate": {
                    "label": "EMPIRICAL ESTIMATE UNDER DECLARED EXTERNAL-FORGER MODEL",
                    "accepted_trials": accepted,
                    "trials": trial_count,
                    "estimated_probability": accepted / trial_count,
                    "wilson_95_percent_interval": _wilson_interval(accepted, trial_count),
                    "universal_security_bound": False,
                },
                "theoretical_or_reference_analysis": restricted_binomial_forgery_analysis(
                    signature_length=len(forged["declarations"]),
                    attacker_mismatch_probability=float(
                        request.parameters.get("attacker_mismatch_probability", 0.5)
                    ),
                    acceptance_threshold=row.verification_threshold,
                    independence_justified=bool(
                        request.parameters.get("iid_mismatch_assumption_justified", False)
                    ),
                    mismatch_probability_justified=bool(
                        request.parameters.get("attacker_probability_justified", False)
                    ),
                ),
            }
        }
    elif request.attack_type == "REPLAY":
        replay_detected = row.consumed_at is not None
        verification = {
            "status": "INVALID" if replay_detected else "UNVERIFIABLE",
            "reason": "Previously consumed session nonce was replayed."
            if replay_detected
            else "Replay requires a previously consumed legitimate session.",
            "document_hash_match": True,
            "usable_measurements": 0,
            "mismatches": 0,
            "mismatch_rate": None,
            "threshold": row.verification_threshold,
            "threshold_source": row.threshold_source,
            "replay_detected": replay_detected,
        }
        observations = {"nonce_previously_consumed": replay_detected}
        detection = {
            "decision": "ATTACK_DETECTED" if replay_detected else "INCONCLUSIVE",
            "test_name": "One-time nonce ledger check",
            "p_value": None,
            "alpha": None,
            "reason": verification["reason"],
        }
    else:  # IMPERSONATION
        forged_identity = deepcopy(public_signature)
        forged_identity["signer_id"] = str(
            request.parameters.get("claimed_signer_id", "Alice")
        ) + "-IMPERSONATED"
        verification = verify_against_evidence(
            row=row,
            signature=forged_identity,
            evidence=private_evidence,
            document_hash=row.document_hash,
        ).model_dump()
        observations = {"claimed_signer": forged_identity["signer_id"], "trusted_signer": row.signer_id}
        detection = {
            "decision": "ATTACK_DETECTED",
            "test_name": "Authenticated participant binding",
            "p_value": None,
            "alpha": None,
            "reason": "Claimed signer does not match the authenticated QDS session owner.",
        }

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    result = {
        "experiment_id": experiment_id,
        "qds_session_id": row.id,
        "status": "COMPLETED",
        "attack": {
            "type": request.attack_type,
            "target": request.target,
            "strength": request.attack_strength,
            "seed": request.seed,
            "parameters": request.parameters,
            "experiment_semantics": "COUNTERFACTUAL_PROTOCOL_EXECUTION_WITH_DECLARED_ATTACKER",
            "does_not_modify_past_measured_quantum_state": True,
        },
        "adversary_model": adversary_model_for_attack(request.attack_type),
        "verification": verification,
        "detection": detection,
        "observations": observations,
        "baseline": baseline,
        "security_policy": {
            "verification_threshold": row.verification_threshold,
            "source": row.threshold_source,
            "claim": "Configured experimental parameter; not a proven security bound.",
        },
        "normal_noise_parameters": private_evidence.get("noise_parameters", {}),
        "quantum_status": private_evidence.get("quantum_status", {}),
        "execution": {
            "quantum": quantum,
            "duration_ms": duration_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        **extra,
    }
    result["reproducibility"] = runtime_provenance(
        component="ATTACK_EXPERIMENT",
        seed=request.seed,
        quantum=quantum,
    )
    result["record_integrity"] = {
        "scheme": "HMAC-SHA512-TRUSTED-SERVER-RECORD-V2",
        "key_id": _experiment_attestation_key_id(),
        "content_sha512": canonical_sha512(result),
        "scope": "EXPERIMENT_CONTENT_AND_INTEGRITY_METADATA_EXCEPT_TAG",
        "tamper_evident_against_trusted_database_copy": True,
        "external_immutability_claim": False,
    }
    result["record_integrity"]["tag"] = _experiment_record_tag(result)
    with session_scope() as db:
        db.add(
            AttackExperiment(
                id=experiment_id,
                qds_session_id=row.id,
                attack_type=request.attack_type,
                target=request.target,
                strength=request.attack_strength,
                seed=request.seed,
                status="COMPLETED",
                result_json=json.dumps(result, separators=(",", ":")),
            )
        )
    return result


def list_experiments(limit: int = 20) -> list[dict[str, Any]]:
    from sqlalchemy import select

    with session_scope() as db:
        rows = list(
            db.scalars(
                select(AttackExperiment)
                .order_by(AttackExperiment.created_at.desc())
                .limit(limit)
            )
        )
        return [_validate_experiment_record(json.loads(row.result_json)) for row in rows]


def get_experiment(experiment_id: str) -> dict[str, Any]:
    with session_scope() as db:
        row = db.get(AttackExperiment, experiment_id)
        if row is None:
            raise LookupError("Attack experiment not found")
        return _validate_experiment_record(json.loads(row.result_json))
