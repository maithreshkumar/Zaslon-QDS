"""
Statistical Verification Service.
Executes Fisher's Exact Test on sample mismatch observations against theoretical error baselines.
"""
from scipy.stats import fisher_exact
from typing import Dict, Any, Tuple, Optional
import math
import logging

from ..core.config import settings

logger = logging.getLogger("zaslon.services.statistics")


class StatisticsService:
    @staticmethod
    def calculate_mismatch_metrics(
        matches: int,
        mismatches: int
    ) -> Tuple[int, float]:
        total = matches + mismatches
        ratio = (mismatches / total) if total > 0 else 0.0
        return total, ratio

    @staticmethod
    def run_fisher_exact_test(
        match_count: int,
        mismatch_count: int,
        baseline_error_rate: Optional[float] = None,
        significance_alpha: Optional[float] = None,
        mismatch_threshold_ratio: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Runs a one-sided Fisher's Exact Test on a 2x2 contingency table:

                         | Matched        | Mismatched
        -----------------+----------------+-----------------
        Observed Sample  | match_count    | mismatch_count
        Theoretical Null | ctrl_matches   | ctrl_mismatches

        Hypothesis:
        H0: The error rate of the transmitted quantum states is consistent with the authentic quantum channel baseline.
        H1: The error rate is significantly higher (indicating state disturbance / eavesdropping / forgery).
        """
        baseline_rate = baseline_error_rate if baseline_error_rate is not None else settings.BASELINE_ERROR_RATE
        alpha = significance_alpha if significance_alpha is not None else settings.FISHER_SIGNIFICANCE_ALPHA
        threshold_ratio = mismatch_threshold_ratio if mismatch_threshold_ratio is not None else settings.MISMATCH_THRESHOLD_RATIO

        sample_size = match_count + mismatch_count
        if sample_size == 0:
            return {
                "odds_ratio": 1.0,
                "odds_ratio_display": "1.0000",
                "p_value": 1.0,
                "statistical_verdict": "ACCEPTABLE",
                "contingency_table": [[0, 0], [0, 0]],
                "significance_alpha": alpha,
                "baseline_error_rate": baseline_rate,
                "mismatch_threshold_ratio": threshold_ratio,
                "explanation": "No samples available for statistical verification."
            }

        # Construct theoretical control baseline representing an undisturbed quantum channel
        ctrl_mismatches = max(0, int(round(sample_size * baseline_rate)))
        ctrl_matches = sample_size - ctrl_mismatches

        table = [
            [match_count, mismatch_count],
            [ctrl_matches, ctrl_mismatches]
        ]

        # Use alternative='less' on matches (sample match count is significantly lower than control)
        # scipy.stats.fisher_exact evaluates table [[a, b], [c, d]]
        # Odds ratio = (a*d) / (b*c).
        raw_odds_ratio, p_value = fisher_exact(table, alternative='less')

        # Handle infinite or NaN odds ratio for JSON compliance
        if math.isinf(raw_odds_ratio):
            safe_odds_ratio = None
            odds_ratio_display = "Infinity" if raw_odds_ratio > 0 else "-Infinity"
        elif math.isnan(raw_odds_ratio):
            safe_odds_ratio = None
            odds_ratio_display = "NaN"
        else:
            safe_odds_ratio = float(raw_odds_ratio)
            odds_ratio_display = f"{safe_odds_ratio:.4f}"

        obs_ratio = mismatch_count / sample_size
        is_suspicious = (p_value < alpha) or (obs_ratio > threshold_ratio)
        verdict = "SUSPICIOUS" if is_suspicious else "ACCEPTABLE"

        if verdict == "SUSPICIOUS":
            explanation = (
                f"Statistical test REJECTED: Observed mismatch ratio is {obs_ratio:.2%} "
                f"(threshold={threshold_ratio:.2%}) with Fisher p-value {p_value:.4e} < alpha {alpha}. "
                f"Quantum channel state disturbance indicates potential tampering or forgery."
            )
        else:
            explanation = (
                f"Statistical test ACCEPTED: Observed mismatch ratio is {obs_ratio:.2%} "
                f"within acceptable channel error baseline {baseline_rate:.2%} (Fisher p-value={p_value:.4f} >= alpha {alpha})."
            )

        logger.info(
            f"FISHER_EXACT_TEST: Sample={sample_size}, Mismatches={mismatch_count} (ratio={obs_ratio:.4f}), "
            f"p-value={p_value:.6e}, OddsRatio={odds_ratio_display}, Verdict={verdict}"
        )

        return {
            "odds_ratio": safe_odds_ratio,
            "odds_ratio_display": odds_ratio_display,
            "p_value": float(p_value),
            "statistical_verdict": verdict,
            "contingency_table": table,
            "significance_alpha": alpha,
            "baseline_error_rate": baseline_rate,
            "mismatch_threshold_ratio": threshold_ratio,
            "explanation": explanation
        }

