from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import hashlib
import math
import random
import threading
from typing import Any, Literal

import numpy as np

Basis = Literal["Z", "X"]
Pauli = Literal["I", "X", "Y", "Z"]
BellState = Literal["PHI_PLUS", "PHI_MINUS", "PSI_PLUS", "PSI_MINUS"]
BellPreparation = Literal[
    "PHI_PLUS",
    "PHI_MINUS",
    "PSI_PLUS",
    "PSI_MINUS",
    "INDEPENDENT",
    "BROKEN_NO_CNOT",
]
PRODUCTION_BELL_STATE: BellState = "PHI_PLUS"
_CUDAQ_GLOBAL_LOCK = threading.RLock()
_CUDAQ_CONFIGURED_TARGET: tuple[str, str] | None = None
BELL_STATE_CORRELATIONS: dict[BellState, tuple[int, int]] = {
    "PHI_PLUS": (1, 1),
    "PHI_MINUS": (1, -1),
    "PSI_PLUS": (-1, 1),
    "PSI_MINUS": (-1, -1),
}


@dataclass(frozen=True)
class NoiseConfig:
    """Canonical independent stochastic noise used by every quantum engine.

    The legacy four names are retained at the API boundary.  The first three are
    Bell-distribution noise applied to Bob's half after Bell-pair preparation and
    before teleportation.  Output terms are applied after feed-forward correction,
    and measurement error is a final classical readout-bit flip.
    """

    bit_flip: float = 0.0
    phase_flip: float = 0.0
    depolarizing: float = 0.0
    measurement_error: float = 0.0
    output_bit_flip: float = 0.0
    output_phase_flip: float = 0.0
    output_depolarizing: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    def model_dump(self) -> dict:
        return asdict(self)

    def semantics(self) -> dict[str, Any]:
        return {
            "model": "CANONICAL_INDEPENDENT_PAULI_V1",
            "composition_order": [
                "BELL_SOURCE_PREPARATION",
                "BELL_DISTRIBUTION_X",
                "BELL_DISTRIBUTION_Z",
                "BELL_DISTRIBUTION_DEPOLARIZING_PAULI",
                "ATTACK_AT_DECLARED_BOUNDARY",
                "TELEPORTATION_AND_FEED_FORWARD_CORRECTION",
                "BOB_OUTPUT_X",
                "BOB_OUTPUT_Z",
                "BOB_OUTPUT_DEPOLARIZING_PAULI",
                "BASIS_ROTATION",
                "CLASSICAL_MEASUREMENT_BIT_FLIP",
            ],
            "locations": {
                "bit_flip": "BELL_DISTRIBUTION_NOISE",
                "phase_flip": "BELL_DISTRIBUTION_NOISE",
                "depolarizing": "BELL_DISTRIBUTION_NOISE",
                "output_bit_flip": "BOB_OUTPUT_OR_MEMORY_NOISE",
                "output_phase_flip": "BOB_OUTPUT_OR_MEMORY_NOISE",
                "output_depolarizing": "BOB_OUTPUT_OR_MEMORY_NOISE",
                "measurement_error": "MEASUREMENT_NOISE",
            },
            "independence_assumption": (
                "Each configured Bernoulli event is sampled independently. Triggered "
                "Paulis compose in the documented order; later events never replace earlier ones."
            ),
        }


@dataclass(frozen=True)
class QuantumExecutionMetadata:
    engine: str
    target: str
    gpu: bool
    fallback_used: bool
    fallback_reason: str | None
    maximum_circuit_width: int = 3
    available_gpus: int | None = None

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TransmissionResult:
    bob_outcome: int
    bell_bits: tuple[int, int]
    input_state: tuple[complex, complex]
    output_state: tuple[complex, complex] | None
    fidelity: float | None


@dataclass(frozen=True)
class PendingTeleportation:
    """Receiver state awaiting classical correction delivery.

    Reference execution keeps the collapsed three-qubit state alive. CUDA-Q's
    current run boundary cannot retain a mid-circuit state across a SeQUeNCe
    event loop, so its context records the exact conditional receiver state
    parameters for a second CUDA-Q recovery kernel. That limitation is exposed
    in protocol metadata and is never described as a shared simulator state.
    """

    bell_bits: tuple[int, int]
    input_state: tuple[complex, complex]
    measurement_basis: Basis
    context: Any


class QuantumEngine(ABC):
    @property
    @abstractmethod
    def metadata(self) -> QuantumExecutionMetadata:
        raise NotImplementedError

    @abstractmethod
    def teleport_and_measure(
        self,
        *,
        bit: int,
        preparation_basis: Basis,
        measurement_basis: Basis,
        intercept: bool = False,
        eve_basis: Basis = "Z",
        entanglement_pauli: Pauli = "I",
        correction_flip_mask: int = 0,
        output_pauli: Pauli = "I",
        noise: NoiseConfig | None = None,
    ) -> TransmissionResult:
        raise NotImplementedError

    @abstractmethod
    def diagnose_bell_pair(
        self,
        *,
        shots: int = 2048,
        preparation: BellPreparation = "PHI_PLUS",
        correlation_threshold: float = 0.90,
        noise: NoiseConfig | None = None,
    ) -> dict[str, Any]:
        """Diagnose dedicated Bell-pair copies; never measure a production pair."""
        raise NotImplementedError

    def begin_networked_teleportation(self, **kwargs) -> PendingTeleportation:
        raise RuntimeError(
            f"{self.metadata.engine} does not implement staged network-mediated teleportation"
        )

    def complete_networked_teleportation(
        self,
        pending: PendingTeleportation,
        *,
        delivered_bell_bits: tuple[int, int],
    ) -> TransmissionResult:
        raise RuntimeError(
            f"{self.metadata.engine} does not implement staged network-mediated teleportation"
        )


I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
PAULI = {"I": I2, "X": X, "Y": Y, "Z": Z}
_PAULI_BITS: dict[Pauli, tuple[int, int]] = {
    "I": (0, 0),
    "X": (1, 0),
    "Y": (1, 1),
    "Z": (0, 1),
}
_BITS_PAULI: dict[tuple[int, int], Pauli] = {
    value: key for key, value in _PAULI_BITS.items()
}


def derive_simulation_seed(master_seed: int | None, domain: str) -> int:
    """Derive reproducible, domain-separated non-secret simulation randomness."""
    material = f"ZASLON-QDS-SIM-V1|{0 if master_seed is None else master_seed}|{domain}"
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def compose_paulis(*operations: Pauli) -> Pauli:
    """Compose Paulis up to global phase, which cannot affect measurement statistics."""
    x_bit = 0
    z_bit = 0
    for operation in operations:
        x_value, z_value = _PAULI_BITS[operation]
        x_bit ^= x_value
        z_bit ^= z_value
    return _BITS_PAULI[(x_bit, z_bit)]


def _sample_pauli_noise(
    rng: random.Random,
    *,
    bit_flip: float,
    phase_flip: float,
    depolarizing: float,
) -> Pauli:
    operations: list[Pauli] = []
    if rng.random() < bit_flip:
        operations.append("X")
    if rng.random() < phase_flip:
        operations.append("Z")
    if rng.random() < depolarizing:
        operations.append(rng.choice(["X", "Y", "Z"]))
    return compose_paulis(*operations)


def _sample_noise_events(noise: NoiseConfig, rng: random.Random) -> tuple[Pauli, Pauli, bool]:
    distribution = _sample_pauli_noise(
        rng,
        bit_flip=noise.bit_flip,
        phase_flip=noise.phase_flip,
        depolarizing=noise.depolarizing,
    )
    output = _sample_pauli_noise(
        rng,
        bit_flip=noise.output_bit_flip,
        phase_flip=noise.output_phase_flip,
        depolarizing=noise.output_depolarizing,
    )
    measurement_flip = rng.random() < noise.measurement_error
    return distribution, output, measurement_flip


def _normalized_two_qubit_counts(raw_counts: dict[str, int]) -> dict[str, int]:
    counts = {"00": 0, "01": 0, "10": 0, "11": 0}
    for label, count in raw_counts.items():
        normalized = str(label).replace(" ", "")
        if len(normalized) != 2 or any(bit not in "01" for bit in normalized):
            raise RuntimeError(f"Unexpected two-qubit measurement label: {label!r}")
        counts[normalized] += int(count)
    return counts


def _correlation(counts: dict[str, int], shots: int) -> float:
    return (
        counts["00"] + counts["11"] - counts["01"] - counts["10"]
    ) / shots


def _classify_bell_state(
    zz_correlation: float, xx_correlation: float, threshold: float
) -> BellState | None:
    for state, (expected_zz, expected_xx) in BELL_STATE_CORRELATIONS.items():
        if expected_zz * zz_correlation >= threshold and expected_xx * xx_correlation >= threshold:
            return state
    return None


def _bell_pair_diagnostic_result(
    *,
    metadata: QuantumExecutionMetadata,
    shots: int,
    preparation: BellPreparation,
    correlation_threshold: float,
    z_counts: dict[str, int],
    x_counts: dict[str, int],
    state_metrics: dict[str, float | None],
    state_metric_note: str,
    noise: NoiseConfig | None = None,
) -> dict[str, Any]:
    if not 128 <= shots <= 65_536:
        raise ValueError("Bell-pair diagnostic shots must be between 128 and 65536")
    if not 0.5 < correlation_threshold <= 1.0:
        raise ValueError("Bell-pair correlation threshold must be greater than 0.5 and at most 1")
    z_counts = _normalized_two_qubit_counts(z_counts)
    x_counts = _normalized_two_qubit_counts(x_counts)
    if sum(z_counts.values()) != shots or sum(x_counts.values()) != shots:
        raise RuntimeError("Bell-pair diagnostic count total does not match requested shots")
    zz = _correlation(z_counts, shots)
    xx = _correlation(x_counts, shots)
    observed_state = _classify_bell_state(zz, xx, correlation_threshold)
    expected_state = preparation if preparation in BELL_STATE_CORRELATIONS else None
    matches_expected = observed_state is not None and observed_state == expected_state
    verified = bool(matches_expected)
    if matches_expected:
        reason = (
            f"Strong Z- and X-basis correlations are consistent with the expected "
            f"{expected_state} Bell state."
        )
    elif observed_state is not None:
        reason = (
            f"Observed correlations classify as {observed_state}, not the configured "
            f"{expected_state or 'non-Bell control'} preparation."
        )
    else:
        reason = (
            "The preparation did not satisfy any standard Bell state's independent "
            "Z- and X-basis correlation signature."
        )
    return {
        "diagnostic_scope": "EFFECTIVE_BELL_DISTRIBUTION" if noise is not None else "IDEAL_SOURCE_PREPARATION",
        "engine": metadata.model_dump(),
        "alice_qubit": "q1",
        "bob_qubit": "q2",
        "expected_state": expected_state,
        "preparation": preparation,
        "observed_state": observed_state,
        "matches_expected": matches_expected,
        "classification": observed_state or "UNCLASSIFIED",
        "shots": shots,
        "total_diagnostic_shots": shots * 2,
        "z_basis": {
            **z_counts,
            "correlation": zz,
        },
        "x_basis": {
            **x_counts,
            "correlation": xx,
        },
        "state_metrics": state_metrics,
        "state_metric_note": state_metric_note,
        "methods": ["Z_CORRELATION", "X_CORRELATION"]
        + (["STATEVECTOR_METRICS"] if any(v is not None for v in state_metrics.values()) else []),
        "correlation_threshold": correlation_threshold,
        "entangled": observed_state is not None,
        "verified": verified,
        "status": "ENTANGLEMENT_VERIFIED" if verified else "ENTANGLEMENT_NOT_VERIFIED",
        "bell_preparation_status": "EXPECTED" if verified else "ANOMALOUS",
        "anomaly": None if verified else "UNEXPECTED_BELL_STATE_BEHAVIOUR",
        "confidence": "HIGH" if verified and shots >= 1024 else "NOT_VERIFIED" if not verified else "MODERATE",
        "reason": reason,
        "noise": (noise.model_dump() if noise is not None else NoiseConfig().model_dump()),
        "noise_semantics": (noise.semantics() if noise is not None else NoiseConfig().semantics()),
        "post_distribution_stages_included": False,
        "non_destructive": True,
        "production_pair_measured": False,
    }


def _bell_statevector(preparation: BellPreparation) -> np.ndarray:
    state = np.array([1, 0, 0, 0], dtype=complex)
    if preparation in BELL_STATE_CORRELATIONS or preparation == "BROKEN_NO_CNOT":
        state = _apply_single(state, H, 0, 2)
    if preparation in BELL_STATE_CORRELATIONS:
        state = _apply_cnot(state, 0, 1, 2)
    if preparation in {"PSI_PLUS", "PSI_MINUS"}:
        state = _apply_single(state, X, 1, 2)
    if preparation in {"PHI_MINUS", "PSI_MINUS"}:
        state = _apply_single(state, Z, 1, 2)
    return state


def _sample_two_qubit_state(
    state: np.ndarray, basis: Basis, shots: int, rng: random.Random
) -> dict[str, int]:
    measured_state = state.copy()
    if basis == "X":
        measured_state = _apply_single(measured_state, H, 0, 2)
        measured_state = _apply_single(measured_state, H, 1, 2)
    probabilities = np.abs(measured_state) ** 2
    samples = rng.choices(range(4), weights=probabilities.tolist(), k=shots)
    counts = {"00": 0, "01": 0, "10": 0, "11": 0}
    for sample in samples:
        counts[f"{sample:02b}"] += 1
    return counts


def _bell_distribution_noise_histogram(
    noise: NoiseConfig, rng: random.Random, shots: int
) -> dict[Pauli, int]:
    histogram: dict[Pauli, int] = {"I": 0, "X": 0, "Y": 0, "Z": 0}
    for _ in range(shots):
        operation = _sample_pauli_noise(
            rng,
            bit_flip=noise.bit_flip,
            phase_flip=noise.phase_flip,
            depolarizing=noise.depolarizing,
        )
        histogram[operation] += 1
    return histogram


def _add_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for label, count in source.items():
        target[label] = target.get(label, 0) + int(count)


def _pure_two_qubit_metrics(
    state: np.ndarray, fidelity_reference: BellState = PRODUCTION_BELL_STATE
) -> dict[str, float]:
    matrix = state.reshape(2, 2)
    rho_a = matrix @ matrix.conj().T
    eigenvalues = np.linalg.eigvalsh(rho_a).real
    eigenvalues = np.clip(eigenvalues, 0.0, 1.0)
    nonzero = eigenvalues[eigenvalues > 1e-15]
    entropy = float(-np.sum(nonzero * np.log2(nonzero)))
    purity = float(np.real(np.trace(rho_a @ rho_a)))
    concurrence = float(2 * abs(state[0] * state[3] - state[1] * state[2]))
    expected_bell_state = _bell_statevector(fidelity_reference)
    fidelity = float(abs(np.vdot(expected_bell_state, state)) ** 2)
    return {
        "reduced_alice_purity": purity,
        "entanglement_entropy_bits": entropy,
        "concurrence": concurrence,
        "bell_state_fidelity": fidelity,
    }


def _apply_single(state: np.ndarray, gate: np.ndarray, qubit: int, width: int) -> np.ndarray:
    operator = np.array([[1]], dtype=complex)
    for index in range(width):
        operator = np.kron(operator, gate if index == qubit else I2)
    return operator @ state


def _apply_cnot(state: np.ndarray, control: int, target: int, width: int) -> np.ndarray:
    result = np.zeros_like(state)
    for index, amplitude in enumerate(state):
        bits = [((index >> (width - 1 - q)) & 1) for q in range(width)]
        if bits[control]:
            bits[target] ^= 1
        mapped = 0
        for value in bits:
            mapped = (mapped << 1) | value
        result[mapped] += amplitude
    return result


def _measure(
    state: np.ndarray, qubit: int, width: int, rng: random.Random
) -> tuple[int, np.ndarray]:
    probabilities = [0.0, 0.0]
    for index, amplitude in enumerate(state):
        bit = (index >> (width - 1 - qubit)) & 1
        probabilities[bit] += float(abs(amplitude) ** 2)
    outcome = 1 if rng.random() < probabilities[1] else 0
    collapsed = state.copy()
    for index in range(len(collapsed)):
        bit = (index >> (width - 1 - qubit)) & 1
        if bit != outcome:
            collapsed[index] = 0
    norm = np.linalg.norm(collapsed)
    if norm:
        collapsed /= norm
    return outcome, collapsed


def _reduced_qubit_state(state: np.ndarray, qubit: int, width: int) -> np.ndarray:
    tensor = state.reshape([2] * width)
    moved = np.moveaxis(tensor, qubit, 0).reshape(2, -1)
    density = moved @ moved.conj().T
    values, vectors = np.linalg.eigh(density)
    vector = vectors[:, int(np.argmax(values))]
    pivot = int(np.argmax(np.abs(vector)))
    phase = np.angle(vector[pivot])
    return vector * np.exp(-1j * phase)


def _prepared_state(bit: int, basis: Basis) -> np.ndarray:
    state = np.array([1, 0], dtype=complex) if bit == 0 else np.array([0, 1], dtype=complex)
    return H @ state if basis == "X" else state


class ReferenceStatevectorEngine(QuantumEngine):
    """Explicit development backend; never presented as CUDA-Q."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(derive_simulation_seed(seed, "REFERENCE_MEASUREMENT"))
        self.noise_rng = random.Random(derive_simulation_seed(seed, "CANONICAL_NOISE"))

    @property
    def metadata(self) -> QuantumExecutionMetadata:
        return QuantumExecutionMetadata(
            engine="REFERENCE_STATEVECTOR",
            target="numpy-cpu-explicit-development",
            gpu=False,
            fallback_used=False,
            fallback_reason=None,
        )

    def diagnose_bell_pair(
        self,
        *,
        shots: int = 2048,
        preparation: BellPreparation = "PHI_PLUS",
        correlation_threshold: float = 0.90,
        noise: NoiseConfig | None = None,
    ) -> dict[str, Any]:
        state = _bell_statevector(preparation)
        if noise is None:
            z_counts = _sample_two_qubit_state(state, "Z", shots, self.rng)
            x_counts = _sample_two_qubit_state(state, "X", shots, self.rng)
            metrics: dict[str, float | None] = _pure_two_qubit_metrics(
                state,
                preparation if preparation in BELL_STATE_CORRELATIONS else PRODUCTION_BELL_STATE,
            )
            metric_note = "Calculated analytically from the reference engine's two-qubit statevector."
        else:
            z_counts = {"00": 0, "01": 0, "10": 0, "11": 0}
            x_counts = {"00": 0, "01": 0, "10": 0, "11": 0}
            identity_total = 0
            for basis, destination in (("Z", z_counts), ("X", x_counts)):
                histogram = _bell_distribution_noise_histogram(noise, self.noise_rng, shots)
                identity_total += histogram["I"]
                for operation, count in histogram.items():
                    if count:
                        noisy_state = _apply_single(state, PAULI[operation], 1, 2)
                        _add_counts(
                            destination,
                            _sample_two_qubit_state(noisy_state, basis, count, self.rng),
                        )
            metrics = {
                "reduced_alice_purity": None,
                "entanglement_entropy_bits": None,
                "concurrence": None,
                "bell_state_fidelity": identity_total / (2 * shots),
            }
            metric_note = (
                "Bell fidelity is the empirical fraction of sampled composed distribution "
                "Paulis equal to identity. Pure-state entanglement metrics are intentionally "
                "omitted for the resulting mixed ensemble."
            )
        return _bell_pair_diagnostic_result(
            metadata=self.metadata,
            shots=shots,
            preparation=preparation,
            correlation_threshold=correlation_threshold,
            z_counts=z_counts,
            x_counts=x_counts,
            state_metrics=metrics,
            state_metric_note=metric_note,
            noise=noise,
        )

    def _measure_single(self, state: np.ndarray, basis: Basis) -> tuple[int, np.ndarray]:
        working = H @ state if basis == "X" else state.copy()
        probability_one = float(abs(working[1]) ** 2)
        outcome = 1 if self.rng.random() < probability_one else 0
        collapsed = np.array([1, 0], dtype=complex) if outcome == 0 else np.array([0, 1], dtype=complex)
        if basis == "X":
            collapsed = H @ collapsed
        return outcome, collapsed

    def teleport_and_measure(
        self,
        *,
        bit: int,
        preparation_basis: Basis,
        measurement_basis: Basis,
        intercept: bool = False,
        eve_basis: Basis = "Z",
        entanglement_pauli: Pauli = "I",
        correction_flip_mask: int = 0,
        output_pauli: Pauli = "I",
        noise: NoiseConfig | None = None,
    ) -> TransmissionResult:
        pending = self.begin_networked_teleportation(
            bit=bit,
            preparation_basis=preparation_basis,
            measurement_basis=measurement_basis,
            intercept=intercept,
            eve_basis=eve_basis,
            entanglement_pauli=entanglement_pauli,
            output_pauli=output_pauli,
            noise=noise,
        )
        delivered = (
            pending.bell_bits[0] ^ ((correction_flip_mask >> 1) & 1),
            pending.bell_bits[1] ^ (correction_flip_mask & 1),
        )
        return self.complete_networked_teleportation(
            pending, delivered_bell_bits=delivered
        )

    def begin_networked_teleportation(
        self,
        *,
        bit: int,
        preparation_basis: Basis,
        measurement_basis: Basis,
        intercept: bool = False,
        eve_basis: Basis = "Z",
        entanglement_pauli: Pauli = "I",
        output_pauli: Pauli = "I",
        noise: NoiseConfig | None = None,
    ) -> PendingTeleportation:
        input_state = _prepared_state(bit, preparation_basis)

        channel_noise = noise or NoiseConfig()
        distribution_noise, output_noise, measurement_flip = _sample_noise_events(
            channel_noise, self.noise_rng
        )

        state = np.kron(np.kron(input_state, np.array([1, 0], complex)), np.array([1, 0], complex))
        state = _apply_single(state, H, 1, 3)
        state = _apply_cnot(state, 1, 2, 3)
        state = _apply_single(state, PAULI[distribution_noise], 2, 3)
        state = _apply_single(state, PAULI[entanglement_pauli], 2, 3)
        # Eve can only intercept the Bob-bound Bell half (q2) while it is in the
        # distribution channel.  q0 is Alice's local message qubit and is not a
        # scientifically valid channel-intercept location.
        if intercept:
            if eve_basis == "X":
                state = _apply_single(state, H, 2, 3)
            _, state = _measure(state, 2, 3, self.rng)
            if eve_basis == "X":
                state = _apply_single(state, H, 2, 3)
        state = _apply_cnot(state, 0, 1, 3)
        state = _apply_single(state, H, 0, 3)
        bell0, state = _measure(state, 0, 3, self.rng)
        bell1, state = _measure(state, 1, 3, self.rng)

        return PendingTeleportation(
            bell_bits=(bell0, bell1),
            input_state=tuple(input_state.tolist()),
            measurement_basis=measurement_basis,
            context={
                "state": state,
                "output_pauli": output_pauli,
                "output_noise": output_noise,
                "measurement_flip": measurement_flip,
            },
        )

    def complete_networked_teleportation(
        self,
        pending: PendingTeleportation,
        *,
        delivered_bell_bits: tuple[int, int],
    ) -> TransmissionResult:
        if any(bit not in {0, 1} for bit in delivered_bell_bits):
            raise ValueError("delivered Bell correction bits must be binary")
        state = pending.context["state"].copy()
        used0, used1 = delivered_bell_bits
        if used1:
            state = _apply_single(state, X, 2, 3)
        if used0:
            state = _apply_single(state, Z, 2, 3)
        state = _apply_single(state, PAULI[pending.context["output_pauli"]], 2, 3)
        state = _apply_single(state, PAULI[pending.context["output_noise"]], 2, 3)

        input_state = np.asarray(pending.input_state, dtype=complex)
        output_state = _reduced_qubit_state(state, 2, 3)
        fidelity = float(abs(np.vdot(input_state, output_state)) ** 2)
        if pending.measurement_basis == "X":
            state = _apply_single(state, H, 2, 3)
        bob_outcome, _ = _measure(state, 2, 3, self.rng)
        if pending.context["measurement_flip"]:
            bob_outcome ^= 1
        return TransmissionResult(
            bob_outcome=bob_outcome,
            bell_bits=pending.bell_bits,
            input_state=tuple(input_state.tolist()),
            output_state=tuple(output_state.tolist()),
            fidelity=max(0.0, min(1.0, fidelity)),
        )


class CudaQEngine(QuantumEngine):
    def __init__(self, seed: int | None = None):
        global _CUDAQ_CONFIGURED_TARGET
        try:
            import cudaq  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "CUDA-Q was explicitly selected but is not installed. "
                "Install CUDA-Q in WSL2/Linux or explicitly select the reference engine for development."
            ) from exc
        self.cudaq = cudaq
        self.rng = random.Random(derive_simulation_seed(seed, "CUDAQ_MEASUREMENT"))
        self.noise_rng = random.Random(derive_simulation_seed(seed, "CANONICAL_NOISE"))
        self._master_seed = 0 if seed is None else seed
        self._execution_counter = 0
        from .config import settings
        requested = (settings.cudaq_target, settings.cudaq_target_option)
        fallback_used = False
        fallback_reason = None
        with _CUDAQ_GLOBAL_LOCK:
            if _CUDAQ_CONFIGURED_TARGET is None:
                try:
                    if settings.cudaq_target != "auto":
                        if settings.cudaq_target_option:
                            cudaq.set_target(settings.cudaq_target, option=settings.cudaq_target_option)
                        else:
                            cudaq.set_target(settings.cudaq_target)
                except Exception as exc:
                    if not (
                        settings.allow_cudaq_cpu_fallback
                        and settings.cudaq_target == "nvidia"
                    ):
                        raise RuntimeError(
                            "The requested CUDA-Q target could not be initialized."
                        ) from exc
                    cudaq.set_target("qpp-cpu")
                    fallback_used = True
                    fallback_reason = "CUDA_Q_GPU_TARGET_UNAVAILABLE"
                target = cudaq.get_target()
                target_name = str(target.name)
                _CUDAQ_CONFIGURED_TARGET = requested
            else:
                if requested != _CUDAQ_CONFIGURED_TARGET:
                    raise RuntimeError(
                        "CUDA-Q target is process-global and was already initialized with a different configuration."
                    )
                target_name = str(cudaq.get_target().name)
            if settings.cudaq_target == "nvidia" and "nvidia" not in target_name.lower():
                fallback_used = True
                fallback_reason = "CUDA_Q_GPU_TARGET_UNAVAILABLE"
        try:
            available_gpus = int(cudaq.num_available_gpus())
        except Exception:
            # Some CPU-only CUDA-Q installations do not expose the GPU query.
            # Target selection remains the authoritative execution-backend signal.
            available_gpus = 0
        self._metadata = QuantumExecutionMetadata(
            engine="CUDA-Q",
            target=target_name,
            gpu="nvidia" in target_name.lower(),
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            available_gpus=available_gpus,
        )
        self._kernel = self._build_kernel()
        self._network_bell_stage_kernel = self._build_network_bell_stage_kernel()
        self._network_recovery_kernel = self._build_network_recovery_kernel()
        self._bell_diagnostic_kernel = self._build_bell_diagnostic_kernel()

    def _next_execution_seed(self, domain: str) -> int:
        self._execution_counter += 1
        return derive_simulation_seed(
            self._master_seed, f"CUDAQ_EXECUTION|{domain}|{self._execution_counter}"
        )

    @property
    def metadata(self) -> QuantumExecutionMetadata:
        return self._metadata

    def _build_kernel(self):
        cudaq = self.cudaq

        @cudaq.kernel
        def kernel(
            bit: int,
            prep_x: int,
            measure_x: int,
            intercept: int,
            eve_x: int,
            distribution_noise_pauli: int,
            entanglement_pauli: int,
            correction_flip_mask: int,
            output_pauli: int,
            output_noise_pauli: int,
            measurement_flip: int,
        ) -> list[bool]:
            q = cudaq.qvector(3)
            if bit == 1:
                x(q[0])
            if prep_x == 1:
                h(q[0])
            h(q[1])
            x.ctrl(q[1], q[2])
            if distribution_noise_pauli == 1:
                x(q[2])
            if distribution_noise_pauli == 2:
                y(q[2])
            if distribution_noise_pauli == 3:
                z(q[2])
            if entanglement_pauli == 1:
                x(q[2])
            if entanglement_pauli == 2:
                y(q[2])
            if entanglement_pauli == 3:
                z(q[2])
            # Intercept-resend acts on the Bob-bound half of the Bell pair,
            # after creation/distribution and before Alice's Bell measurement.
            if intercept == 1:
                if eve_x == 1:
                    h(q[2])
                eve_result = mz(q[2])
                reset(q[2])
                if eve_result:
                    x(q[2])
                if eve_x == 1:
                    h(q[2])
            x.ctrl(q[0], q[1])
            h(q[0])
            m0 = mz(q[0])
            m1 = mz(q[1])
            if m1:
                x(q[2])
            if m0:
                z(q[2])
            if correction_flip_mask == 1:
                x(q[2])
            if correction_flip_mask == 2:
                z(q[2])
            if correction_flip_mask == 3:
                x(q[2])
                z(q[2])
            if output_pauli == 1:
                x(q[2])
            if output_pauli == 2:
                y(q[2])
            if output_pauli == 3:
                z(q[2])
            if output_noise_pauli == 1:
                x(q[2])
            if output_noise_pauli == 2:
                y(q[2])
            if output_noise_pauli == 3:
                z(q[2])
            if measure_x == 1:
                h(q[2])
            if measurement_flip == 1:
                x(q[2])
            result = mz(q[2])
            return [m0, m1, result]

        return kernel

    def _build_network_bell_stage_kernel(self):
        cudaq = self.cudaq

        @cudaq.kernel
        def bell_stage(
            bit: int,
            prep_x: int,
            distribution_noise_pauli: int,
            entanglement_pauli: int,
        ) -> list[bool]:
            q = cudaq.qvector(3)
            if bit == 1:
                x(q[0])
            if prep_x == 1:
                h(q[0])
            h(q[1])
            x.ctrl(q[1], q[2])
            if distribution_noise_pauli == 1:
                x(q[2])
            if distribution_noise_pauli == 2:
                y(q[2])
            if distribution_noise_pauli == 3:
                z(q[2])
            if entanglement_pauli == 1:
                x(q[2])
            if entanglement_pauli == 2:
                y(q[2])
            if entanglement_pauli == 3:
                z(q[2])
            x.ctrl(q[0], q[1])
            h(q[0])
            m0 = mz(q[0])
            m1 = mz(q[1])
            return [m0, m1]

        return bell_stage

    def _build_network_recovery_kernel(self):
        cudaq = self.cudaq

        @cudaq.kernel
        def recovery_stage(
            bit: int,
            prep_x: int,
            measure_x: int,
            source_m0: int,
            source_m1: int,
            delivered_m0: int,
            delivered_m1: int,
            distribution_noise_pauli: int,
            entanglement_pauli: int,
            output_pauli: int,
            output_noise_pauli: int,
            measurement_flip: int,
        ) -> bool:
            receiver = cudaq.qubit()
            if bit == 1:
                x(receiver)
            if prep_x == 1:
                h(receiver)
            # Reconstruct the exact conditional Bob state left by the Bell
            # measurement. CUDA-Q 0.15 cannot keep that q2 allocation alive
            # while the Python SeQUeNCe event loop runs.
            if source_m0 == 1:
                z(receiver)
            if source_m1 == 1:
                x(receiver)
            if distribution_noise_pauli == 1:
                x(receiver)
            if distribution_noise_pauli == 2:
                y(receiver)
            if distribution_noise_pauli == 3:
                z(receiver)
            if entanglement_pauli == 1:
                x(receiver)
            if entanglement_pauli == 2:
                y(receiver)
            if entanglement_pauli == 3:
                z(receiver)
            # Only the control bits delivered by SeQUeNCe drive correction.
            if delivered_m1 == 1:
                x(receiver)
            if delivered_m0 == 1:
                z(receiver)
            if output_pauli == 1:
                x(receiver)
            if output_pauli == 2:
                y(receiver)
            if output_pauli == 3:
                z(receiver)
            if output_noise_pauli == 1:
                x(receiver)
            if output_noise_pauli == 2:
                y(receiver)
            if output_noise_pauli == 3:
                z(receiver)
            if measure_x == 1:
                h(receiver)
            if measurement_flip == 1:
                x(receiver)
            return mz(receiver)

        return recovery_stage

    def _build_bell_diagnostic_kernel(self):
        cudaq = self.cudaq

        @cudaq.kernel
        def bell_diagnostic(measure_x: int, preparation_mode: int, distribution_pauli: int):
            pair = cudaq.qvector(2)
            if preparation_mode == 1:
                h(pair[0])
            if preparation_mode >= 2:
                h(pair[0])
                x.ctrl(pair[0], pair[1])
            if preparation_mode == 4 or preparation_mode == 5:
                x(pair[1])
            if preparation_mode == 3 or preparation_mode == 5:
                z(pair[1])
            if distribution_pauli == 1:
                x(pair[1])
            if distribution_pauli == 2:
                y(pair[1])
            if distribution_pauli == 3:
                z(pair[1])
            if measure_x == 1:
                h(pair[0])
                h(pair[1])
            mz(pair)

        return bell_diagnostic

    def diagnose_bell_pair(
        self,
        *,
        shots: int = 2048,
        preparation: BellPreparation = "PHI_PLUS",
        correlation_threshold: float = 0.90,
        noise: NoiseConfig | None = None,
    ) -> dict[str, Any]:
        mode = {
            "INDEPENDENT": 0,
            "BROKEN_NO_CNOT": 1,
            "PHI_PLUS": 2,
            "PHI_MINUS": 3,
            "PSI_PLUS": 4,
            "PSI_MINUS": 5,
        }[preparation]
        pauli_number = {"I": 0, "X": 1, "Y": 2, "Z": 3}
        z_counts: dict[str, int] = {"00": 0, "01": 0, "10": 0, "11": 0}
        x_counts: dict[str, int] = {"00": 0, "01": 0, "10": 0, "11": 0}
        identity_total = 0
        for measure_x, destination in ((0, z_counts), (1, x_counts)):
            histogram = (
                {"I": shots, "X": 0, "Y": 0, "Z": 0}
                if noise is None
                else _bell_distribution_noise_histogram(noise, self.noise_rng, shots)
            )
            identity_total += histogram["I"]
            for operation, count in histogram.items():
                if count:
                    with _CUDAQ_GLOBAL_LOCK:
                        self.cudaq.set_random_seed(
                            self._next_execution_seed(
                                f"BELL_DIAGNOSTIC|{measure_x}|{operation}"
                            )
                        )
                        sampled = self.cudaq.sample(
                            self._bell_diagnostic_kernel,
                            measure_x,
                            mode,
                            pauli_number[operation],
                            shots_count=count,
                        )
                    _add_counts(
                        destination,
                        {str(label): int(value) for label, value in sampled.items()},
                    )
        return _bell_pair_diagnostic_result(
            metadata=self.metadata,
            shots=shots,
            preparation=preparation,
            correlation_threshold=correlation_threshold,
            z_counts=z_counts,
            x_counts=x_counts,
            state_metrics={
                "reduced_alice_purity": None,
                "entanglement_entropy_bits": None,
                "concurrence": None,
                "bell_state_fidelity": None if noise is None else identity_total / (2 * shots),
            },
            state_metric_note=(
                "Direct state inspection was not used on the NVIDIA execution target; "
                "the decision uses independent Z- and X-basis CUDA-Q sampling runs. "
                "For effective-channel diagnostics, Bell fidelity is the empirical identity-Pauli fraction."
            ),
            noise=noise,
        )

    def begin_networked_teleportation(
        self,
        *,
        bit: int,
        preparation_basis: Basis,
        measurement_basis: Basis,
        intercept: bool = False,
        eve_basis: Basis = "Z",
        entanglement_pauli: Pauli = "I",
        output_pauli: Pauli = "I",
        noise: NoiseConfig | None = None,
    ) -> PendingTeleportation:
        if intercept:
            raise RuntimeError(
                "Staged network signing does not permit an undeclared intercept operation"
            )
        pauli_number = {"I": 0, "X": 1, "Y": 2, "Z": 3}
        channel_noise = noise or NoiseConfig()
        distribution_noise, output_noise, measurement_flip = _sample_noise_events(
            channel_noise, self.noise_rng
        )
        with _CUDAQ_GLOBAL_LOCK:
            self.cudaq.set_random_seed(self._next_execution_seed("NETWORK_BELL_STAGE"))
            results = self.cudaq.run(
                self._network_bell_stage_kernel,
                int(bit),
                int(preparation_basis == "X"),
                pauli_number[distribution_noise],
                pauli_number[entanglement_pauli],
                shots_count=1,
            )
        shot = results[0]
        input_state = _prepared_state(bit, preparation_basis)
        return PendingTeleportation(
            bell_bits=(int(bool(shot[0])), int(bool(shot[1]))),
            input_state=tuple(input_state.tolist()),
            measurement_basis=measurement_basis,
            context={
                "bit": bit,
                "preparation_basis": preparation_basis,
                "distribution_noise": distribution_noise,
                "entanglement_pauli": entanglement_pauli,
                "output_pauli": output_pauli,
                "output_noise": output_noise,
                "measurement_flip": measurement_flip,
                "continuity": "CONDITIONAL_RECEIVER_STATE_RECONSTRUCTION",
            },
        )

    def complete_networked_teleportation(
        self,
        pending: PendingTeleportation,
        *,
        delivered_bell_bits: tuple[int, int],
    ) -> TransmissionResult:
        if any(bit not in {0, 1} for bit in delivered_bell_bits):
            raise ValueError("delivered Bell correction bits must be binary")
        pauli_number = {"I": 0, "X": 1, "Y": 2, "Z": 3}
        context = pending.context
        with _CUDAQ_GLOBAL_LOCK:
            self.cudaq.set_random_seed(self._next_execution_seed("NETWORK_RECOVERY_STAGE"))
            results = self.cudaq.run(
                self._network_recovery_kernel,
                int(context["bit"]),
                int(context["preparation_basis"] == "X"),
                int(pending.measurement_basis == "X"),
                int(pending.bell_bits[0]),
                int(pending.bell_bits[1]),
                int(delivered_bell_bits[0]),
                int(delivered_bell_bits[1]),
                pauli_number[context["distribution_noise"]],
                pauli_number[context["entanglement_pauli"]],
                pauli_number[context["output_pauli"]],
                pauli_number[context["output_noise"]],
                int(context["measurement_flip"]),
                shots_count=1,
            )
        return TransmissionResult(
            bob_outcome=int(bool(results[0])),
            bell_bits=pending.bell_bits,
            input_state=pending.input_state,
            output_state=None,
            fidelity=None,
        )

    def teleport_and_measure(self, **kwargs) -> TransmissionResult:
        pauli_number = {"I": 0, "X": 1, "Y": 2, "Z": 3}
        noise = kwargs.get("noise") or NoiseConfig()
        distribution_noise, output_noise, measurement_flip = _sample_noise_events(
            noise, self.noise_rng
        )
        with _CUDAQ_GLOBAL_LOCK:
            self.cudaq.set_random_seed(self._next_execution_seed("TELEPORT_AND_MEASURE"))
            results = self.cudaq.run(
                self._kernel,
                int(kwargs["bit"]),
                int(kwargs["preparation_basis"] == "X"),
                int(kwargs["measurement_basis"] == "X"),
                int(kwargs.get("intercept", False)),
                int(kwargs.get("eve_basis", "Z") == "X"),
                pauli_number[distribution_noise],
                pauli_number[kwargs.get("entanglement_pauli", "I")],
                int(kwargs.get("correction_flip_mask", 0)),
                pauli_number[kwargs.get("output_pauli", "I")],
                pauli_number[output_noise],
                int(measurement_flip),
                shots_count=1,
            )
        shot = results[0]
        input_state = _prepared_state(kwargs["bit"], kwargs["preparation_basis"])
        return TransmissionResult(
            bob_outcome=int(bool(shot[2])),
            bell_bits=(int(bool(shot[0])), int(bool(shot[1]))),
            input_state=tuple(input_state.tolist()),
            output_state=None,
            fidelity=None,
        )


class QiskitAerEngine(QuantumEngine):
    """Independent circuit-level validator using Qiskit Aer."""

    def __init__(self, seed: int | None = None):
        try:
            from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
            from qiskit_aer import AerSimulator
        except ImportError as exc:
            raise RuntimeError(
                "Qiskit Aer was selected but qiskit and qiskit-aer are not installed."
            ) from exc
        self.QuantumCircuit = QuantumCircuit
        self.QuantumRegister = QuantumRegister
        self.ClassicalRegister = ClassicalRegister
        self.simulator = AerSimulator()
        self.seed = seed
        self.rng = random.Random(derive_simulation_seed(seed, "QISKIT_MEASUREMENT"))
        self.noise_rng = random.Random(derive_simulation_seed(seed, "CANONICAL_NOISE"))

    @property
    def metadata(self) -> QuantumExecutionMetadata:
        return QuantumExecutionMetadata(
            engine="QISKIT_AER",
            target="aer_simulator-cpu-independent-validator",
            gpu=False,
            fallback_used=False,
            fallback_reason=None,
        )

    def _bell_pair_circuit(
        self,
        preparation: BellPreparation,
        measure_basis: Basis | None = None,
        distribution_pauli: Pauli = "I",
    ):
        qc = self.QuantumCircuit(2, 2) if measure_basis is not None else self.QuantumCircuit(2)
        if preparation in BELL_STATE_CORRELATIONS or preparation == "BROKEN_NO_CNOT":
            qc.h(0)
        if preparation in BELL_STATE_CORRELATIONS:
            qc.cx(0, 1)
        if preparation in {"PSI_PLUS", "PSI_MINUS"}:
            qc.x(1)
        if preparation in {"PHI_MINUS", "PSI_MINUS"}:
            qc.z(1)
        self._gate(qc, distribution_pauli, 1)
        if measure_basis == "X":
            qc.h(0)
            qc.h(1)
        if measure_basis is not None:
            qc.measure(0, 0)
            qc.measure(1, 1)
        return qc

    def diagnose_bell_pair(
        self,
        *,
        shots: int = 2048,
        preparation: BellPreparation = "PHI_PLUS",
        correlation_threshold: float = 0.90,
        noise: NoiseConfig | None = None,
    ) -> dict[str, Any]:
        from qiskit.quantum_info import Statevector, concurrence, entropy, partial_trace, purity, state_fidelity

        z_counts: dict[str, int] = {"00": 0, "01": 0, "10": 0, "11": 0}
        x_counts: dict[str, int] = {"00": 0, "01": 0, "10": 0, "11": 0}
        identity_total = 0
        for basis, destination in (("Z", z_counts), ("X", x_counts)):
            histogram = (
                {"I": shots, "X": 0, "Y": 0, "Z": 0}
                if noise is None
                else _bell_distribution_noise_histogram(noise, self.noise_rng, shots)
            )
            identity_total += histogram["I"]
            for operation, count in histogram.items():
                if count:
                    sampled = self.simulator.run(
                        self._bell_pair_circuit(preparation, basis, operation),
                        shots=count,
                        seed_simulator=self.rng.randrange(2**31),
                    ).result().get_counts()
                    _add_counts(destination, dict(sampled))
        state = Statevector.from_instruction(self._bell_pair_circuit(preparation))
        rho_a = partial_trace(state, [1])
        fidelity_reference = (
            preparation if preparation in BELL_STATE_CORRELATIONS else PRODUCTION_BELL_STATE
        )
        expected = Statevector(_bell_statevector(fidelity_reference))
        metrics = (
            {
                "reduced_alice_purity": float(np.real(purity(rho_a))),
                "entanglement_entropy_bits": float(np.real(entropy(rho_a, base=2))),
                "concurrence": float(np.real(concurrence(state))),
                "bell_state_fidelity": float(np.real(state_fidelity(state, expected))),
            }
            if noise is None
            else {
                "reduced_alice_purity": None,
                "entanglement_entropy_bits": None,
                "concurrence": None,
                "bell_state_fidelity": identity_total / (2 * shots),
            }
        )
        return _bell_pair_diagnostic_result(
            metadata=self.metadata,
            shots=shots,
            preparation=preparation,
            correlation_threshold=correlation_threshold,
            z_counts=dict(z_counts),
            x_counts=dict(x_counts),
            state_metrics=metrics,
            state_metric_note=(
                "Calculated from Qiskit Aer circuit statevector before measurement."
                if noise is None else
                "Effective mixed ensemble sampled in Qiskit Aer; Bell fidelity is the empirical identity-Pauli fraction."
            ),
            noise=noise,
        )

    @staticmethod
    def _gate(qc, operation: Pauli, qubit) -> None:
        if operation == "X":
            qc.x(qubit)
        elif operation == "Y":
            qc.y(qubit)
        elif operation == "Z":
            qc.z(qubit)

    def _measured_preparation(self, bit: int, basis: Basis, eve_basis: Basis) -> int:
        qc = self.QuantumCircuit(1, 1)
        if bit:
            qc.x(0)
        if basis == "X":
            qc.h(0)
        if eve_basis == "X":
            qc.h(0)
        qc.measure(0, 0)
        counts = self.simulator.run(qc, shots=1, seed_simulator=self.rng.randrange(2**31)).result().get_counts()
        return int(next(iter(counts)))

    def teleport_and_measure(
        self,
        *,
        bit: int,
        preparation_basis: Basis,
        measurement_basis: Basis,
        intercept: bool = False,
        eve_basis: Basis = "Z",
        entanglement_pauli: Pauli = "I",
        correction_flip_mask: int = 0,
        output_pauli: Pauli = "I",
        noise: NoiseConfig | None = None,
    ) -> TransmissionResult:
        channel_noise = noise or NoiseConfig()
        distribution_noise, output_noise, measurement_flip = _sample_noise_events(
            channel_noise, self.noise_rng
        )

        q = self.QuantumRegister(3, "q")
        # c[3] is reserved for Eve's measurement so the attack is represented
        # inside the same dynamic circuit as Bell-pair distribution.
        c = self.ClassicalRegister(4, "c")
        qc = self.QuantumCircuit(q, c)
        if bit:
            qc.x(q[0])
        if preparation_basis == "X":
            qc.h(q[0])
        qc.h(q[1])
        qc.cx(q[1], q[2])
        self._gate(qc, distribution_noise, q[2])
        self._gate(qc, entanglement_pauli, q[2])
        if intercept:
            if eve_basis == "X":
                qc.h(q[2])
            qc.measure(q[2], c[3])
            qc.reset(q[2])
            with qc.if_test((c[3], 1)):
                qc.x(q[2])
            if eve_basis == "X":
                qc.h(q[2])
        qc.cx(q[0], q[1])
        qc.h(q[0])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])
        with qc.if_test((c[1], 1)):
            qc.x(q[2])
        with qc.if_test((c[0], 1)):
            qc.z(q[2])
        if correction_flip_mask & 1:
            qc.x(q[2])
        if correction_flip_mask & 2:
            qc.z(q[2])
        self._gate(qc, output_pauli, q[2])
        self._gate(qc, output_noise, q[2])
        if measurement_basis == "X":
            qc.h(q[2])
        qc.measure(q[2], c[2])
        counts = self.simulator.run(
            qc, shots=1, seed_simulator=self.rng.randrange(2**31)
        ).result().get_counts()
        bits = next(iter(counts)).replace(" ", "")
        # Qiskit renders classical strings in descending bit order: c3 c2 c1 c0.
        bob = int(bits[1])
        if measurement_flip:
            bob ^= 1
        input_state = _prepared_state(bit, preparation_basis)
        return TransmissionResult(
            bob_outcome=bob,
            bell_bits=(int(bits[3]), int(bits[2])),
            input_state=tuple(input_state.tolist()),
            output_state=None,
            fidelity=None,
        )


def run_channel_diagnostic(
    engine: QuantumEngine,
    *,
    shots_per_basis: int = 256,
    master_seed: int = 2026,
    attack_strength: float = 0.0,
    output_pauli: Pauli = "I",
    entanglement_pauli: Pauli = "I",
    intercept: bool = False,
    correction_flip_mask: int = 0,
    noise: NoiseConfig | None = None,
    disturbance_threshold: float = 0.05,
) -> dict[str, Any]:
    """Measure dedicated, known Z/X control states independently of QDS evidence.

    This is an empirical channel diagnostic, not a QDS security proof.  Each call
    consumes fresh simulated Bell pairs and never reads or mutates stored signature
    measurements.
    """
    if not 32 <= shots_per_basis <= 16_384:
        raise ValueError("shots_per_basis must be between 32 and 16384")
    if not 0.0 <= attack_strength <= 1.0:
        raise ValueError("attack_strength must be between 0 and 1")
    if not 0.0 <= disturbance_threshold <= 1.0:
        raise ValueError("disturbance_threshold must be between 0 and 1")
    selection_rng = random.Random(
        derive_simulation_seed(master_seed, "CHANNEL_DIAGNOSTIC_ATTACK_SELECTION")
    )
    metrics: dict[str, dict[str, int | float]] = {}
    total_errors = 0
    fidelity_samples: list[float] = []
    for basis in ("Z", "X"):
        errors = 0
        attacked = 0
        for shot_index in range(shots_per_basis):
            bit = shot_index & 1
            selected = selection_rng.random() < attack_strength
            attacked += int(selected)
            result = engine.teleport_and_measure(
                bit=bit,
                preparation_basis=basis,
                measurement_basis=basis,
                intercept=selected and intercept,
                eve_basis="X" if selection_rng.getrandbits(1) else "Z",
                entanglement_pauli=entanglement_pauli if selected else "I",
                correction_flip_mask=correction_flip_mask if selected else 0,
                output_pauli=output_pauli if selected else "I",
                noise=noise,
            )
            errors += int(result.bob_outcome != bit)
            if result.fidelity is not None:
                fidelity_samples.append(result.fidelity)
        total_errors += errors
        metrics[basis] = {
            "shots": shots_per_basis,
            "errors": errors,
            "error_rate": errors / shots_per_basis,
            "attacked_states": attacked,
        }
    combined_rate = total_errors / (2 * shots_per_basis)
    phase_sensitive = float(metrics["X"]["error_rate"])
    bit_sensitive = float(metrics["Z"]["error_rate"])
    detected = max(phase_sensitive, bit_sensitive) > disturbance_threshold
    return {
        "type": "DEDICATED_RANDOMIZED_BASIS_CHANNEL_DIAGNOSTIC",
        "claim_scope": "EMPIRICAL_CHANNEL_DISTURBANCE_ONLY",
        "production_signature_evidence_used": False,
        "production_signature_evidence_modified": False,
        "fresh_bell_pairs_consumed": shots_per_basis * 2,
        "bases": metrics,
        "z_basis_error_rate": bit_sensitive,
        "x_basis_error_rate": phase_sensitive,
        "combined_channel_disturbance": combined_rate,
        "mean_teleportation_fidelity": (
            sum(fidelity_samples) / len(fidelity_samples) if fidelity_samples else None
        ),
        "disturbance_threshold": disturbance_threshold,
        "decision": "CHANNEL_DISTURBANCE_DETECTED" if detected else "NO_CHANNEL_DISTURBANCE_DETECTED",
        "engine": engine.metadata.model_dump(),
        "noise": (noise or NoiseConfig()).model_dump(),
        "noise_semantics": (noise or NoiseConfig()).semantics(),
        "limitations": (
            "The diagnostic reveals disturbances observable in prepared Z/X eigenstates; "
            "it is not an information-theoretic QDS security proof."
        ),
    }


def validate_qiskit_aer(*, shots: int = 512, seed: int = 2026) -> dict:
    """Validate computational-basis teleportation using independent Aer circuits."""
    if not 32 <= shots <= 16_384:
        raise ValueError("shots must be between 32 and 16384")
    ideal = QiskitAerEngine(seed)
    ideal_errors = 0
    attacked = QiskitAerEngine(seed + 1)
    attack_errors = 0
    noisy = QiskitAerEngine(seed + 2)
    noise_errors = 0
    for index in range(shots):
        bit = index & 1
        ideal_result = ideal.teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z"
        )
        ideal_errors += int(ideal_result.bob_outcome != bit)
        attacked_result = attacked.teleport_and_measure(
            bit=bit,
            preparation_basis="Z",
            measurement_basis="Z",
            intercept=True,
            eve_basis="X" if attacked.rng.getrandbits(1) else "Z",
        )
        attack_errors += int(attacked_result.bob_outcome != bit)
        noisy_result = noisy.teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z",
            noise=NoiseConfig(measurement_error=0.15),
        )
        noise_errors += int(noisy_result.bob_outcome != bit)

    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector, state_fidelity

    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell_state = Statevector.from_instruction(bell)
    expected_bell = np.array([1, 0, 0, 1], dtype=complex) / math.sqrt(2)
    bell_fidelity = float(state_fidelity(bell_state, expected_bell))
    measured_bell = bell.copy()
    measured_bell.measure_all()
    bell_counts = ideal.simulator.run(
        measured_bell, shots=shots, seed_simulator=seed
    ).result().get_counts()
    bell_correlated = sum(count for label, count in bell_counts.items() if label in {"00", "11"})
    return {
        "validator": ideal.metadata.model_dump(),
        "shots_per_scenario": shots,
        "ideal": {"errors": ideal_errors, "qber": ideal_errors / shots},
        "intercept_resend": {"errors": attack_errors, "qber": attack_errors / shots},
        "measurement_noise": {
            "configured_probability": 0.15,
            "errors": noise_errors,
            "observed_error_rate": noise_errors / shots,
        },
        "bell_state": {
            "counts": dict(bell_counts),
            "correlation_rate": bell_correlated / shots,
            "state_fidelity": bell_fidelity,
        },
        "expectations": {
            "ideal_qber_max": 0.02,
            "random_basis_intercept_resend_qber_expected": 0.25,
            "intercept_resend_tolerance": 0.10,
        },
        "passed": ideal_errors / shots <= 0.02
        and abs(attack_errors / shots - 0.25) <= 0.10,
    }


def cross_validate_quantum_engines(
    *, primary_engine_name: str, shots: int = 512, seed: int = 2026,
    tolerance: float = 0.12,
) -> dict:
    """Compare sampled teleportation/QBER outcomes from the selected engine and Aer."""
    primary = create_quantum_engine(primary_engine_name, seed)
    aer_report = validate_qiskit_aer(shots=shots, seed=seed + 1000)
    rng = random.Random(seed + 2000)
    ideal_errors = 0
    attack_errors = 0
    for index in range(shots):
        bit = index & 1
        ideal_errors += int(primary.teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z"
        ).bob_outcome != bit)
        attack_errors += int(primary.teleport_and_measure(
            bit=bit, preparation_basis="Z", measurement_basis="Z",
            intercept=True, eve_basis="X" if rng.getrandbits(1) else "Z",
        ).bob_outcome != bit)
    primary_ideal = ideal_errors / shots
    primary_attack = attack_errors / shots
    differences = {
        "ideal_qber": abs(primary_ideal - aer_report["ideal"]["qber"]),
        "intercept_resend_qber": abs(primary_attack - aer_report["intercept_resend"]["qber"]),
    }
    within_tolerance = max(differences.values()) <= tolerance
    overall_passed = bool(aer_report["passed"] and within_tolerance)
    return {
        **aer_report,
        "passed": overall_passed,
        "comparison": {
            "primary": primary.metadata.model_dump(),
            "primary_results": {
                "ideal_qber": primary_ideal,
                "intercept_resend_qber": primary_attack,
            },
            "absolute_differences": differences,
            "tolerance": tolerance,
            "within_configured_tolerance": within_tolerance,
            "comparison_method": "ABSOLUTE_QBER_DIFFERENCE",
            "interpretation": (
                "Finite-shot teleportation error-rate differences are compared with the configured "
                "absolute tolerance. This is not a statistical equivalence test."
            ),
        },
    }
def create_quantum_engine(engine_name: str, seed: int | None = None) -> QuantumEngine:
    normalized = engine_name.strip().lower()
    if normalized == "cudaq":
        return CudaQEngine(seed=seed)
    if normalized in {"reference", "statevector", "numpy"}:
        return ReferenceStatevectorEngine(seed=seed)
    if normalized in {"qiskit", "aer", "qiskit-aer"}:
        return QiskitAerEngine(seed=seed)
    raise ValueError(f"Unsupported quantum engine: {engine_name}")
