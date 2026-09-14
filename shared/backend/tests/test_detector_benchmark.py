from zaslon_shared.benchmark import run_detector_benchmark


def test_detector_benchmark_reports_aggregate_security_metrics() -> None:
    result = run_detector_benchmark(
        engine_name="reference",
        scenarios=["HONEST", "PHASE_FLIP"],
        strengths=[0.0, 1.0],
        repetitions=2,
        shots_per_basis=32,
        seed=261100,
    )
    assert result["family_correction"] == "HOLM_FWER_ACROSS_Z_AND_X_PER_RUN"
    assert result["false_positive_rate"] == 0.0
    assert result["honest_abort_rate"] == 0.0
    phase_full = next(
        row for row in result["aggregates"]
        if row["scenario"] == "PHASE_FLIP" and row["strength"] == 1.0
    )
    assert phase_full["mean_qber"] == 0.5
    assert phase_full["detection_probability"] == 1.0
    assert phase_full["mean_fidelity"] == 0.5
    assert len(phase_full["detection_probability_wilson_95"]) == 2
    assert result["threshold_calibration"]["status"] == "CALIBRATED_EMPIRICALLY"
    assert result["dataset_split"] == (
        "INDEPENDENT_DOMAIN_SEPARATED_CALIBRATION_AND_HELD_OUT_EVALUATION"
    )
    assert result["held_out_threshold_evaluation"]["evaluation_record_count"] > 0
    held_out = result["held_out_threshold_evaluation"]
    assert held_out["negative_control_policy"] == "HONEST_OR_ZERO_ATTACK_STRENGTH"
    assert held_out["evaluation_negative_control_count"] == 6
    assert held_out["evaluation_positive_attack_count"] == 2
    assert {
        row["dataset"] for row in result["records"]
    } == {"CALIBRATION", "HELD_OUT_EVALUATION"}
    assert "NOT A FORMAL" in result["claim"]
