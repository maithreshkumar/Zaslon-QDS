"""
Three-Qubit Quantum Teleportation Circuit Implementation using NVIDIA CUDA-Q.

Qubit allocations:
- q[0]: Message qubit (prepared via SHA-512 derived rotation angles)
- q[1]: Alice's Bell pair qubit
- q[2]: Bob's Bell pair qubit (target for reconstructed state)
- q[3]: Eve's ancilla qubit (active only during physical Intercept-and-Resend)

Principle of Deferred Measurement (Nielsen & Chuang §4.4):
Alice's Bell-basis measurement and classical feed-forward corrections
are mapped to coherent quantum operations (controlled-X and controlled-Z)
prior to terminal measurement. This eliminates mid-circuit classical branching,
guaranteeing full compatibility with CUDA-Q high-performance sampling across all backends.
"""
from typing import Dict, Any, Optional, List
import logging
import math
import random

logger = logging.getLogger("zaslon.quantum.teleportation")

try:
    import cudaq
    CUDA_Q_AVAILABLE = True
    try:
        cudaq.set_target("density-matrix-cpu")
    except Exception as e:
        logger.warning(f"Could not set CUDA-Q density-matrix-cpu target: {e}")
except ImportError:
    cudaq = None
    CUDA_Q_AVAILABLE = False


if CUDA_Q_AVAILABLE:
    @cudaq.kernel
    def three_qubit_teleport_kernel(
        theta: float,
        phi: float,
        basis_flag: int,
        phase_drift: float,
        basis_tilt: float,
        bit_flip: int,
        is_intercepted: int,
        intercept_basis: int,
        is_severed: int
    ):
        """
        Executes a 3-qubit quantum teleportation circuit on CUDA-Q with pre-measurement
        physical perturbations during channel transit.

        Args:
            theta: Rotation angle for Ry on message qubit q[0].
            phi: Rotation angle for Rz on message qubit q[0].
            basis_flag: 0 for Z-basis measurement, 1 for X-basis measurement.
            phase_drift: Phase rotation (Rz) on q[2] during transit.
            basis_tilt: Polarization / basis rotation (Ry) on q[2] during transit.
            bit_flip: 1 to apply bit-flip (X) on q[2], 0 otherwise.
            is_intercepted: 1 if Eve intercepts and re-prepares, 0 otherwise.
            intercept_basis: 0 for Z basis, 1 for X basis.
            is_severed: 1 if Bell pair entanglement is severed, 0 otherwise.
        """
        # Allocate 4-qubit register: q[0]=message, q[1]=Alice Bell, q[2]=Bob Bell, q[3]=Eve ancilla
        q = cudaq.qvector(4)

        # 1. State preparation on message qubit q[0]
        ry(theta, q[0])
        rz(phi, q[0])

        # 2. Bell pair generation between Alice (q[1]) and Bob (q[2])
        if is_severed == 0:
            h(q[1])
            cx(q[1], q[2])
        else:
            # Broken Bell pair (q[2] remains unentangled ground state)
            h(q[1])

        # 3. Alice interacts message qubit with her Bell qubit
        cx(q[0], q[1])
        h(q[0])

        # 4. Deferred measurement corrections (Nielsen & Chuang §4.4):
        # Alice's q[1] feeds forward X correction to Bob's q[2]
        # Alice's q[0] feeds forward Z correction to Bob's q[2]
        if is_severed == 0:
            cx(q[1], q[2])
            h(q[2])
            cx(q[0], q[2])
            h(q[2])

        # 5. Pre-measurement physical perturbations during in-flight optical transit:
        # Phase drift / dephasing
        if phase_drift != 0.0:
            rz(phase_drift, q[2])

        # Direct bit-flip perturbation
        if bit_flip == 1:
            x(q[2])

        # Intercept-and-Resend simulation:
        # Eve performs projective measurement in chosen basis using ancilla q[3]
        if is_intercepted == 1:
            if intercept_basis == 1:
                h(q[2])
            cx(q[2], q[3])
            if intercept_basis == 1:
                h(q[2])

        # Polarization drift / basis misalignment
        if basis_tilt != 0.0:
            ry(basis_tilt, q[2])

        # 6. Bob's verification measurement basis transformation
        if basis_flag == 1:
            h(q[2])  # Basis rotation from X to Z for measurement

        # 7. Terminal measurement on all qubits: q[0], q[1], q[2], q[3]
        mz(q[0])
        mz(q[1])
        mz(q[2])
        mz(q[3])


def execute_teleportation_circuit(
    theta: float,
    phi: float,
    basis: str,
    phase_drift_rad: float = 0.0,
    basis_rotation_rad: float = 0.0,
    bit_flip: int = 0,
    is_intercepted: int = 0,
    intercept_basis: int = 0,
    is_severed: int = 0,
    shots: int = 1
) -> Dict[str, Any]:
    """
    Executes a single teleportation operation using CUDA-Q.
    Raises RuntimeError if CUDA-Q is unavailable.
    """
    if not CUDA_Q_AVAILABLE:
        raise RuntimeError("CUDA_Q_UNAVAILABLE: NVIDIA CUDA-Q runtime is not available in this environment.")

    basis_flag = 1 if basis == "X" else 0

    counts = cudaq.sample(
        three_qubit_teleport_kernel,
        theta,
        phi,
        basis_flag,
        phase_drift_rad,
        basis_rotation_rad,
        bit_flip,
        is_intercepted,
        intercept_basis,
        is_severed,
        shots_count=shots
    )

    most_frequent_bitstring = counts.most_probable()
    raw_str = str(most_frequent_bitstring).strip()

    # Bits in sequence: q[0] (m0), q[1] (m1), q[2] (bob_meas), q[3] (eve_meas)
    bits = [int(c) for c in raw_str if c in ('0', '1')]
    if len(bits) >= 3:
        m0 = bits[0]
        m1 = bits[1]
        bob_meas = bits[2]
        eve_meas = bits[3] if len(bits) >= 4 else 0
    else:
        m0 = bits[0] if len(bits) > 0 else 0
        m1 = bits[1] if len(bits) > 1 else 0
        bob_meas = bits[-1] if len(bits) > 0 else 0
        eve_meas = 0

    return {
        "m0": m0,
        "m1": m1,
        "correction_x": m1,
        "correction_z": m0,
        "bob_observed_bit": bob_meas,
        "eve_observed_bit": eve_meas,
        "counts": {str(k): int(v) for k, v in counts.items()}
    }
