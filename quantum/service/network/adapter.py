"""
CUDA-Q <-> SeQUeNCe Physical Coupling Adapter.
Translates photonic network dynamics (attenuation, delay, depolarization, Eve interception)
into explicit physical quantum perturbation parameters for CUDA-Q 3-qubit teleportation execution.
"""
from typing import Dict, Any, Optional
import math
from pydantic import BaseModel, Field


class QuantumMediumProfile(BaseModel):
    """Configurable physical parameters for the quantum communication medium."""
    profile_name: str = Field(default="demo-fiber-25km")
    medium_type: str = Field(default="single_mode_optical_fiber")
    channel_length_km: float = Field(default=25.0, ge=0.1)
    attenuation_db_per_km: float = Field(default=0.20, ge=0.0)
    wavelength_nm: float = Field(default=1550.0)
    speed_of_light_in_medium_mps: float = Field(default=2.04e8)
    detector_efficiency: float = Field(default=0.90, ge=0.1, le=1.0)
    detector_dark_count_hz: float = Field(default=100.0)
    memory_t2_coherence_ms: float = Field(default=10.0, ge=0.1)


class NetworkPerturbation(BaseModel):
    """Physical perturbations derived from SeQUeNCe network events and Eve attacks."""
    phase_drift_rad: float = 0.0
    depolarization_prob: float = 0.0
    basis_rotation_rad: float = 0.0
    bit_flip_prob: float = 0.0
    is_severed: bool = False
    effective_fidelity: float = 1.0


class NetworkQuantumAdapter:
    """
    Couples SeQUeNCe discrete-event network state and adversary actions
    into physical parameters affecting CUDA-Q circuit outcomes.
    """

    @staticmethod
    def map_network_to_perturbation(
        network_telemetry: Dict[str, Any],
        active_attack: Optional[str] = None,
        attack_params: Optional[Dict[str, Any]] = None
    ) -> NetworkPerturbation:
        params = attack_params or {}
        fidelity = network_telemetry.get("quantum_physical_metrics", {}).get("state_fidelity_post_transmission", 0.99)

        if active_attack == "QUANTUM_BIT_FLIP_FORGERY":
            flip_intensity = float(params.get("intensity", 0.30))
            return NetworkPerturbation(
                bit_flip_prob=flip_intensity,
                effective_fidelity=fidelity * (1.0 - flip_intensity),
                phase_drift_rad=0.0
            )

        elif active_attack == "QUANTUM_PHASE_FLIP_DEPOLARIZATION":
            phase_shift = float(params.get("phase_shift_rad", math.pi))
            depol_p = float(params.get("depolarization_prob", 0.25))
            return NetworkPerturbation(
                phase_drift_rad=phase_shift,
                depolarization_prob=depol_p,
                effective_fidelity=fidelity * 0.70
            )

        elif active_attack == "QUANTUM_BASIS_ALTERATION":
            rot_angle = float(params.get("rotation_angle_rad", math.pi / 2))
            return NetworkPerturbation(
                basis_rotation_rad=rot_angle,
                effective_fidelity=fidelity * 0.50
            )

        elif active_attack == "QUANTUM_STATE_REPLACEMENT":
            return NetworkPerturbation(
                phase_drift_rad=math.pi / 2,
                depolarization_prob=0.35,
                effective_fidelity=fidelity * 0.65
            )

        elif active_attack == "INTERCEPT_AND_RESEND":
            # Eve intercept-and-resend induces at least 25% error on incompatible measurement bases
            return NetworkPerturbation(
                bit_flip_prob=0.25,
                phase_drift_rad=math.pi / 4,
                effective_fidelity=fidelity * 0.75
            )

        elif active_attack == "QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS":
            return NetworkPerturbation(
                is_severed=True,
                effective_fidelity=0.0
            )

        # Baseline authentic channel
        return NetworkPerturbation(
            phase_drift_rad=0.01,
            depolarization_prob=0.005,
            effective_fidelity=fidelity
        )
