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
    is_intercepted: bool = False
    effective_fidelity: float = 1.0
    detector_efficiency: float = 0.90


class NetworkQuantumAdapter:
    """
    Couples SeQUeNCe discrete-event network state and adversary actions
    into physical parameters affecting CUDA-Q circuit outcomes.
    """

    @staticmethod
    def werner_fidelity_to_depolarizing_p(fidelity: float) -> float:
        """
        Maps quantum channel Werner state fidelity to single-qubit depolarizing error probability:
        p = 1.5 * (1.0 - F), bounded to [0.0, 1.0].
        """
        return min(1.0, max(0.0, 1.5 * (1.0 - fidelity)))

    @classmethod
    def map_network_to_perturbation(
        cls,
        network_telemetry: Dict[str, Any],
        active_attack: Optional[str] = None,
        attack_params: Optional[Dict[str, Any]] = None
    ) -> NetworkPerturbation:
        params = attack_params or {}
        fidelity = network_telemetry.get("quantum_physical_metrics", {}).get("state_fidelity_post_transmission", 0.99)
        det_eff = network_telemetry.get("quantum_physical_metrics", {}).get("detector_quantum_efficiency", 0.90)

        # Depolarizing noise probability derived from channel state fidelity:
        # For single-qubit Werner state / depolarizing channel: p = 1.5 * (1.0 - F)
        # Bounded strictly to [0.0, 1.0]
        depol_p = cls.werner_fidelity_to_depolarizing_p(fidelity)

        attack_upper = (active_attack or "").upper().strip()

        if attack_upper in ("QUANTUM_BIT_FLIP_FORGERY", "MEASUREMENT_MANIPULATION"):
            flip_intensity = float(params.get("intensity", 0.30))
            return NetworkPerturbation(
                bit_flip_prob=flip_intensity,
                effective_fidelity=max(0.0, fidelity * (1.0 - flip_intensity)),
                phase_drift_rad=0.0,
                depolarization_prob=depol_p,
                detector_efficiency=det_eff
            )

        elif attack_upper in ("QUANTUM_PHASE_FLIP_DEPOLARIZATION", "DEPOLARIZATION"):
            phase_shift = float(params.get("phase_shift_rad", math.pi / 2.0))
            add_depol = float(params.get("depolarization_prob", 0.20))
            total_depol = min(1.0, depol_p + add_depol)
            return NetworkPerturbation(
                phase_drift_rad=phase_shift,
                depolarization_prob=total_depol,
                effective_fidelity=max(0.0, fidelity * (1.0 - total_depol)),
                detector_efficiency=det_eff
            )

        elif attack_upper in ("QUANTUM_BASIS_ALTERATION", "BASIS_MANIPULATION"):
            rot_angle = float(params.get("rotation_angle_rad", math.pi / 2.0))  # 90-degree orthogonal basis rotation
            return NetworkPerturbation(
                basis_rotation_rad=rot_angle,
                depolarization_prob=depol_p,
                effective_fidelity=max(0.0, fidelity * 0.50),
                detector_efficiency=det_eff
            )

        elif attack_upper in ("QUANTUM_STATE_REPLACEMENT",):
            return NetworkPerturbation(
                phase_drift_rad=math.pi / 2.0,
                depolarization_prob=0.40,
                basis_rotation_rad=math.pi / 4.0,
                effective_fidelity=max(0.0, fidelity * 0.50),
                detector_efficiency=det_eff
            )

        elif attack_upper in ("INTERCEPT_AND_RESEND",):
            # Eve intercepts at mid-span: projective measurement and re-preparation
            return NetworkPerturbation(
                is_intercepted=True,
                depolarization_prob=depol_p,
                effective_fidelity=max(0.0, fidelity * 0.75),
                detector_efficiency=det_eff
            )

        elif attack_upper in ("QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS", "DENIAL_OF_SERVICE"):
            # Bell entanglement link completely severed
            return NetworkPerturbation(
                is_severed=True,
                effective_fidelity=0.0,
                detector_efficiency=det_eff
            )

        elif attack_upper in ("UNCLASSIFIED_QUANTUM_DISTURBANCE", "CUSTOM_QUANTUM_NOISE", "QUANTUM_NOISE_INJECTION") or any(k in params for k in ("rotation_angle_rad", "basis_rotation_rad", "tilt_rad", "unclassified_tilt_rad", "phase_shift_rad", "continuous_noise", "depolarization_prob", "bit_flip_prob")):
            # Unclassified physical pre-measurement disturbance (continuous rotation, tilt, or continuous noise)
            rot_angle = float(params.get("rotation_angle_rad") or params.get("basis_rotation_rad") or params.get("tilt_rad") or params.get("unclassified_tilt_rad") or 0.0)
            phase_shift = float(params.get("phase_shift_rad") or params.get("phase_drift_rad") or 0.0)
            add_depol = float(params.get("depolarization_prob") or params.get("continuous_noise") or 0.0)
            flip_prob = float(params.get("bit_flip_prob") or 0.0)
            if rot_angle == 0.0 and phase_shift == 0.0 and add_depol == 0.0 and flip_prob == 0.0:
                rot_angle = math.pi / 3.0  # default 60-degree non-orthogonal tilt
                add_depol = 0.20
            total_depol = min(1.0, depol_p + add_depol)
            return NetworkPerturbation(
                phase_drift_rad=phase_shift if phase_shift != 0.0 else 0.005,
                basis_rotation_rad=rot_angle,
                bit_flip_prob=flip_prob,
                depolarization_prob=total_depol,
                effective_fidelity=max(0.0, fidelity * (1.0 - max(flip_prob, add_depol, abs(rot_angle) / (math.pi / 2.0)))),
                detector_efficiency=det_eff
            )

        # Baseline authentic quantum channel
        return NetworkPerturbation(
            phase_drift_rad=0.005,
            depolarization_prob=depol_p,
            effective_fidelity=fidelity,
            detector_efficiency=det_eff
        )
