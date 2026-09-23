"""
Quantum Teleportation Engine.
Coordinates batch execution of 3-qubit circuits, coupling with SeQUeNCe network simulation,
pre-measurement physical perturbations, timing, and error handling.
"""
import time
import logging
import random
import math
from typing import List, Dict, Any, Optional

from .circuits.teleportation import execute_teleportation_circuit, CUDA_Q_AVAILABLE
from .circuits.state_prep import derive_teleportation_parameters
from .network.simulator import simulate_qds_network
from .network.adapter import NetworkQuantumAdapter, QuantumMediumProfile

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
        total_count: int = 4096,
        phase_drift_rad: float = 0.0,
        basis_rotation_rad: float = 0.0,
        bit_flip: int = 0,
        is_intercepted: int = 0,
        is_severed: int = 0,
        simulation_seed: Optional[int] = None
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
        seed = simulation_seed if simulation_seed is not None else 42
        rng = random.Random(seed + start_index)

        for p in batch_params:
            op_idx = p["operation_index"]
            theta = p["prep_theta"]
            phi = p["prep_phi"]
            basis = p["basis"]
            expected_bit = p["expected_bit"]

            # Intercept basis chosen randomly/pseudo-randomly by Eve if intercepted
            intercept_basis = rng.randint(0, 1) if is_intercepted else 0

            circ_res = execute_teleportation_circuit(
                theta=theta,
                phi=phi,
                basis=basis,
                phase_drift_rad=phase_drift_rad,
                basis_rotation_rad=basis_rotation_rad,
                bit_flip=bit_flip,
                is_intercepted=is_intercepted,
                intercept_basis=intercept_basis,
                is_severed=is_severed,
                shots=1
            )
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

    def execute_coupled_teleportation(
        self,
        sha512_digest: str,
        start_index: int = 0,
        batch_size: int = 4096,
        total_count: int = 4096,
        fiber_distance_km: float = 25.0,
        attenuation_db_per_km: float = 0.20,
        active_attack: Optional[str] = None,
        attack_params: Optional[Dict[str, Any]] = None,
        noise_mode: str = "DEMO",
        simulation_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes coupled SeQUeNCe network simulation and CUDA-Q 3-qubit teleportation.
        Applies pre-measurement physical perturbations derived from the network state
        and adversary actions during in-flight transit before terminal measurement by Bob.
        """
        if not self.cuda_q_available:
            raise RuntimeError("CUDA_Q_UNAVAILABLE: NVIDIA CUDA-Q runtime is required.")

        seed_val = simulation_seed if simulation_seed is not None else 42
        start_time = time.perf_counter()

        # 1. Run SeQUeNCe discrete-event network simulation
        medium = QuantumMediumProfile(
            channel_length_km=fiber_distance_km,
            attenuation_db_per_km=attenuation_db_per_km
        )
        network_telemetry = simulate_qds_network(
            total_operations=total_count,
            medium_profile=medium,
            fiber_distance_km=fiber_distance_km,
            attenuation_db_per_km=attenuation_db_per_km,
            active_attack=active_attack,
            attack_params=attack_params,
            simulation_seed=seed_val
        )

        # 2. Map network telemetry & adversary actions to physical perturbations
        perturbation = NetworkQuantumAdapter.map_network_to_perturbation(
            network_telemetry=network_telemetry,
            active_attack=active_attack,
            attack_params=attack_params
        )

        # 3. Derive state preparation parameters from SHA-512
        all_params = derive_teleportation_parameters(sha512_digest, total_count=total_count)
        end_index = min(start_index + batch_size, total_count)
        batch_params = all_params[start_index:end_index]

        results: List[Dict[str, Any]] = []
        rng = random.Random(seed_val + start_index)

        # Apply noise mode settings
        # In IDEAL mode: zero perturbation unless actively attacked
        eff_phase_drift = 0.0 if (noise_mode == "IDEAL" and not active_attack) else perturbation.phase_drift_rad
        eff_basis_rot = perturbation.basis_rotation_rad
        is_intercepted_flag = 1 if perturbation.is_intercepted else 0
        is_severed_flag = 1 if perturbation.is_severed else 0

        for p in batch_params:
            op_idx = p["operation_index"]
            theta = p["prep_theta"]
            phi = p["prep_phi"]
            basis = p["basis"]
            expected_bit = p["expected_bit"]

            # Determine bit flip for this specific operation
            bit_flip_flag = 0
            if perturbation.bit_flip_prob > 0.0:
                if rng.random() < perturbation.bit_flip_prob:
                    bit_flip_flag = 1

            # Determine depolarizing error for this operation (Werner channel)
            current_phase_drift = eff_phase_drift
            if perturbation.depolarization_prob > 0.0 and noise_mode != "IDEAL":
                if rng.random() < perturbation.depolarization_prob:
                    # Depolarizing perturbation: random Pauli rotation
                    current_phase_drift += math.pi / 2.0

            # Intercept-and-resend basis selection by Eve (Z=0, X=1)
            # Eve chooses randomly with equal probability
            intercept_basis = rng.randint(0, 1) if is_intercepted_flag else 0

            circ_res = execute_teleportation_circuit(
                theta=theta,
                phi=phi,
                basis=basis,
                phase_drift_rad=current_phase_drift,
                basis_rotation_rad=eff_basis_rot,
                bit_flip=bit_flip_flag,
                is_intercepted=is_intercepted_flag,
                intercept_basis=intercept_basis,
                is_severed=is_severed_flag,
                shots=1
            )

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

        # Compute empirical match statistics
        matches = sum(1 for r in results if r["is_match"])
        mismatches = len(results) - matches
        empirical_error_rate = (mismatches / len(results)) if results else 0.0

        return {
            "start_index": start_index,
            "batch_size": len(results),
            "total_count": total_count,
            "duration_ms": duration_ms,
            "simulation_seed": seed_val,
            "noise_mode": noise_mode,
            "network_simulation": network_telemetry,
            "perturbation": perturbation.dict(),
            "empirical_statistics": {
                "matches": matches,
                "mismatches": mismatches,
                "total_measured": len(results),
                "observed_error_rate": round(empirical_error_rate, 4)
            },
            "measurements": results
        }
