CORRECTIONS = {0: "I", 1: "X", 2: "Z", 3: "XZ"}


def correction_for_mask(mask: int) -> str:
    try:
        return CORRECTIONS[mask]
    except KeyError as exc:
        raise ValueError("Bell correction mask must be 0, 1, 2, or 3") from exc

