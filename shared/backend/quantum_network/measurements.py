def mismatch_rate(mismatches: int, usable: int) -> float | None:
    if mismatches < 0 or usable < 0 or mismatches > usable:
        raise ValueError("Invalid measurement counts")
    return mismatches / usable if usable else None

