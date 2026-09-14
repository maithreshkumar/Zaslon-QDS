def correction_mask(first_bit: int, second_bit: int) -> int:
    """Encode Bell result using bit 1 for X and bit 2 for Z correction."""
    return (int(bool(first_bit)) << 1) | int(bool(second_bit))

