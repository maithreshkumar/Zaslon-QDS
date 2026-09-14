from __future__ import annotations

import json

import cudaq

from zaslon_shared.config import settings
from zaslon_shared.quantum import (
    PRODUCTION_BELL_STATE,
    CudaQEngine,
    cross_validate_quantum_engines,
)


def main() -> None:
    gpu_count = int(cudaq.num_available_gpus())
    if gpu_count < 1:
        raise SystemExit("CUDA-Q loaded, but it cannot see an NVIDIA GPU in this environment.")

    engine = CudaQEngine(seed=2026)
    if not engine.metadata.gpu:
        raise SystemExit(
            f"CUDA-Q target is {engine.metadata.target!r}, not an NVIDIA GPU target."
        )

    expected_correlations = {
        "PHI_PLUS": (1, 1),
        "PHI_MINUS": (1, -1),
        "PSI_PLUS": (-1, 1),
        "PSI_MINUS": (-1, -1),
    }
    bell_state_diagnostics = {
        state: engine.diagnose_bell_pair(shots=2048, preparation=state)
        for state in expected_correlations
    }
    entanglement = bell_state_diagnostics[PRODUCTION_BELL_STATE]
    independent_control = engine.diagnose_bell_pair(
        shots=512, preparation="INDEPENDENT"
    )
    broken_control = engine.diagnose_bell_pair(
        shots=512, preparation="BROKEN_NO_CNOT"
    )
    for state, diagnostic in bell_state_diagnostics.items():
        if diagnostic["observed_state"] != state or not diagnostic["verified"]:
            raise SystemExit(f"CUDA-Q failed to classify the expected {state} Bell preparation.")
        expected_zz, expected_xx = expected_correlations[state]
        if expected_zz * diagnostic["z_basis"]["correlation"] < 0.90:
            raise SystemExit(f"CUDA-Q {state} Z correlation had the wrong sign or magnitude.")
        if expected_xx * diagnostic["x_basis"]["correlation"] < 0.90:
            raise SystemExit(f"CUDA-Q {state} X correlation had the wrong sign or magnitude.")
    if independent_control["verified"]:
        raise SystemExit("Independent |00> qubits were incorrectly classified as entangled.")
    if broken_control["verified"]:
        raise SystemExit("The H-without-CNOT control was incorrectly classified as entangled.")

    for bit in (0, 1):
        outcomes = [
            engine.teleport_and_measure(
                bit=bit, preparation_basis="Z", measurement_basis="Z"
            ).bob_outcome
            for _ in range(16)
        ]
        if any(outcome != bit for outcome in outcomes):
            raise SystemExit(
                f"Ideal CUDA-Q computational-basis teleportation failed for |{bit}>."
            )

    cross_validation = cross_validate_quantum_engines(
        primary_engine_name="cudaq", shots=256, seed=2026, tolerance=0.12
    )
    report = {
        "cudaq": engine.metadata.model_dump(),
        "entanglement": entanglement,
        "bell_state_diagnostics": bell_state_diagnostics,
        "production_bell_state_analysis": {
            "preparation_mode": "UNIFORM",
            "configured_states": [PRODUCTION_BELL_STATE],
            "distinct_bell_states_used": 1,
            "all_same": True,
            "states_used_per_qds_session": {
                "PHI_PLUS": 512 * 2 * settings.states_per_candidate,
                "PHI_MINUS": 0,
                "PSI_PLUS": 0,
                "PSI_MINUS": 0,
            },
            "expected_state": PRODUCTION_BELL_STATE,
            "observed_state": entanglement["observed_state"],
            "matches_expected": entanglement["matches_expected"],
            "diagnostic_shots_are_fresh_circuit_executions": True,
        },
        "negative_controls": {
            "independent_00": independent_control,
            "broken_no_cnot": broken_control,
        },
        "teleportation": {
            "computational_basis_checks_per_bit": 16,
            "completed": True,
        },
        "qiskit_cross_validation": cross_validation,
    }
    print(json.dumps(report, indent=2))
    if not cross_validation["comparison"]["within_configured_tolerance"]:
        raise SystemExit("CUDA-Q and Qiskit Aer exceeded the configured comparison tolerance.")
    print("CUDA-Q GPU execution and Qiskit Aer cross-validation passed.")


if __name__ == "__main__":
    main()
