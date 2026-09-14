from __future__ import annotations

from cryptography.fernet import Fernet
import pytest
import threading
import time

from zaslon_shared.config import settings
from zaslon_shared.db import QuantumJob, session_scope
from zaslon_shared.job_queue import (
    claim_next_job,
    complete_job,
    job_status,
    submit_job,
    update_worker_status,
    worker_readiness,
)
from zaslon_shared.migrations import run_migrations, verify_schema
from zaslon_shared.dispatch import sign as dispatch_sign
from zaslon_shared.quantum_worker import execute_job


@pytest.fixture
def queue_key():
    previous = settings.job_payload_key
    object.__setattr__(settings, "job_payload_key", Fernet.generate_key().decode("ascii"))
    try:
        yield
    finally:
        object.__setattr__(settings, "job_payload_key", previous)


def test_versioned_migrations_are_idempotent():
    first = run_migrations()
    second = run_migrations()
    assert verify_schema() is True
    assert [row["status"] for row in first] == [
        "APPLIED",
        "APPLIED",
        "APPLIED",
        "APPLIED",
    ]
    assert [row["status"] for row in second] == [
        "ALREADY_APPLIED",
        "ALREADY_APPLIED",
        "ALREADY_APPLIED",
        "ALREADY_APPLIED",
    ]


def test_queue_encrypts_payload_claims_atomically_and_clears_input(queue_key):
    plaintext_marker = "private-document-content"
    job_id = submit_job(
        role="ALICE",
        job_type="TEST",
        payload={"document": plaintext_marker, "seed": 7},
    )
    with session_scope() as db:
        row = db.get(QuantumJob, job_id)
        assert row is not None
        assert plaintext_marker not in (row.payload_ciphertext or "")
        assert row.status == "QUEUED"

    claimed = claim_next_job(worker_id="test-worker")
    assert claimed is not None
    assert claimed["job_id"] == job_id
    assert claimed["payload"]["document"] == plaintext_marker
    assert claim_next_job(worker_id="second-worker") is None

    complete_job(job_id, worker_id="test-worker", result={"ok": True})
    status = job_status(job_id, role="ALICE")
    assert status["status"] == "SUCCEEDED"
    assert status["result"] == {"ok": True}
    assert status["encrypted_payload_retained"] is False
    with pytest.raises(LookupError):
        job_status(job_id, role="BOB")


def test_worker_health_distinguishes_process_cudaq_and_gpu():
    update_worker_status(
        {
            "worker_id": "test-worker",
            "worker": "HEALTHY",
            "cudaq": "HEALTHY",
            "gpu": "AVAILABLE",
            "engine": "CUDA-Q",
            "requested_target": "nvidia",
            "execution_target": "nvidia",
            "cudaq_version": "0.15.1",
            "gpu_name": "test-gpu",
            "fallback_used": False,
            "fallback_reason": None,
        }
    )
    status = worker_readiness()
    assert status["available"] is True
    assert status["worker"] == "HEALTHY"
    assert status["cudaq"] == "HEALTHY"
    assert status["gpu"] == "AVAILABLE"


def test_api_dispatch_and_worker_execute_the_existing_signer_without_duplication(queue_key):
    previous_mode = settings.execution_mode
    previous_sequence = settings.sequence_enabled
    previous_timeout = settings.job_wait_timeout_seconds
    object.__setattr__(settings, "execution_mode", "worker_queue")
    object.__setattr__(settings, "sequence_enabled", False)
    object.__setattr__(settings, "job_wait_timeout_seconds", 15.0)

    def work_once() -> None:
        deadline = time.monotonic() + 5
        claimed = None
        while claimed is None and time.monotonic() < deadline:
            claimed = claim_next_job(worker_id="integration-worker")
            if claimed is None:
                time.sleep(0.01)
        assert claimed is not None
        result = execute_job(claimed["job_type"], dict(claimed["payload"]))
        complete_job(claimed["job_id"], worker_id="integration-worker", result=result)

    worker = threading.Thread(target=work_once)
    worker.start()
    try:
        result = dispatch_sign(
            role="ALICE",
            document=b"queued quantum signature",
            parameters={
                "filename": "queued.txt",
                "signer_id": "Alice",
                "verifier_id": "Bob",
                "seed": 26141,
                "encryption_passphrase": None,
                "noise": {},
            },
        )
        worker.join(timeout=15)
        assert not worker.is_alive()
        assert result["session"]["signer_id"] == "Alice"
        assert result["quantum"]["engine"] == "REFERENCE_STATEVECTOR"
        assert result["worker_job"]["status"] == "SUCCEEDED"
    finally:
        object.__setattr__(settings, "execution_mode", previous_mode)
        object.__setattr__(settings, "sequence_enabled", previous_sequence)
        object.__setattr__(settings, "job_wait_timeout_seconds", previous_timeout)
