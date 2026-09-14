import numpy as np


def pure_state_fidelity(first, second) -> float:
    a = np.asarray(first, dtype=complex)
    b = np.asarray(second, dtype=complex)
    if not np.isclose(np.linalg.norm(a), 1) or not np.isclose(np.linalg.norm(b), 1):
        raise ValueError("States must be normalized")
    return float(abs(np.vdot(a, b)) ** 2)

