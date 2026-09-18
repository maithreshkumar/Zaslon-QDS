"""
Unit tests for Fisher's Exact Test and statistical hypothesis testing in Zaslon-QDS.
"""
import pytest
import math

from backend.app.services.statistics_service import StatisticsService


def test_calculate_mismatch_metrics():
    tot, ratio = StatisticsService.calculate_mismatch_metrics(190, 10)
    assert tot == 200
    assert math.isclose(ratio, 0.05, abs_tol=1e-5)

    tot, ratio = StatisticsService.calculate_mismatch_metrics(0, 0)
    assert tot == 0
    assert ratio == 0.0


def test_fisher_zero_mismatch_safe_serialization():
    # 205 operations with zero mismatches against 1% baseline error
    res = StatisticsService.run_fisher_exact_test(match_count=205, mismatch_count=0)
    assert res["statistical_verdict"] == "ACCEPTABLE"
    assert res["p_value"] >= 0.01
    assert "contingency_table" in res
    assert res["odds_ratio"] is None or isinstance(res["odds_ratio"], float)
    assert "odds_ratio_display" in res
    assert "explanation" in res
    assert "ACCEPT" in res["explanation"]


def test_fisher_elevated_mismatch_forgery():
    # 205 operations with 35 mismatches (~17% error rate, far exceeding 1% baseline)
    res = StatisticsService.run_fisher_exact_test(match_count=170, mismatch_count=35)
    assert res["statistical_verdict"] == "SUSPICIOUS"
    assert res["p_value"] < 0.01
    assert "REJECT" in res["explanation"]


def test_fisher_custom_thresholds():
    # Strict alpha=0.001
    res = StatisticsService.run_fisher_exact_test(
        match_count=195,
        mismatch_count=10,
        baseline_error_rate=0.01,
        significance_alpha=0.001,
        mismatch_threshold_ratio=0.02
    )
    # Even if p_value might be moderate, mismatch_ratio (10/205 ~ 4.8%) > threshold_ratio (2%) triggers suspicious
    assert res["statistical_verdict"] == "SUSPICIOUS"
