from __future__ import annotations

import base64
from typing import Any

from .attacks import run_attack
from .benchmark import run_detector_benchmark
from .config import settings
from .job_queue import submit_and_wait
from .multiverifier import run_transferability_experiment
from .participant import sign_document
from .quantum import cross_validate_quantum_engines
from .runtime import quantum_job_slot
from .schemas import AttackRunRequest


def sign(*, role: str, document: bytes, parameters: dict[str, Any]) -> dict[str, Any]:
    if settings.execution_mode == "worker_queue":
        payload = {
            **parameters,
            "document_b64": base64.b64encode(document).decode("ascii"),
        }
        return submit_and_wait(role=role, job_type=f"SIGN_{role}", payload=payload)
    with quantum_job_slot("signature"):
        return sign_document(document=document, **parameters)


def attack(request: AttackRunRequest) -> dict[str, Any]:
    if settings.execution_mode == "worker_queue":
        return submit_and_wait(
            role="ATTACK",
            job_type="ATTACK_RUN",
            payload=request.model_dump(mode="json"),
        )
    with quantum_job_slot("attack"):
        return run_attack(request)


def detector_benchmark(parameters: dict[str, Any]) -> dict[str, Any]:
    if settings.execution_mode == "worker_queue":
        return submit_and_wait(
            role="ATTACK", job_type="DETECTOR_BENCHMARK", payload=parameters
        )
    with quantum_job_slot("detector benchmark"):
        return run_detector_benchmark(engine_name=settings.quantum_engine, **parameters)


def multiverifier_benchmark(parameters: dict[str, Any]) -> dict[str, Any]:
    if settings.execution_mode == "worker_queue":
        return submit_and_wait(
            role="ATTACK", job_type="MULTIVERIFIER_BENCHMARK", payload=parameters
        )
    with quantum_job_slot("multi-verifier benchmark"):
        return run_transferability_experiment(
            document=b"ZASLON-QDS multi-verifier benchmark message",
            filename="multiverifier-benchmark.txt",
            **parameters,
        )


def qiskit_validation(parameters: dict[str, Any]) -> dict[str, Any]:
    if settings.execution_mode == "worker_queue":
        return submit_and_wait(
            role="ALICE", job_type="QISKIT_VALIDATION", payload=parameters
        )
    with quantum_job_slot("validation"):
        return cross_validate_quantum_engines(**parameters)


def network_experiment(parameters: dict[str, Any]) -> dict[str, Any]:
    if settings.execution_mode != "worker_queue":
        from .network import configured_network, simulate_sequence_network

        return simulate_sequence_network(
            requested_bell_pairs=int(parameters.get("requested_bell_pairs", 32)),
            config=configured_network(
                seed=int(parameters.get("seed", 2026)),
                include_charlie=bool(parameters.get("include_charlie", False)),
            ),
            correction_flip_mask=int(parameters.get("correction_flip_mask", 0)),
        )
    return submit_and_wait(
        role="ATTACK", job_type="NETWORK_EXPERIMENT", payload=parameters
    )

