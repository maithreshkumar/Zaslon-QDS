from zaslon_shared.quantum import Basis


def validate_state_label(bit: int, basis: Basis) -> tuple[int, Basis]:
    if bit not in (0, 1) or basis not in ("Z", "X"):
        raise ValueError("Only Z/X teleportation test-state labels are supported")
    return bit, basis
