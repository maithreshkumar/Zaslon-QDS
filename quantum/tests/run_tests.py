"""
Test runner for quantum service inside the container using standard library.
"""
import sys
import os
import math
import hashlib

# Ensure /app is in sys.path
sys.path.insert(0, "/app")

from service.circuits.teleportation import execute_teleportation_circuit, CUDA_Q_AVAILABLE
from service.circuits.state_prep import derive_teleportation_parameters
from service.engine import QuantumTeleportationEngine


def run_all():
    print("=== Zaslon-QDS Quantum Verification Test Suite ===")
    print(f"CUDA-Q Available: {CUDA_Q_AVAILABLE}")
    assert CUDA_Q_AVAILABLE is True, "CUDA-Q must be available"

    engine = QuantumTeleportationEngine()
    avail = engine.check_availability()
    print(f"Engine Availability: {avail}")
    assert avail["status"] == "READY"

    print("\n--- Test 1: |0> in Z basis (expected 0) ---")
    r0 = execute_teleportation_circuit(theta=0.0, phi=0.0, basis="Z")
    print(f"Result: {r0}")
    assert r0["bob_observed_bit"] == 0, f"Expected 0, got {r0['bob_observed_bit']}"

    print("\n--- Test 2: |1> in Z basis (expected 1) ---")
    r1 = execute_teleportation_circuit(theta=math.pi, phi=0.0, basis="Z")
    print(f"Result: {r1}")
    assert r1["bob_observed_bit"] == 1, f"Expected 1, got {r1['bob_observed_bit']}"

    print("\n--- Test 3: |+> in X basis (expected 0) ---")
    rp = execute_teleportation_circuit(theta=math.pi / 2.0, phi=0.0, basis="X")
    print(f"Result: {rp}")
    assert rp["bob_observed_bit"] == 0, f"Expected 0, got {rp['bob_observed_bit']}"

    print("\n--- Test 4: |-> in X basis (expected 1) ---")
    rm = execute_teleportation_circuit(theta=math.pi / 2.0, phi=math.pi, basis="X")
    print(f"Result: {rm}")
    assert rm["bob_observed_bit"] == 1, f"Expected 1, got {rm['bob_observed_bit']}"

    print("\n--- Test 5: Batch Execution of 128 Circuits from SHA-512 ---")
    digest = hashlib.sha512(b"Zaslon-QDS Production Batch Verification").hexdigest()
    batch_res = engine.execute_batch(
        sha512_digest=digest,
        start_index=0,
        batch_size=128,
        total_count=128
    )
    print(f"Executed 128 circuits in {batch_res['duration_ms']:.2f}ms")
    matches = sum(1 for m in batch_res["measurements"] if m["is_match"])
    mismatches = 128 - matches
    print(f"Matches: {matches}/128 (100.0% fidelity), Mismatches: {mismatches}")
    assert matches == 128, f"Expected 128 matches, got {matches}"

    print("\n=======================================================")
    print("ALL QUANTUM TELEPORTATION TESTS PASSED WITH 100% FIDELITY!")
    print("=======================================================")


if __name__ == "__main__":
    run_all()
