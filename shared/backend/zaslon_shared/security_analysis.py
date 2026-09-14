from __future__ import annotations

import math
from typing import Iterable

from scipy.stats import binom


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("successes/trials are invalid")
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def holm_adjust(p_values: Iterable[float], *, alpha: float = 0.01) -> list[dict]:
    """Holm family-wise error correction for a pre-declared test family."""
    values = [float(value) for value in p_values]
    if not values or any(not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("p-values must be a non-empty collection in [0, 1]")
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    adjusted_sorted: list[float] = []
    running_max = 0.0
    family_size = len(values)
    for rank, (_, value) in enumerate(ordered, start=1):
        adjusted = min(1.0, (family_size - rank + 1) * value)
        running_max = max(running_max, adjusted)
        adjusted_sorted.append(running_max)
    results: list[dict | None] = [None] * family_size
    for (original_index, raw), adjusted in zip(ordered, adjusted_sorted, strict=True):
        results[original_index] = {
            "raw_p_value": raw,
            "adjusted_p_value": adjusted,
            "family_size": family_size,
            "alpha": alpha,
            "decision": "REJECT_NULL" if adjusted < alpha else "DO_NOT_REJECT_NULL",
            "correction": "HOLM_FWER",
            "interpretation": (
                "A p-value is not an attack probability and is not the probability that "
                "the null hypothesis is true."
            ),
        }
    return [item for item in results if item is not None]


def classifier_metrics(*, tp: int, tn: int, fp: int, fn: int) -> dict:
    if min(tp, tn, fp, fn) < 0:
        raise ValueError("confusion counts cannot be negative")

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    tpr = ratio(tp, tp + fn)
    tnr = ratio(tn, tn + fp)
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tpr_sensitivity": tpr,
        "tnr_specificity": tnr,
        "fpr": ratio(fp, fp + tn),
        "fnr": ratio(fn, fn + tp),
        "precision": ratio(tp, tp + fp),
        "accuracy": ratio(tp + tn, tp + tn + fp + fn),
        "balanced_accuracy": (tpr + tnr) / 2 if tpr is not None and tnr is not None else None,
        "honest_acceptance_rate": tnr,
        "honest_abort_rate": ratio(fp, fp + tn),
    }


def calibrate_threshold(
    *,
    honest_mismatch_rates: Iterable[float],
    attack_mismatch_rates: Iterable[float],
    candidate_thresholds: Iterable[float],
    maximum_false_positive_rate: float = 0.05,
) -> dict:
    honest = [float(value) for value in honest_mismatch_rates]
    attacks = [float(value) for value in attack_mismatch_rates]
    candidates = sorted(set(float(value) for value in candidate_thresholds))
    if not honest or not attacks or not candidates:
        raise ValueError("honest, attack, and threshold samples are required")
    if any(not 0 <= value <= 1 for value in [*honest, *attacks, *candidates]):
        raise ValueError("rates and thresholds must be in [0, 1]")
    rows = []
    for threshold in candidates:
        # A run is rejected/detected when its mismatch rate exceeds the threshold.
        fp = sum(value > threshold for value in honest)
        tn = len(honest) - fp
        tp = sum(value > threshold for value in attacks)
        fn = len(attacks) - tp
        rows.append({"threshold": threshold, **classifier_metrics(tp=tp, tn=tn, fp=fp, fn=fn)})
    eligible = [
        row for row in rows
        if row["fpr"] is not None and row["fpr"] <= maximum_false_positive_rate
    ]
    if not eligible:
        return {
            "selected_threshold": None,
            "objective": "MAXIMIZE_BALANCED_ACCURACY_SUBJECT_TO_FPR_LIMIT",
            "maximum_false_positive_rate": maximum_false_positive_rate,
            "status": "NO_CANDIDATE_SATISFIED_FALSE_POSITIVE_CONSTRAINT",
            "candidates": rows,
        }
    selected = max(
        eligible,
        key=lambda row: (row["balanced_accuracy"], row["tpr_sensitivity"], -row["threshold"]),
    )
    return {
        "selected_threshold": selected["threshold"],
        "selected_metrics": selected,
        "objective": "MAXIMIZE_BALANCED_ACCURACY_SUBJECT_TO_FPR_LIMIT",
        "maximum_false_positive_rate": maximum_false_positive_rate,
        "status": "CALIBRATED_EMPIRICALLY",
        "claim": "Empirical operating-point calibration; not a QDS security proof.",
        "candidates": rows,
    }


def restricted_binomial_forgery_analysis(
    *,
    signature_length: int,
    attacker_mismatch_probability: float,
    acceptance_threshold: float,
    independence_justified: bool,
    mismatch_probability_justified: bool,
) -> dict:
    assumptions = {
        "independent_bernoulli_mismatches": independence_justified,
        "known_fixed_attacker_mismatch_probability": mismatch_probability_justified,
        "acceptance_rule": "X <= floor(threshold * L)",
    }
    if signature_length <= 0:
        raise ValueError("signature_length must be positive")
    if not 0 <= attacker_mismatch_probability <= 1 or not 0 <= acceptance_threshold <= 1:
        raise ValueError("probabilities must be in [0, 1]")
    cutoff = math.floor(acceptance_threshold * signature_length)
    estimate = float(
        binom.cdf(cutoff, signature_length, attacker_mismatch_probability)
    )
    supported = independence_justified and mismatch_probability_justified
    return {
        "model": "RESTRICTED_IID_BERNOULLI_FORGER_MODEL",
        "label": "RESTRICTED MODEL BOUND" if supported else "REFERENCE BOUND",
        "formally_applies_to_zaslon": supported,
        "signature_length": signature_length,
        "attacker_mismatch_probability": attacker_mismatch_probability,
        "acceptance_threshold": acceptance_threshold,
        "accepted_mismatch_cutoff": cutoff,
        "binomial_lower_tail_probability": estimate,
        "equation": "P_accept = P[X <= floor(tL)], X ~ Binomial(L, p_e)",
        "assumptions": assumptions,
        "warning": (
            None if supported else
            "The implementation has not established every IID/fixed-p_e assumption; this value is comparative only."
        ),
    }

