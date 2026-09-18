"""
Unit tests validating foundational cryptography, state mapping, and statistical tests.
"""
import pytest
import math
import hashlib

from backend.app.core.security import compute_sha512, generate_secure_token
from backend.app.services.statistics_service import StatisticsService
from quantum.service.circuits.state_prep import derive_teleportation_parameters


def test_sha512_computation():
    msg = b"SIH 26141 Zaslon-QDS Test Message"
    digest = compute_sha512(msg)
    expected = hashlib.sha512(msg).hexdigest()
    assert digest == expected
    assert len(digest) == 128


def test_secure_token_generation():
    tok1 = generate_secure_token()
    tok2 = generate_secure_token()
    assert tok1 != tok2
    assert tok1.startswith("qds_tok_")


def test_deterministic_state_mapping_reproducibility():
    digest = "a" * 128
    params1 = derive_teleportation_parameters(digest, total_count=100)
    params2 = derive_teleportation_parameters(digest, total_count=100)
    assert len(params1) == 100
    assert params1 == params2

    # Check structure
    for p in params1:
        assert "operation_index" in p
        assert "prep_theta" in p
        assert "prep_phi" in p
        assert "basis" in p
        assert p["basis"] in ("Z", "X")
        assert p["expected_bit"] in (0, 1)


def test_fisher_exact_test_acceptable():
    # 205 operations sampled, 0 mismatches (ideal quantum channel)
    res = StatisticsService.run_fisher_exact_test(match_count=205, mismatch_count=0)
    assert res["statistical_verdict"] == "ACCEPTABLE"
    assert res["p_value"] >= 0.01


def test_fisher_exact_test_suspicious_forgery():
    # 205 operations sampled, 50 mismatches (high mismatch indicating forgery/eavesdropping)
    res = StatisticsService.run_fisher_exact_test(match_count=155, mismatch_count=50)
    assert res["statistical_verdict"] == "SUSPICIOUS"
    assert res["p_value"] < 0.01
