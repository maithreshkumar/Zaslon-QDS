"""
Three-Qubit Quantum Teleportation Circuit Implementation using NVIDIA CUDA-Q.

Qubit allocations:
- q[0]: Message qubit (prepared via SHA-512 derived rotation angles)
- q[1]: Alice's Bell pair qubit
- q[2]: Bob's Bell pair qubit (target for reconstructed state)

Principle of Deferred Measurement (Nielsen & Chuang §4.4):
Alice's Bell-basis measurement and classical feed-forward corrections
are mapped to coherent quantum operations (controlled-X and controlled-Z)
prior to terminal measurement. This eliminates mid-circuit classical branching,
guaranteeing full compatibility with CUDA-Q high-performance sampling across all backends.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("zaslon.quantum.teleportation")

try:
    import cudaq
    CUDA_Q_AVAILABLE = True
except ImportError:
    cudaq = None
    CUDA_Q_AVAILABLE = False


if CUDA_Q_AVAILABLE:
    @cudaq.kernel
    def three_qubit_teleport_kernel(theta: float, phi: float, basis_flag: int):
        """
        Executes a 3-qubit quantum teleportation circuit on CUDA-Q.

        Args:
            theta: Rotation angle for Ry on message qubit q[0].
            phi: Rotation angle for Rz on message qubit q[0].
            basis_flag: 0 for Z-basis measurement, 1 for X-basis measurement.
        """
        # Allocate 3-qubit register: q[0]=message, q[1]=Alice Bell, q[2]=Bob Bell
        q = cudaq.qvector(3)

        # 1. State preparation on message qubit q[0]
        ry(theta, q[0])
        rz(phi, q[0])

        # 2. Bell pair generation between Alice (q[1]) and Bob (q[2])
        h(q[1])
        cx(q[1], q[2])

        # 3. Alice interacts message qubit with her Bell qubit
        cx(q[0], q[1])
        h(q[0])

        # 4. Deferred measurement corrections (Nielsen & Chuang §4.4):
        # Alice's q[1] feeds forward X correction to Bob's q[2]
        cx(q[1], q[2])
        # Alice's q[0] feeds forward Z correction to Bob's q[2]
        # Controlled-Z realized via H -> CNOT -> H
        h(q[2])
        cx(q[0], q[2])
        h(q[2])

        # 5. Bob's verification measurement in designated basis
        if basis_flag == 1:
            h(q[2])  # Basis rotation from X to Z for measurement

        # 6. Terminal measurement on all 3 qubits in order: q[0], q[1], q[2]
        mz(q[0])
        mz(q[1])
        mz(q[2])


def execute_teleportation_circuit(
    theta: float,
    phi: float,
    basis: str,
    shots: int = 1
) -> Dict[str, Any]:
    """
    Executes a single teleportation operation using CUDA-Q.
    Raises RuntimeError if CUDA-Q is unavailable.
    """
    if not CUDA_Q_AVAILABLE:
        raise RuntimeError("CUDA_Q_UNAVAILABLE: NVIDIA CUDA-Q runtime is not available in this environment.")

    basis_flag = 1 if basis == "X" else 0

    # Execute sample using CUDA-Q simulation target
    counts = cudaq.sample(three_qubit_teleport_kernel, theta, phi, basis_flag, shots_count=shots)

    # Get observed bitstring
    most_frequent_bitstring = counts.most_probable()
    raw_str = str(most_frequent_bitstring).strip()

    # In CUDA-Q, register measurements reflect the measured bits in sequence:
    # q0 (m0), q1 (m1), and q2 (Bob's observed outcome)
    bits = [int(c) for c in raw_str if c in ('0', '1')]
    if len(bits) >= 3:
        m0 = bits[0]
        m1 = bits[1]
        bob_meas = bits[2]
    else:
        m0 = bits[0] if len(bits) > 0 else 0
        m1 = bits[1] if len(bits) > 1 else 0
        bob_meas = bits[-1] if len(bits) > 0 else 0

    return {
        "m0": m0,
        "m1": m1,
        "correction_x": m1,
        "correction_z": m0,
        "bob_observed_bit": bob_meas,
        "counts": {str(k): int(v) for k, v in counts.items()}
    }

