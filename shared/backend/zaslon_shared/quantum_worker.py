from __future__ import annotations

import base64
import logging
import subprocess
import threading
import time
from typing import Any

from .attacks import run_attack
from .benchmark import run_detector_benchmark
from .config import settings
from .job_queue import (
    claim_next_job,
    complete_job,
    fail_job,
    heartbeat_job,
    recover_stale_jobs,
    update_worker_status,
    validate_job_queue_configuration,
)
from .migrations import verify_schema
from .multiverifier import run_transferability_experiment
from .network import configured_network, simulate_sequence_network
from .participant import sign_document
from .quantum import create_quantum_engine, cross_validate_quantum_engines
from .schemas import AttackRunRequest


logger = logging.getLogger("zaslon.quantum-worker")


def _gpu_name() -> str | None:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return completed.stdout.splitlines()[0].strip() or None
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def initialize_worker_health() -> dict[str, Any]:
    try:
        import cudaq

        engine = create_quantum_engine("cudaq", seed=26141)
        diagnostic = engine.diagnose_bell_pair(shots=128)
        recovery = engine.teleport_and_measure(
            bit=1, preparation_basis="Z", measurement_basis="Z"
        )
        if not diagnostic["verified"] or recovery.bob_outcome != 1:
            raise RuntimeError("Known-state CUDA-Q health experiment failed")
        correction_outcomes: set[tuple[int, int]] = set()
        for _ in range(64):
            corrected = engine.teleport_and_measure(
                bit=1, preparation_basis="X", measurement_basis="X"
            )
            if corrected.bob_outcome != 1:
                raise RuntimeError("CUDA-Q Pauli correction health experiment failed")
            correction_outcomes.add(corrected.bell_bits)
        if correction_outcomes != {(0, 0), (0, 1), (1, 0), (1, 1)}:
            raise RuntimeError("CUDA-Q did not exercise all Bell correction cases")
        phase_check = engine.teleport_and_measure(
            bit=0,
            preparation_basis="X",
            measurement_basis="X",
            output_pauli="Z",
        )
        if phase_check.bob_outcome != 1:
            raise RuntimeError("CUDA-Q phase-sensitive health experiment failed")
        if settings.cudaq_target == "nvidia" and not engine.metadata.gpu:
            if not engine.metadata.fallback_used:
                raise RuntimeError("CUDA-Q did not execute on the requested NVIDIA target")
        network_health = None
        if settings.sequence_enabled:
            pending_network_recovery = engine.begin_networked_teleportation(
                bit=0, preparation_basis="X", measurement_basis="X"
            )
            network_health = simulate_sequence_network(
                requested_bell_pairs=1,
                config=configured_network(seed=26141),
                correction_messages=[pending_network_recovery.bell_bits],
                include_private_delivery_receipts=True,
            )
            if not network_health["gate_to_cudaq"]["allowed"]:
                raise RuntimeError("SeQUeNCe network health experiment did not deliver its controls")
            delivered = network_health.pop("_private_delivered_correction_messages")
            network_recovery = engine.complete_networked_teleportation(
                pending_network_recovery,
                delivered_bell_bits=tuple(delivered[0]),
            )
            if network_recovery.bob_outcome != 0:
                raise RuntimeError("SeQUeNCe-delivered CUDA-Q recovery health experiment failed")
            network_health["integration"]["control_effect"] = (
                "SEQUENCE_DELIVERED_BITS_CAUSALLY_DRIVE_RECEIVER_RECOVERY_STAGE"
            )
            network_health["integration"]["execution_order"] = [
                "CUDA_Q_BELL_MEASUREMENT",
                "SEQUENCE_CLASSICAL_DELIVERY",
                "CUDA_Q_RECEIVER_CORRECTION_AND_MEASUREMENT",
            ]
        status = {
            "worker_id": settings.worker_id,
            "worker": "HEALTHY",
            "cudaq": "HEALTHY",
            "gpu": "AVAILABLE" if engine.metadata.gpu else "UNAVAILABLE",
            "engine": engine.metadata.engine,
            "requested_target": settings.cudaq_target,
            "execution_target": engine.metadata.target,
            "cudaq_version": str(getattr(cudaq, "__version__", "UNKNOWN")),
            "gpu_name": _gpu_name(),
            "fallback_used": engine.metadata.fallback_used,
            "fallback_reason": engine.metadata.fallback_reason,
            "known_state_kernel": "PASSED",
            "three_qubit_teleportation": "PASSED",
            "all_pauli_correction_cases": "PASSED",
            "phase_sensitive_x_basis": "PASSED",
            "bell_diagnostic": "PASSED",
            "cudaq_sequence_control_transport": "PASSED"
            if network_health is not None
            else "DISABLED",
            "staged_network_receiver_recovery": "PASSED"
            if network_health is not None
            else "DISABLED",
            "sequence": "HEALTHY" if network_health is not None else "DISABLED",
            "sequence_result": network_health,
        }
    except Exception as exc:
        status = {
            "worker_id": settings.worker_id,
            "worker": "HEALTHY",
            "cudaq": "UNAVAILABLE",
            "gpu": "UNAVAILABLE",
            "engine": "CUDA-Q",
            "requested_target": settings.cudaq_target,
            "execution_target": None,
            "cudaq_version": None,
            "gpu_name": _gpu_name(),
            "fallback_used": False,
            "fallback_reason": None,
            "error_code": "QUANTUM_BACKEND_UNAVAILABLE",
            "error_message": " ".join(str(exc).split())[:512],
        }
    update_worker_status(status)
    return status


def _document(payload: dict[str, Any]) -> bytes:
    try:
        return base64.b64decode(payload.pop("document_b64"), validate=True)
    except Exception as exc:
        raise ValueError("Quantum signing job contains invalid document bytes") from exc


def execute_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if job_type in {"SIGN_ALICE", "SIGN_BOB"}:
        document = _document(payload)
        requested_pairs = 512 * 2 * settings.states_per_candidate
        network = None
        if settings.sequence_enabled:
            correction_sender = str(payload.get("signer_id", "Alice"))
            correction_receiver = str(payload.get("verifier_id", "Bob"))
            network = simulate_sequence_network(
                requested_bell_pairs=requested_pairs,
                config=configured_network(
                    seed=int(payload.get("seed") or 0),
                    include_charlie=correction_receiver == "Charlie",
                ),
                correction_sender=correction_sender,
                correction_receiver=correction_receiver,
            )
            if not network["gate_to_cudaq"]["allowed"]:
                raise RuntimeError("ENTANGLEMENT_DISTRIBUTION_FAILED")
        return sign_document(document=document, network_context=network, **payload)
    if job_type == "ATTACK_RUN":
        return run_attack(AttackRunRequest.model_validate(payload))
    if job_type == "DETECTOR_BENCHMARK":
        return run_detector_benchmark(engine_name=settings.quantum_engine, **payload)
    if job_type == "MULTIVERIFIER_BENCHMARK":
        return run_transferability_experiment(
            document=b"ZASLON-QDS multi-verifier benchmark message",
            filename="multiverifier-benchmark.txt",
            **payload,
        )
    if job_type == "QISKIT_VALIDATION":
        return cross_validate_quantum_engines(**payload)
    if job_type == "NETWORK_EXPERIMENT":
        config = configured_network(
            seed=int(payload.get("seed", 2026)),
            include_charlie=bool(payload.get("include_charlie", False)),
        )
        return simulate_sequence_network(
            requested_bell_pairs=int(payload.get("requested_bell_pairs", 32)),
            config=config,
            correction_flip_mask=int(payload.get("correction_flip_mask", 0)),
        )
    raise ValueError(f"Unsupported quantum job type: {job_type}")


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    validate_job_queue_configuration()
    if settings.execution_mode != "worker_queue":
        raise RuntimeError("The quantum worker requires ZASLON_EXECUTION_MODE=worker_queue")
    if not verify_schema():
        raise RuntimeError("Database migrations are incomplete")
    recover_stale_jobs()
    status = initialize_worker_health()
    if status["cudaq"] != "HEALTHY":
        raise RuntimeError(status.get("error_code", "QUANTUM_BACKEND_UNAVAILABLE"))
    last_health = time.monotonic()
    while True:
        job = claim_next_job(worker_id=settings.worker_id)
        if job is None:
            if time.monotonic() - last_health >= settings.worker_heartbeat_seconds:
                update_worker_status(status)
                last_health = time.monotonic()
            time.sleep(min(settings.job_poll_interval_seconds, 1.0))
            continue
        job_id = job["job_id"]
        heartbeat_stop = threading.Event()

        def maintain_heartbeat() -> None:
            while not heartbeat_stop.wait(settings.worker_heartbeat_seconds):
                heartbeat_job(job_id, worker_id=settings.worker_id)
                update_worker_status(status)

        heartbeat_thread = threading.Thread(
            target=maintain_heartbeat,
            name=f"heartbeat-{job_id}",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            heartbeat_job(job_id, worker_id=settings.worker_id)
            result = execute_job(job["job_type"], dict(job["payload"]))
            complete_job(job_id, worker_id=settings.worker_id, result=result)
        except Exception as exc:
            logger.exception("Quantum job %s failed", job_id)
            fail_job(
                job_id,
                worker_id=settings.worker_id,
                code="QUANTUM_JOB_EXECUTION_FAILED",
                message=str(exc),
            )
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=max(settings.worker_heartbeat_seconds, 1.0))
        update_worker_status(status)
        last_health = time.monotonic()


if __name__ == "__main__":
    run_worker()
