"""
End-to-End API Compatibility Test Suite for Frontend Integration.
Validates all endpoints consumed by the React application.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from quantum.service.circuits.state_prep import derive_teleportation_parameters
from unittest.mock import patch

def fake_quantum_execution(sha512_digest: str, start_index: int, batch_size: int, total_count: int = 4096):
    params = derive_teleportation_parameters(sha512_digest, total_count=total_count)
    batch = params[start_index:start_index + batch_size]
    measurements = []
    for p in batch:
        measurements.append({
            "operation_index": p["operation_index"],
            "prep_theta": p["prep_theta"],
            "prep_phi": p["prep_phi"],
            "basis": p["basis"],
            "expected_bit": p["expected_bit"],
            "alice_m0": 0,
            "alice_m1": 0,
            "bob_correction_x": 0,
            "bob_correction_z": 0,
            "bob_observed_bit": p["expected_bit"],
            "is_match": True
        })
    return {"measurements": measurements, "batch_size": len(measurements)}

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_complete_frontend_api_compatibility(client):
    # 1. Health check
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

    # 2. Create session
    res = client.post(
        "/api/v1/sessions",
        json={"session_name": "Frontend-E2E-Sig", "created_by": "Alice_Signer", "verifier_id": "Bob_Verifier"}
    )
    assert res.status_code == 201
    sess_body = res.json()
    assert sess_body["success"] is True
    session_id = sess_body["data"]["id"]

    # 3. List sessions
    res = client.get("/api/v1/sessions?limit=10&offset=0")
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1

    # 4. Get specific session
    res = client.get(f"/api/v1/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["data"]["session_name"] == "Frontend-E2E-Sig"

    # 5. Compute SHA-512 Hash
    res = client.post(
        f"/api/v1/sessions/{session_id}/hash",
        json={"raw_message": "SIH 26141 Secret Document Payload", "actor": "Alice_Signer"}
    )
    assert res.status_code == 201
    hash_body = res.json()
    assert hash_body["success"] is True
    assert len(hash_body["data"]["sha512_digest"]) == 128

    # 6. Check workflow overview
    res = client.get(f"/api/v1/sessions/{session_id}/workflow")
    assert res.status_code == 200
    wf_body = res.json()
    assert wf_body["data"]["stages"]["hash_stage"]["completed"] is True

    # 7. Launch Teleportation
    with patch("backend.app.services.quantum_service.QuantumService.execute_teleportation_batch", side_effect=fake_quantum_execution):
        res = client.post(
            f"/api/v1/sessions/{session_id}/teleport?background=false",
            json={"actor": "Alice_Signer", "teleportation_count": 64, "batch_size": 32}
        )
        assert res.status_code == 202
        assert res.json()["success"] is True

    # 8. Check Quantum Status
    res = client.get(f"/api/v1/sessions/{session_id}/quantum-status")
    assert res.status_code == 200
    q_status = res.json()["data"]
    assert q_status["status"] == "COMPLETED"
    assert q_status["completed_operations"] == 64
    assert q_status["progress_percentage"] == 100.0

    # 9. Get Measurements
    res = client.get(f"/api/v1/sessions/{session_id}/measurements?page=1&page_size=25")
    assert res.status_code == 200
    meas_data = res.json()["data"]
    assert meas_data["total"] == 64
    assert len(meas_data["items"]) == 25
    assert meas_data["items"][0]["is_match"] is True

    # 10. Issue Public Declaration
    res = client.post(
        f"/api/v1/sessions/{session_id}/declare",
        json={"signer_id": "Alice_Signer"}
    )
    assert res.status_code == 201
    decl_data = res.json()["data"]
    assert decl_data["is_consumed"] is False
    assert decl_data["signature_token"].startswith("sig_qds_")

    # 11. Get Public Declaration
    res = client.get(f"/api/v1/sessions/{session_id}/declaration")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "ACTIVE"

    # 12. Verify Session
    res = client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"verifier_id": "Bob_Verifier", "sample_ratio": 0.10}
    )
    assert res.status_code == 200
    verif_data = res.json()["data"]
    assert verif_data["security_decision"] == "VERIFIED"
    assert verif_data["statistical_verdict"] == "ACCEPTABLE"
    assert verif_data["attack_detected"] is False

    # 13. Get Verification Results
    res = client.get(f"/api/v1/sessions/{session_id}/verification-results")
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1

    # 14. Get Verification Samples (Protected: Bob only)
    # Anonymous or unauthorized caller blocked with 403 UNAUTHORIZED_PROBE
    res_anon = client.get(f"/api/v1/sessions/{session_id}/samples")
    assert res_anon.status_code == 403

    # Authorized Bob verifier succeeds
    res = client.get(f"/api/v1/sessions/{session_id}/samples", headers={"X-Participant-ID": "Bob_Verifier"})
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1

    # 15. Simulate Attack: FORGERY
    res = client.post(
        f"/api/v1/sessions/{session_id}/simulate-attack",
        json={"attack_type": "FORGERY"}
    )
    assert res.status_code == 201
    att_event = res.json()["data"]
    assert att_event["attack_type"] == "FORGERY"
    assert att_event["detected"] is True

    # 16. Get Attack Events
    res = client.get(f"/api/v1/sessions/{session_id}/attack-events")
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1

    # 17. Get Audit Trail
    res = client.get(f"/api/v1/audit-trail?session_id={session_id}")
    assert res.status_code == 200
    audits = res.json()["data"]
    assert len(audits) >= 5
