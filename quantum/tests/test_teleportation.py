"""
Unit and fidelity tests for NVIDIA CUDA-Q 3-qubit quantum teleportation circuits.
"""
import pytest
import math
import hashlib

from service.circuits.teleportation import execute_teleportation_circuit, CUDA_Q_AVAILABLE
from service.circuits.state_prep import derive_teleportation_parameters
from service.engine import QuantumTeleportationEngine


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_cudaq_runtime_active():
    assert CUDA_Q_AVAILABLE is True
    engine = QuantumTeleportationEngine()
    avail = engine.check_availability()
    assert avail["cuda_q_available"] is True
    assert avail["status"] == "READY"


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_teleport_basis_state_zero():
    # |0> in computational basis Z (theta=0, phi=0, basis=Z) -> expected Bob bit = 0
    res = execute_teleportation_circuit(theta=0.0, phi=0.0, basis="Z", shots=1)
    assert res["bob_observed_bit"] == 0
    assert "counts" in res
    assert "m0" in res and "m1" in res


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_teleport_basis_state_one():
    # |1> in computational basis Z (theta=pi, phi=0, basis=Z) -> expected Bob bit = 1
    res = execute_teleportation_circuit(theta=math.pi, phi=0.0, basis="Z", shots=1)
    assert res["bob_observed_bit"] == 1


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_teleport_hadamard_plus_state():
    # |+> in Hadamard basis X (theta=pi/2, phi=0, basis=X) -> expected Bob bit = 0
    res = execute_teleportation_circuit(theta=math.pi / 2.0, phi=0.0, basis="X", shots=1)
    assert res["bob_observed_bit"] == 0


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_teleport_hadamard_minus_state():
    # |-> in Hadamard basis X (theta=pi/2, phi=pi, basis=X) -> expected Bob bit = 1
    res = execute_teleportation_circuit(theta=math.pi / 2.0, phi=math.pi, basis="X", shots=1)
    assert res["bob_observed_bit"] == 1


@pytest.mark.skipif(not CUDA_Q_AVAILABLE, reason="CUDA-Q runtime not available in this environment")
def test_engine_batch_execution_fidelity():
    digest = hashlib.sha512(b"Zaslon-QDS Fidelity Benchmark").hexdigest()
    engine = QuantumTeleportationEngine()
    batch_res = engine.execute_batch(
        sha512_digest=digest,
        start_index=0,
        batch_size=64,
        total_count=64
    )

    assert batch_res["batch_size"] == 64
    assert len(batch_res["measurements"]) == 64
    assert batch_res["duration_ms"] > 0

    # In noiseless quantum simulation, fidelity must be 100% (all match)
    matches = sum(1 for m in batch_res["measurements"] if m["is_match"])
    assert matches == 64
