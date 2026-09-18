"""
Unit tests for deterministic quantum state preparation mapping from SHA-512 digests.
"""
import pytest
import math
import hashlib

from quantum.service.circuits.state_prep import derive_teleportation_parameters


def test_state_prep_invalid_input():
    with pytest.raises(ValueError):
        derive_teleportation_parameters("invalid_short_hash")

    with pytest.raises(ValueError):
        derive_teleportation_parameters("g" * 128)  # non-hex character


def test_state_prep_full_4096_operations():
    test_msg = b"SIH 26141 Zaslon-QDS Production Digest Test"
    digest = hashlib.sha512(test_msg).hexdigest()

    params = derive_teleportation_parameters(digest, total_count=4096)
    assert len(params) == 4096

    # Verify contiguous indexing
    for i, p in enumerate(params):
        assert p["operation_index"] == i
        assert p["basis"] in ("Z", "X")
        assert p["expected_bit"] in (0, 1)

        if p["basis"] == "Z":
            assert math.isclose(p["prep_phi"], 0.0, abs_tol=1e-5)
            if p["expected_bit"] == 0:
                assert math.isclose(p["prep_theta"], 0.0, abs_tol=1e-5)
            else:
                assert math.isclose(p["prep_theta"], math.pi, abs_tol=1e-5)
        else:  # basis == "X"
            assert math.isclose(p["prep_theta"], math.pi / 2.0, abs_tol=1e-5)
            if p["expected_bit"] == 0:
                assert math.isclose(p["prep_phi"], 0.0, abs_tol=1e-5)
            else:
                assert math.isclose(p["prep_phi"], math.pi, abs_tol=1e-5)


def test_state_prep_avalanche_effect():
    # Two messages differing by a single bit
    digest1 = hashlib.sha512(b"Message A").hexdigest()
    digest2 = hashlib.sha512(b"Message B").hexdigest()

    params1 = derive_teleportation_parameters(digest1, total_count=512)
    params2 = derive_teleportation_parameters(digest2, total_count=512)

    diff_count = sum(1 for p1, p2 in zip(params1, params2) if p1["expected_bit"] != p2["expected_bit"] or p1["basis"] != p2["basis"])
    # In cryptographically sound expansion, roughly 50-75% of properties should differ
    assert diff_count > 150
