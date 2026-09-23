"""
Deterministic Quantum State Preparation Mapping for Zaslon-QDS.
Expands SHA-512 cryptographic digests into exact quantum state parameters
(theta, phi, basis, expected_bit) for 3-qubit teleportation verification.
Used independently by Bob to derive expected quantum states without trusting database ground-truth.
"""
import hashlib
import math
from typing import List, Dict, Any


def derive_teleportation_parameters(sha512_hex: str, total_count: int = 4096) -> List[Dict[str, Any]]:
    """
    Deterministically expands a 512-bit SHA-512 digest into `total_count`
    teleportation state preparation parameter specifications.

    Args:
        sha512_hex: 128-character hexadecimal string representing SHA-512 output.
        total_count: Number of teleportation operations (default: 4096).

    Returns:
        List of parameter dicts with operation_index, prep_theta, prep_phi, basis, expected_bit.
    """
    if len(sha512_hex) != 128:
        raise ValueError(f"Invalid SHA-512 hex length: expected 128, got {len(sha512_hex)}")

    digest_bytes = bytes.fromhex(sha512_hex)
    parameters: List[Dict[str, Any]] = []

    rounds_needed = math.ceil(total_count / 512)

    all_bits = []
    basis_bits = []

    for r in range(rounds_needed):
        round_hasher = hashlib.sha512()
        round_hasher.update(digest_bytes)
        round_hasher.update(r.to_bytes(4, byteorder='big'))
        round_digest = round_hasher.digest()

        for byte in round_digest:
            for bit_pos in range(8):
                all_bits.append((byte >> (7 - bit_pos)) & 1)

        basis_hasher = hashlib.sha512()
        basis_hasher.update(round_digest)
        basis_hasher.update(b"basis_selection")
        basis_digest = basis_hasher.digest()
        for byte in basis_digest:
            for bit_pos in range(8):
                basis_bits.append((byte >> (7 - bit_pos)) & 1)

    for i in range(total_count):
        bit = all_bits[i]
        basis_flag = basis_bits[i]  # 0 for Computational (Z), 1 for Hadamard (X)
        basis_name = "Z" if basis_flag == 0 else "X"

        if basis_name == "Z":
            theta = 0.0 if bit == 0 else math.pi
            phi = 0.0
        else:
            theta = math.pi / 2.0
            phi = 0.0 if bit == 0 else math.pi

        parameters.append({
            "operation_index": i,
            "prep_theta": float(theta),
            "prep_phi": float(phi),
            "basis": basis_name,
            "expected_bit": int(bit)
        })

    return parameters
