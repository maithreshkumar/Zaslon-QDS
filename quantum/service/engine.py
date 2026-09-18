"""
Quantum Teleportation Engine.
Coordinates batch execution of 3-qubit circuits, timing, and error handling.
"""
import time
import logging
from typing import List, Dict, Any

from .circuits.teleportation import execute_teleportation_circuit, CUDA_Q_AVAILABLE
from .circuits.state_prep import derive_teleportation_parameters

logger = logging.getLogger("zaslon.quantum.engine")


class QuantumTeleportationEngine:
    def __init__(self, target_backend: str = "default"):
        self.target_backend = target_backend
        self.cuda_q_available = CUDA_Q_AVAILABLE

    def check_availability(self) -> Dict[str, Any]:
        return {
            "cuda_q_available": self.cuda_q_available,
            "target_backend": self.target_backend,
            "status": "READY" if self.cuda_q_available else "CUDA_Q_UNAVAILABLE"
        }

    def execute_batch(
        self,
        sha512_digest: str,
        start_index: int,
        batch_size: int,
        total_count: int = 4096
    ) -> Dict[str, Any]:
        """
        Executes a batch of teleportation circuits derived from the SHA-512 digest.
        """
        if not self.cuda_q_available:
            raise RuntimeError(
                "CUDA_Q_UNAVAILABLE: CUDA-Q is required to execute quantum teleportation circuits. "
                "Ensure the service is running in a CUDA-Q supported environment."
            )

        start_time = time.perf_counter()
        
        # Derive parameters deterministically from the SHA-512 digest
        all_params = derive_teleportation_parameters(sha512_digest, total_count=total_count)
        
        end_index = min(start_index + batch_size, total_count)
        batch_params = all_params[start_index:end_index]
        
        results: List[Dict[str, Any]] = []

        for p in batch_params:
            op_idx = p["operation_index"]
            theta = p["prep_theta"]
            phi = p["prep_phi"]
            basis = p["basis"]
            expected_bit = p["expected_bit"]

            circ_res = execute_teleportation_circuit(theta, phi, basis, shots=1)
            bob_bit = circ_res["bob_observed_bit"]
            is_match = (bob_bit == expected_bit)

            results.append({
                "operation_index": op_idx,
                "prep_theta": theta,
                "prep_phi": phi,
                "basis": basis,
                "expected_bit": expected_bit,
                "alice_m0": circ_res["m0"],
                "alice_m1": circ_res["m1"],
                "bob_correction_x": circ_res["correction_x"],
                "bob_correction_z": circ_res["correction_z"],
                "bob_observed_bit": bob_bit,
                "is_match": is_match
            })

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "start_index": start_index,
            "batch_size": len(results),
            "total_count": total_count,
            "duration_ms": duration_ms,
            "measurements": results
        }
