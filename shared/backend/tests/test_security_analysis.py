import pytest

from zaslon_shared.security_analysis import (
    calibrate_threshold,
    classifier_metrics,
    holm_adjust,
    restricted_binomial_forgery_analysis,
)


def test_holm_adjustment_controls_family_and_preserves_original_order() -> None:
    results = holm_adjust([0.004, 0.030, 0.001], alpha=0.01)
    assert [item["adjusted_p_value"] for item in results] == [0.008, 0.03, 0.003]
    assert [item["decision"] for item in results] == [
        "REJECT_NULL", "DO_NOT_REJECT_NULL", "REJECT_NULL"
    ]
    assert all(item["family_size"] == 3 for item in results)
    assert all("not an attack probability" in item["interpretation"] for item in results)


def test_classifier_metrics_use_security_correct_denominators() -> None:
    metrics = classifier_metrics(tp=80, tn=90, fp=10, fn=20)
    assert metrics["tpr_sensitivity"] == 0.8
    assert metrics["tnr_specificity"] == 0.9
    assert metrics["fpr"] == 0.1
    assert metrics["fnr"] == 0.2
    assert metrics["honest_acceptance_rate"] == 0.9
    assert metrics["honest_abort_rate"] == 0.1
    assert metrics["balanced_accuracy"] == pytest.approx(0.85)


def test_threshold_calibration_obeys_false_positive_constraint() -> None:
    result = calibrate_threshold(
        honest_mismatch_rates=[0.00, 0.01, 0.02, 0.03, 0.04],
        attack_mismatch_rates=[0.02, 0.08, 0.12, 0.20, 0.30],
        candidate_thresholds=[0.01, 0.03, 0.04, 0.07, 0.10],
        maximum_false_positive_rate=0.0,
    )
    assert result["selected_metrics"]["fpr"] == 0.0
    assert result["selected_threshold"] == 0.04
    assert result["status"] == "CALIBRATED_EMPIRICALLY"


def test_unjustified_binomial_value_is_labeled_reference_not_security_proof() -> None:
    result = restricted_binomial_forgery_analysis(
        signature_length=512,
        attacker_mismatch_probability=0.5,
        acceptance_threshold=0.05,
        independence_justified=False,
        mismatch_probability_justified=False,
    )
    assert result["label"] == "REFERENCE BOUND"
    assert result["formally_applies_to_zaslon"] is False
    assert result["warning"] is not None
    assert 0.0 <= result["binomial_lower_tail_probability"] <= 1.0
