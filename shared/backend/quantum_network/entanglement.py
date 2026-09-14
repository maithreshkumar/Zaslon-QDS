from zaslon_shared.quantum import Pauli


def validate_entanglement_operation(operation: Pauli) -> Pauli:
    if operation not in ("I", "X", "Y", "Z"):
        raise ValueError("Unsupported entanglement operation")
    return operation

