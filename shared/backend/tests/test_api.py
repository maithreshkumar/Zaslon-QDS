import json
import os

from fastapi.testclient import TestClient

from app.main import app


ALICE_HEADERS = {"X-ZASLON-API-Key": os.environ["ZASLON_ALICE_API_KEY"]}
BOB_HEADERS = {"X-ZASLON-API-Key": os.environ["ZASLON_BOB_API_KEY"]}
ATTACK_HEADERS = {"X-ZASLON-API-Key": os.environ["ZASLON_ATTACK_API_KEY"]}


def test_health_session_retrieval_and_signature_limits():
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["quantum"]["engine"] == "REFERENCE_STATEVECTOR"

        signed = client.post(
            "/api/v1/bob/sign",
            headers=BOB_HEADERS,
            files={"document": ("bob.txt", b"signed by bob", "text/plain")},
            data={"signer_id": "Bob", "verifier_id": "Alice", "seed": "22"},
        )
        assert signed.status_code == 200
        signed_payload = signed.json()
        session_id = signed_payload["session"]["id"]
        assert signed_payload["artifact"]["filename"] == "bob.txt.qds.json"
        artifact = client.get(
            signed_payload["artifact"]["download_url"], headers=BOB_HEADERS
        )
        assert artifact.status_code == 200
        assert artifact.headers["content-type"].startswith("application/json")
        assert artifact.headers["content-disposition"] == (
            'attachment; filename="bob.txt.qds.json"'
        )
        downloaded_signature = artifact.json()
        assert downloaded_signature == signed_payload["signature"]
        assert {
            "version", "algorithm", "protocol", "signature_id", "session_id",
            "signer_id", "verifier_id", "hash_algorithm", "document_hash",
            "created_at", "nonce", "quantum_parameters", "teleportation_metadata",
            "signature_declarations", "verification_thresholds",
        } <= downloaded_signature.keys()
        assert "candidates" not in downloaded_signature
        assert "experiment_seed" not in downloaded_signature
        assert downloaded_signature["bell_state_analysis"]["all_same"] is True
        assert downloaded_signature["bell_state_analysis"]["expected_state"] == "PHI_PLUS"
        assert downloaded_signature["bell_state_analysis"]["observed_state"] == "PHI_PLUS"
        retrieved = client.get(f"/api/v1/sessions/{session_id}", headers=ALICE_HEADERS)
        assert retrieved.status_code == 200
        assert retrieved.json()["signer_id"] == "Bob"
        quantum_status = client.get(
            f"/api/v1/sessions/{session_id}/quantum-status", headers=BOB_HEADERS
        )
        assert quantum_status.status_code == 200
        assert quantum_status.json()["entanglement"]["verified"] is True
        assert quantum_status.json()["bell_pair"]["status"] == (
            "ENTANGLEMENT_CONSUMED_BY_TELEPORTATION"
        )


def test_qiskit_validation_endpoint_runs_real_aer_circuits():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/validate/qiskit",
            json={"shots": 32, "seed": 7},
            headers=ALICE_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["validator"]["engine"] == "QISKIT_AER"
        assert response.json()["comparison"]["primary"]["engine"] == "REFERENCE_STATEVECTOR"


def test_frontend_alice_bob_and_attack_endpoints_end_to_end():
    with TestClient(app) as client:
        signed = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={"document": ("x.pdf", b"PDF-like test bytes", "application/pdf")},
            data={"signer_id": "Alice", "verifier_id": "Bob", "seed": "77",
                  "encryption_passphrase": "test-password"},
        )
        assert signed.status_code == 200
        payload = signed.json()
        signature_bytes = json.dumps(payload["signature"]).encode()

        altered = client.post("/api/v1/bob/verify", headers=BOB_HEADERS, files={
            "document": ("x.pdf", b"altered", "application/pdf"),
            "signature": ("x.qds.json", signature_bytes, "application/json"),
        })
        assert altered.json()["status"] == "INVALID"

        verified = client.post("/api/v1/bob/verify", headers=BOB_HEADERS, files={
            "document": ("x.pdf", b"PDF-like test bytes", "application/pdf"),
            "signature": ("x.qds.json", signature_bytes, "application/json"),
        })
        assert verified.json()["status"] == "VALID"

        baseline = client.post("/api/v1/attacks/runs", headers=ATTACK_HEADERS, json={
            "qds_session_id": payload["session"]["id"], "attack_type": "BASELINE",
            "target": "PROTOCOL", "attack_strength": 0, "seed": 77,
        })
        assert baseline.status_code == 200
        assert baseline.json()["verification"]["status"] == "VALID"

        decrypted = client.post("/api/v1/bob/decrypt", headers=BOB_HEADERS, json={
            "encrypted_package": payload["encryption"], "passphrase": "test-password"
        })
        assert decrypted.status_code == 200
        assert decrypted.content == b"PDF-like test bytes"


def test_signing_rejects_a_qds_artifact_as_the_source_document():
    with TestClient(app) as client:
        signed = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={"document": ("source.txt", b"source bytes", "text/plain")},
            data={"signer_id": "Alice", "verifier_id": "Bob", "seed": "78"},
        )
        assert signed.status_code == 200
        artifact_bytes = json.dumps(signed.json()["signature"], indent=2).encode("utf-8")

        nested = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={
                "document": (
                    "source.txt.qds.json",
                    artifact_bytes,
                    "application/json",
                )
            },
            data={"signer_id": "Alice", "verifier_id": "Bob", "seed": "79"},
        )
        assert nested.status_code == 400
        assert "original document" in nested.json()["detail"]


def test_role_credentials_block_cross_role_and_unauthenticated_requests():
    with TestClient(app) as client:
        missing = client.get("/api/v1/sessions")
        assert missing.status_code == 401

        invalid = client.get(
            "/api/v1/sessions", headers={"X-ZASLON-API-Key": "not-a-valid-key"}
        )
        assert invalid.status_code == 401

        bob_calling_attack = client.get("/api/v1/attacks/runs", headers=BOB_HEADERS)
        assert bob_calling_attack.status_code == 403

        alice_calling_attack = client.get("/api/v1/attacks/runs", headers=ALICE_HEADERS)
        assert alice_calling_attack.status_code == 403

        attack_calling_bob = client.post("/api/v1/bob/decrypt", headers=ATTACK_HEADERS, json={})
        assert attack_calling_bob.status_code == 403

        alice_calling_bob = client.post("/api/v1/bob/decrypt", headers=ALICE_HEADERS, json={})
        assert alice_calling_bob.status_code == 403

        attack_calling_alice = client.post(
            "/api/v1/alice/sessions", headers=ATTACK_HEADERS
        )
        assert attack_calling_alice.status_code == 403

        bob_calling_alice = client.post("/api/v1/alice/sessions", headers=BOB_HEADERS)
        assert bob_calling_alice.status_code == 403

        bob_reading_attack_result = client.get(
            "/api/v1/results/not-a-real-experiment", headers=BOB_HEADERS
        )
        assert bob_reading_attack_result.status_code == 403

        attack_sessions = client.get("/api/v1/sessions", headers=ATTACK_HEADERS)
        assert attack_sessions.status_code == 200

        bob_session_listing = client.get("/api/v1/sessions", headers=BOB_HEADERS)
        assert bob_session_listing.status_code == 403


def test_authenticated_role_controls_signer_and_intended_verifier_identity():
    with TestClient(app) as client:
        spoofed_signer = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={"document": ("identity.txt", b"identity", "text/plain")},
            data={"signer_id": "Bob", "verifier_id": "Bob", "seed": "91"},
        )
        assert spoofed_signer.status_code == 403

        unknown_verifier = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={"document": ("identity.txt", b"identity", "text/plain")},
            data={"signer_id": "Alice", "verifier_id": "Mallory", "seed": "91"},
        )
        assert unknown_verifier.status_code == 400

        signed = client.post(
            "/api/v1/alice/sessions",
            headers=ALICE_HEADERS,
            files={"document": ("identity.txt", b"identity", "text/plain")},
            data={"signer_id": "Alice", "verifier_id": "Bob", "seed": "91"},
        )
        assert signed.status_code == 200
        signature = json.dumps(signed.json()["signature"]).encode()

        alice_attempt = client.post(
            "/api/v1/alice/verify",
            headers=ALICE_HEADERS,
            files={
                "document": ("identity.txt", b"identity", "text/plain"),
                "signature": ("identity.qds.json", signature, "application/json"),
            },
        )
        assert alice_attempt.status_code == 200
        assert alice_attempt.json()["status"] == "INVALID"
        assert alice_attempt.json()["failure_code"] == "UNAUTHORIZED_VERIFIER"

        bob_attempt = client.post(
            "/api/v1/bob/verify",
            headers=BOB_HEADERS,
            files={
                "document": ("identity.txt", b"identity", "text/plain"),
                "signature": ("identity.qds.json", signature, "application/json"),
            },
        )
        assert bob_attempt.status_code == 200
        assert bob_attempt.json()["status"] == "VALID"
