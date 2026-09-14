import os

from fastapi.testclient import TestClient

from app.main import app


ATTACK_HEADERS = {"X-ZASLON-API-Key": os.environ["ZASLON_ATTACK_API_KEY"]}


def test_channel_benchmark_endpoint_returns_real_calibration_metrics() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/attacks/benchmarks/channel",
            headers=ATTACK_HEADERS,
            json={
                "scenarios": ["HONEST", "PHASE_FLIP"],
                "strengths": [0.0, 1.0],
                "repetitions": 1,
                "shots_per_basis": 32,
                "seed": 261300,
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_calibration"]["status"] == "CALIBRATED_EMPIRICALLY"
    assert payload["held_out_threshold_evaluation"]["dataset"] == (
        "INDEPENDENT_SEEDED_HELD_OUT_EVALUATION"
    )
    assert payload["family_correction"] == "HOLM_FWER_ACROSS_Z_AND_X_PER_RUN"
    assert payload["honest_abort_rate"] == 0.0


def test_multiverifier_endpoint_reports_transferability_and_repudiation_metrics() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/attacks/benchmarks/multiverifier",
            headers=ATTACK_HEADERS,
            json={"scenario": "HONEST", "trials": 1, "seed": 261301},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["p_transfer_failure_empirical"] == 0.0
    assert payload["metrics"]["p_repudiation_empirical"] == 0.0
    assert payload["thresholds"]["relation"] == "s_a < s_v"
