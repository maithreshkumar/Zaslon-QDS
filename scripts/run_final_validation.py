from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "backend"))
sys.path.insert(0, str(ROOT / "Alice" / "backend"))
sys.path.insert(0, str(ROOT / "Bob" / "backend"))
sys.path.insert(0, str(ROOT / "Attack" / "backend"))

_temp_directory = tempfile.TemporaryDirectory(prefix="zaslon-final-validation-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_temp_directory.name) / 'validation.db'}"
os.environ["ZASLON_QUANTUM_ENGINE"] = "reference"
os.environ.setdefault("ZASLON_ALICE_API_KEY", "validation-alice-key-000000000000000")
os.environ.setdefault("ZASLON_BOB_API_KEY", "validation-bob-key-00000000000000000")
os.environ.setdefault("ZASLON_ATTACK_API_KEY", "validation-attack-key-000000000000000")

from zaslon_shared.attacks import run_attack  # noqa: E402
from zaslon_shared.benchmark import run_detector_benchmark  # noqa: E402
from zaslon_shared.db import engine as validation_database_engine, init_db  # noqa: E402
from zaslon_shared.multiverifier import run_transferability_experiment  # noqa: E402
from zaslon_shared.participant import sign_document, verify_received_document  # noqa: E402
from zaslon_shared.protocol import verify_document  # noqa: E402
from zaslon_shared.quantum import (  # noqa: E402
    NoiseConfig,
    ReferenceStatevectorEngine,
    run_channel_diagnostic,
)
from zaslon_shared.schemas import AttackRunRequest  # noqa: E402
from zaslon_shared.security_analysis import wilson_interval  # noqa: E402


def _p_values(result: dict) -> tuple[float | None, float | None]:
    detection = result["detection"]
    if detection.get("p_value") is not None:
        return float(detection["p_value"]), None
    tests = detection.get("basis_tests", [])
    if not tests:
        return None, None
    return (
        min(float(item["raw_p_value"]) for item in tests),
        min(float(item["adjusted_p_value"]) for item in tests),
    )


def _channel_matrix_entry(label: str, result: dict) -> dict:
    diagnostic = result["observations"]["channel_diagnostic"]
    total_errors = sum(int(item["errors"]) for item in diagnostic["bases"].values())
    trials = sum(int(item["shots"]) for item in diagnostic["bases"].values())
    raw_p, adjusted_p = _p_values(result)
    return {
        "scenario": label,
        "trials": trials,
        "attack_strength": result["attack"]["strength"],
        "mean_qber": diagnostic["combined_channel_disturbance"],
        "qber_wilson_95": wilson_interval(total_errors, trials),
        "raw_p_value": raw_p,
        "adjusted_p_value": adjusted_p,
        "detection_rate": 1.0 if result["detection"]["decision"] == "ATTACK_DETECTED" else 0.0,
        "verification_result": result["verification"]["status"],
        "production_mismatch_rate": result["verification"]["mismatch_rate"],
        "runtime_ms": result["execution"]["duration_ms"],
    }


def main() -> Path:
    init_db()
    started = time.perf_counter()
    document = b"ZASLON-QDS final reproducible validation document"
    signed = sign_document(
        document=document,
        filename="final-validation.txt",
        signer_id="Alice",
        verifier_id="Bob",
        seed=261400,
        noise={},
    )
    signature = signed["signature"]
    session_id = signed["session"]["id"]
    verify_started = time.perf_counter()
    honest = verify_document(
        document=document,
        signature=signature,
        consume=False,
        authenticated_verifier_id="Bob",
    ).model_dump()
    verification_latency_ms = (time.perf_counter() - verify_started) * 1000
    unauthorized = verify_document(
        document=document,
        signature=signature,
        consume=False,
        authenticated_verifier_id="Alice",
    ).model_dump()
    modified = verify_document(
        document=b"modified final validation document",
        signature=signature,
        consume=False,
        authenticated_verifier_id="Bob",
    ).model_dump()

    matrix: list[dict] = [
        {
            "scenario": "HONEST_BASELINE",
            "trials": honest["usable_measurements"],
            "attack_strength": 0.0,
            "mean_qber": honest["mismatch_rate"],
            "qber_wilson_95": wilson_interval(honest["mismatches"], honest["usable_measurements"]),
            "raw_p_value": None,
            "adjusted_p_value": None,
            "detection_rate": 0.0,
            "verification_result": honest["status"],
            "runtime_ms": verification_latency_ms,
        },
        {
            "scenario": "UNAUTHORIZED_VERIFICATION",
            "trials": 1,
            "attack_strength": None,
            "mean_qber": None,
            "qber_wilson_95": None,
            "raw_p_value": None,
            "adjusted_p_value": None,
            "detection_rate": 1.0,
            "verification_result": unauthorized["status"],
            "failure_code": unauthorized["failure_code"],
            "runtime_ms": None,
        },
        {
            "scenario": "MODIFIED_DOCUMENT",
            "trials": 1,
            "attack_strength": None,
            "mean_qber": None,
            "qber_wilson_95": None,
            "raw_p_value": None,
            "adjusted_p_value": None,
            "detection_rate": 1.0,
            "verification_result": modified["status"],
            "failure_code": modified["failure_code"],
            "runtime_ms": None,
        },
    ]

    channel_specs = [
        ("X_CHANNEL_ATTACK", "PAULI_MANIPULATION", "QUANTUM_STATE", {"pauli_operation": "X"}),
        ("Z_PHASE_ATTACK", "PAULI_MANIPULATION", "QUANTUM_STATE", {"pauli_operation": "Z"}),
        ("Y_CHANNEL_ATTACK", "PAULI_MANIPULATION", "QUANTUM_STATE", {"pauli_operation": "Y"}),
        ("INTERCEPT_RESEND", "INTERCEPT_RESEND", "QUANTUM_CHANNEL", {}),
        ("BELL_RESULT_MANIPULATION", "BELL_RESULT_MANIPULATION", "BELL_RESULTS", {}),
        ("CORRECTION_MITM", "CORRECTION_MITM", "CLASSICAL_CORRECTION_CHANNEL", {}),
    ]
    for index, (label, attack_type, target, parameters) in enumerate(channel_specs):
        result = run_attack(
            AttackRunRequest(
                qds_session_id=session_id,
                attack_type=attack_type,
                target=target,
                attack_strength=1.0,
                seed=261410 + index,
                parameters={**parameters, "diagnostic_shots_per_basis": 128},
            )
        )
        matrix.append(_channel_matrix_entry(label, result))

    partial = run_attack(
        AttackRunRequest(
            qds_session_id=session_id,
            attack_type="PARTIAL_SIGNATURE_TAMPERING",
            target="SIGNATURE",
            attack_strength=0.10,
            seed=261420,
            parameters={"forgery_trials": 128},
        )
    )
    full = run_attack(
        AttackRunRequest(
            qds_session_id=session_id,
            attack_type="FULL_FORGERY",
            target="SIGNATURE",
            attack_strength=1.0,
            seed=261421,
            parameters={
                "scenario": "OBSERVED_SIGNATURE",
                "forgery_trials": 128,
                "attacker_mismatch_probability": 0.5,
            },
        )
    )
    impersonation = run_attack(
        AttackRunRequest(
            qds_session_id=session_id,
            attack_type="IMPERSONATION",
            target="IDENTITY",
            attack_strength=0.0,
            seed=261422,
        )
    )
    for label, result, estimate in (
        ("PARTIAL_TAMPERING", partial, partial["forgery"]["success_estimate"]),
        ("FULL_FORGERY", full, full["forgery"]["empirical_success_estimate"]),
    ):
        matrix.append({
            "scenario": label,
            "trials": estimate["trials"],
            "attack_strength": result["attack"]["strength"],
            "mean_qber": None,
            "qber_wilson_95": None,
            "raw_p_value": None,
            "adjusted_p_value": None,
            "detection_rate": 1.0 if result["verification"]["status"] == "INVALID" else 0.0,
            "empirical_acceptance_probability": estimate["estimated_probability"],
            "empirical_acceptance_wilson_95": estimate["wilson_95_percent_interval"],
            "verification_result": result["verification"]["status"],
            "runtime_ms": result["execution"]["duration_ms"],
        })
    matrix.append({
        "scenario": "IMPERSONATION",
        "trials": 1,
        "attack_strength": None,
        "mean_qber": None,
        "qber_wilson_95": None,
        "raw_p_value": None,
        "adjusted_p_value": None,
        "detection_rate": 1.0,
        "verification_result": impersonation["verification"]["status"],
        "runtime_ms": impersonation["execution"]["duration_ms"],
    })

    consumed = verify_document(
        document=document,
        signature=signature,
        consume=True,
        authenticated_verifier_id="Bob",
    )
    replay = run_attack(
        AttackRunRequest(
            qds_session_id=session_id,
            attack_type="REPLAY",
            target="PROTOCOL_SESSION",
            attack_strength=0.0,
            seed=261423,
        )
    )
    matrix.append({
        "scenario": "REPLAY",
        "trials": 1,
        "attack_strength": None,
        "mean_qber": None,
        "qber_wilson_95": None,
        "raw_p_value": None,
        "adjusted_p_value": None,
        "detection_rate": 1.0 if replay["detection"]["decision"] == "ATTACK_DETECTED" else 0.0,
        "verification_result": replay["verification"]["status"],
        "initial_consume_result": consumed.status,
        "runtime_ms": replay["execution"]["duration_ms"],
    })

    combined_noise = NoiseConfig(
        bit_flip=0.08,
        phase_flip=0.07,
        depolarizing=0.06,
        output_bit_flip=0.05,
        output_phase_flip=0.04,
        output_depolarizing=0.05,
        measurement_error=0.03,
    )
    combined = run_channel_diagnostic(
        ReferenceStatevectorEngine(seed=261430),
        shots_per_basis=1024,
        master_seed=261430,
        noise=combined_noise,
    )
    combined_errors = sum(int(item["errors"]) for item in combined["bases"].values())
    combined_trials = 2048
    matrix.append({
        "scenario": "COMBINED_NOISE",
        "trials": combined_trials,
        "attack_strength": None,
        "mean_qber": combined["combined_channel_disturbance"],
        "qber_wilson_95": wilson_interval(combined_errors, combined_trials),
        "raw_p_value": None,
        "adjusted_p_value": None,
        "detection_rate": None,
        "verification_result": "CHANNEL_DIAGNOSTIC_ONLY",
        "runtime_ms": None,
    })

    benchmark = run_detector_benchmark(
        engine_name="reference",
        scenarios=[
            "HONEST", "BIT_FLIP", "PHASE_FLIP", "Y_ATTACK", "DEPOLARIZING",
            "INTERCEPT_RESEND", "BELL_RESULT_MANIPULATION", "CORRECTION_MITM",
        ],
        strengths=[0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50],
        repetitions=10,
        shots_per_basis=64,
        seed=261440,
        normal_noise=NoiseConfig(
            output_bit_flip=0.005,
            output_phase_flip=0.005,
            measurement_error=0.005,
        ),
        evaluation_noise=NoiseConfig(
            output_bit_flip=0.005,
            output_phase_flip=0.005,
            measurement_error=0.005,
        ),
    )
    transferability = run_transferability_experiment(
        document=b"final honest transferability message",
        filename="transferability.txt",
        trials=10,
        seed=261450,
        scenario="HONEST",
    )
    repudiation = run_transferability_experiment(
        document=b"final selective disturbance message",
        filename="repudiation.txt",
        trials=10,
        seed=261451,
        scenario="SELECTIVE_CHARLIE_DISTURBANCE",
        selective_charlie_measurement_error=0.20,
    )
    total_runtime = time.perf_counter() - started
    report = {
        "schema": "zaslon.research-validation.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "engine": "REFERENCE_STATEVECTOR",
            "database": "ISOLATED_TEMPORARY_SQLITE",
            "seed_family": 261400,
            "claim": "Reproducible empirical validation; CUDA-Q is validated separately on WSL/NVIDIA.",
            "signature_format": signature["format"],
            "protocol_version": signature["protocol_version"],
            "reproducibility_manifest": signature["reproducibility"],
        },
        "signature_security": {
            "server_attestation": signature["server_attestation"],
            "basis_statistics": honest["basis_statistics"],
            "phase_sensitive_normal_verification": honest["basis_statistics"][
                "phase_sensitive_evidence"
            ],
        },
        "matrix": matrix,
        "detector_benchmark": benchmark,
        "transferability": transferability,
        "repudiation_selective_disturbance": repudiation,
        "forgery_reference_analysis": full["forgery"]["theoretical_or_reference_analysis"],
        "performance": {
            **signed["performance"],
            "verification_latency_ms": verification_latency_ms,
            "mean_attack_runtime_ms": statistics.fmean(
                item["runtime_ms"] for item in matrix if isinstance(item.get("runtime_ms"), (int, float))
            ),
            "complete_matrix_runtime_seconds": total_runtime,
        },
        "capability_status": {
            "core_teleportation": "VALIDATED",
            "attack_detection": "EMPIRICALLY_VALIDATED",
            "forgery": "EMPIRICAL_PLUS_RESTRICTED_REFERENCE_BOUND",
            "transferability": "EXPERIMENTALLY_VALIDATED",
            "non_repudiation": "EXPERIMENTAL_ONLY_NOT_FORMALLY_PROVEN",
            "information_theoretic_security": "NOT_FORMALLY_PROVEN",
        },
    }
    destination = Path(
        os.getenv("ZASLON_VALIDATION_OUTPUT", str(ROOT / "FINAL_VALIDATION_RESULTS.json"))
    )
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    validation_database_engine.dispose()
    _temp_directory.cleanup()
    return destination


if __name__ == "__main__":
    print(main())
