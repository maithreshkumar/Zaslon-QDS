from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "backend"))

from zaslon_shared.quantum import (  # noqa: E402
    CudaQEngine,
    NoiseConfig,
    QiskitAerEngine,
    ReferenceStatevectorEngine,
    run_channel_diagnostic,
)


def _rates(engine, noise: NoiseConfig) -> dict:
    started = time.perf_counter()
    result = run_channel_diagnostic(
        engine,
        shots_per_basis=256,
        master_seed=261500,
        noise=noise,
        disturbance_threshold=1.0,
    )
    return {
        "z_error_rate": result["z_basis_error_rate"],
        "x_error_rate": result["x_basis_error_rate"],
        "combined_qber": result["combined_channel_disturbance"],
        "engine": result["engine"],
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> Path:
    noise = NoiseConfig(
        bit_flip=0.12,
        phase_flip=0.10,
        depolarizing=0.08,
        output_bit_flip=0.06,
        output_phase_flip=0.04,
        output_depolarizing=0.07,
        measurement_error=0.05,
    )
    results = {
        "reference": _rates(ReferenceStatevectorEngine(seed=261500), noise),
        "qiskit_aer": _rates(QiskitAerEngine(seed=261500), noise),
        "cudaq": _rates(CudaQEngine(seed=261500), noise),
    }
    reference = results["reference"]
    comparisons = {}
    for name in ("qiskit_aer", "cudaq"):
        comparisons[name] = {
            "z_absolute_difference": abs(results[name]["z_error_rate"] - reference["z_error_rate"]),
            "x_absolute_difference": abs(results[name]["x_error_rate"] - reference["x_error_rate"]),
            "within_configured_tolerance_0_10": (
                abs(results[name]["z_error_rate"] - reference["z_error_rate"]) <= 0.10
                and abs(results[name]["x_error_rate"] - reference["x_error_rate"]) <= 0.10
            ),
            "method": "ABSOLUTE_QBER_DIFFERENCE_NOT_STATISTICAL_EQUIVALENCE",
        }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shots_per_basis": 256,
        "noise": noise.model_dump(),
        "noise_semantics": noise.semantics(),
        "results": results,
        "comparisons": comparisons,
        "passed": all(item["within_configured_tolerance_0_10"] for item in comparisons.values()),
    }
    destination = Path(
        os.getenv("ZASLON_VALIDATION_OUTPUT", str(ROOT / "CUDA_VALIDATION_RESULTS.json"))
    )
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(main())
