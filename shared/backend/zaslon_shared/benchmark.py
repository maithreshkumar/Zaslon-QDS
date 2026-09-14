from __future__ import annotations

import statistics
from typing import Any, Iterable, Literal

from scipy.stats import sem, t

from .attacks import _diagnostic_family_detection
from .quantum import (
    NoiseConfig,
    Pauli,
    create_quantum_engine,
    derive_simulation_seed,
    run_channel_diagnostic,
)
from .security_analysis import calibrate_threshold, wilson_interval


BenchmarkScenario = Literal[
    "HONEST",
    "BIT_FLIP",
    "PHASE_FLIP",
    "Y_ATTACK",
    "DEPOLARIZING",
    "INTERCEPT_RESEND",
    "BELL_RESULT_MANIPULATION",
    "CORRECTION_MITM",
]


def _is_negative_control(row: dict[str, Any]) -> bool:
    """Treat honest rows and zero-strength attack labels as null controls."""
    return row["scenario"] == "HONEST" or float(row["strength"]) <= 0.0


def _mean_confidence_interval(values: list[float]) -> list[float]:
    if not values:
        raise ValueError("values cannot be empty")
    mean = statistics.fmean(values)
    if len(values) == 1 or len(set(values)) == 1:
        return [mean, mean]
    margin = float(t.ppf(0.975, len(values) - 1) * sem(values))
    return [max(0.0, mean - margin), min(1.0, mean + margin)]


def _scenario_parameters(scenario: BenchmarkScenario) -> dict[str, Any]:
    if scenario == "BIT_FLIP":
        return {"output_pauli": "X"}
    if scenario == "PHASE_FLIP":
        return {"output_pauli": "Z"}
    if scenario == "Y_ATTACK":
        return {"output_pauli": "Y"}
    if scenario == "INTERCEPT_RESEND":
        return {"intercept": True}
    if scenario == "BELL_RESULT_MANIPULATION":
        return {"correction_flip_mask": 3}
    if scenario == "CORRECTION_MITM":
        return {"correction_flip_mask": 1}
    return {}


def run_detector_benchmark(
    *,
    engine_name: str,
    scenarios: Iterable[BenchmarkScenario],
    strengths: Iterable[float],
    repetitions: int,
    shots_per_basis: int,
    seed: int,
    normal_noise: NoiseConfig | None = None,
    evaluation_noise: NoiseConfig | None = None,
    family_alpha: float = 0.01,
) -> dict[str, Any]:
    """Run reproducible independent channel-detector experiments.

    This harness benchmarks empirical detection behavior. It does not turn the
    resulting rates into a universal QDS security guarantee.
    """
    scenario_list = list(dict.fromkeys(scenarios))
    strength_list = sorted(set(float(value) for value in strengths))
    if not scenario_list or not strength_list:
        raise ValueError("at least one scenario and strength are required")
    if not 1 <= repetitions <= 200:
        raise ValueError("repetitions must be between 1 and 200")
    if any(not 0.0 <= value <= 1.0 for value in strength_list):
        raise ValueError("strengths must be in [0, 1]")
    base_noise = normal_noise or NoiseConfig()
    held_out_noise = evaluation_noise or base_noise
    records: list[dict[str, Any]] = []
    for dataset in ("CALIBRATION", "HELD_OUT_EVALUATION"):
      dataset_noise = base_noise if dataset == "CALIBRATION" else held_out_noise
      for scenario in scenario_list:
        for strength in strength_list:
          for repetition in range(repetitions):
                run_seed = derive_simulation_seed(
                    seed,
                    f"BENCHMARK|{dataset}|{scenario}|{strength:.12g}|{repetition}",
                )
                honest_engine = create_quantum_engine(
                    engine_name, derive_simulation_seed(run_seed, "HONEST_ENGINE")
                )
                attacked_engine = create_quantum_engine(
                    engine_name, derive_simulation_seed(run_seed, "ATTACK_ENGINE")
                )
                honest = run_channel_diagnostic(
                    honest_engine,
                    shots_per_basis=shots_per_basis,
                    master_seed=derive_simulation_seed(run_seed, "HONEST_DIAGNOSTIC"),
                    noise=dataset_noise,
                )
                parameters = _scenario_parameters(scenario)
                attack_strength = 0.0 if scenario in {"HONEST", "DEPOLARIZING"} else strength
                attack_noise = dataset_noise
                if scenario == "DEPOLARIZING":
                    values = dataset_noise.model_dump()
                    values["output_depolarizing"] = strength
                    attack_noise = NoiseConfig(**values)
                attacked = run_channel_diagnostic(
                    attacked_engine,
                    shots_per_basis=shots_per_basis,
                    master_seed=derive_simulation_seed(run_seed, "ATTACK_DIAGNOSTIC"),
                    attack_strength=attack_strength,
                    noise=attack_noise,
                    output_pauli=parameters.get("output_pauli", "I"),
                    intercept=parameters.get("intercept", False),
                    correction_flip_mask=parameters.get("correction_flip_mask", 0),
                )
                statistics_result = _diagnostic_family_detection(
                    honest, attacked, alpha=family_alpha
                )
                adjusted_values = [
                    item["adjusted_p_value"] for item in statistics_result["basis_tests"]
                ]
                records.append({
                    "dataset": dataset,
                    "scenario": scenario,
                    "strength": strength,
                    "repetition": repetition,
                    "seed": run_seed,
                    "z_error_rate": attacked["z_basis_error_rate"],
                    "x_error_rate": attacked["x_basis_error_rate"],
                    "combined_qber": attacked["combined_channel_disturbance"],
                    "mean_fidelity": attacked["mean_teleportation_fidelity"],
                    "minimum_adjusted_p_value": min(adjusted_values),
                    "detected": statistics_result["decision"] == "ATTACK_DETECTED",
                    "statistics": statistics_result,
                })
    calibration_records = [row for row in records if row["dataset"] == "CALIBRATION"]
    evaluation_records = [
        row for row in records if row["dataset"] == "HELD_OUT_EVALUATION"
    ]
    aggregates: list[dict[str, Any]] = []
    for scenario in scenario_list:
        for strength in strength_list:
            group = [
                row for row in evaluation_records
                if row["scenario"] == scenario and row["strength"] == strength
            ]
            qbers = [float(row["combined_qber"]) for row in group]
            detections = sum(bool(row["detected"]) for row in group)
            fidelities = [
                float(row["mean_fidelity"])
                for row in group if row["mean_fidelity"] is not None
            ]
            aggregates.append({
                "scenario": scenario,
                "strength": strength,
                "trials": len(group),
                "mean_qber": statistics.fmean(qbers),
                "median_qber": statistics.median(qbers),
                "mean_qber_95_percent_ci": _mean_confidence_interval(qbers),
                "detection_probability": detections / len(group),
                "detection_probability_wilson_95": wilson_interval(detections, len(group)),
                "mean_fidelity": statistics.fmean(fidelities) if fidelities else None,
                "mean_adjusted_p_value": statistics.fmean(
                    float(row["minimum_adjusted_p_value"]) for row in group
                ),
            })
    negative_control_rates = [
        float(row["combined_qber"])
        for row in calibration_records if _is_negative_control(row)
    ]
    attack_rates = [
        float(row["combined_qber"])
        for row in calibration_records if not _is_negative_control(row)
    ]
    threshold_calibration = (
        calibrate_threshold(
            honest_mismatch_rates=negative_control_rates,
            attack_mismatch_rates=attack_rates,
            candidate_thresholds=sorted(set([*strength_list, 0.01, 0.02, 0.05, 0.10, 0.20])),
            maximum_false_positive_rate=0.05,
        )
        if negative_control_rates and attack_rates
        else None
    )
    false_positives = sum(
        bool(row["detected"])
        for row in evaluation_records if row["scenario"] == "HONEST"
    )
    honest_count = sum(row["scenario"] == "HONEST" for row in evaluation_records)
    held_out_threshold_evaluation = None
    if threshold_calibration and threshold_calibration.get("selected_threshold") is not None:
        selected_threshold = float(threshold_calibration["selected_threshold"])
        evaluation_negative_controls = [
            float(row["combined_qber"])
            for row in evaluation_records if _is_negative_control(row)
        ]
        evaluation_attacks = [
            float(row["combined_qber"])
            for row in evaluation_records if not _is_negative_control(row)
        ]
        fp = sum(value > selected_threshold for value in evaluation_negative_controls)
        tn = len(evaluation_negative_controls) - fp
        tp = sum(value > selected_threshold for value in evaluation_attacks)
        fn = len(evaluation_attacks) - tp
        from .security_analysis import classifier_metrics

        held_out_threshold_evaluation = {
            "dataset": "INDEPENDENT_SEEDED_HELD_OUT_EVALUATION",
            "selected_threshold_from_calibration_only": selected_threshold,
            "calibration_seed_domain": "BENCHMARK|CALIBRATION",
            "evaluation_seed_domain": "BENCHMARK|HELD_OUT_EVALUATION",
            "calibration_record_count": len(calibration_records),
            "evaluation_record_count": len(evaluation_records),
            "negative_control_policy": "HONEST_OR_ZERO_ATTACK_STRENGTH",
            "evaluation_negative_control_count": len(evaluation_negative_controls),
            "evaluation_positive_attack_count": len(evaluation_attacks),
            "metrics": classifier_metrics(tp=tp, tn=tn, fp=fp, fn=fn),
            "noise_profile": held_out_noise.model_dump(),
            "claim": "HELD-OUT EMPIRICAL PERFORMANCE; NOT A SECURITY PROOF",
        }
    return {
        "benchmark": "REPRODUCIBLE_NON_AI_CHANNEL_DETECTOR_EVALUATION",
        "engine": engine_name,
        "shots_per_basis": shots_per_basis,
        "repetitions_per_dataset": repetitions,
        "dataset_split": "INDEPENDENT_DOMAIN_SEPARATED_CALIBRATION_AND_HELD_OUT_EVALUATION",
        "calibration_noise_profile": base_noise.model_dump(),
        "held_out_noise_profile": held_out_noise.model_dump(),
        "family_correction": "HOLM_FWER_ACROSS_Z_AND_X_PER_RUN",
        "family_alpha": family_alpha,
        "records": records,
        "aggregates": aggregates,
        "threshold_calibration": threshold_calibration,
        "held_out_threshold_evaluation": held_out_threshold_evaluation,
        "false_positive_rate": false_positives / honest_count if honest_count else None,
        "honest_acceptance_rate": 1 - false_positives / honest_count if honest_count else None,
        "honest_abort_rate": false_positives / honest_count if honest_count else None,
        "claim": "EMPIRICAL BENCHMARK; NOT A FORMAL QDS SECURITY PROOF",
    }
