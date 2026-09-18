"""
Unit tests for fail-fast configuration and startup settings validation.
Verifies compliance with Master Prompt 4, Section 30.
"""
import pytest
from pydantic import ValidationError
from backend.app.core.config import Settings


def test_valid_default_settings():
    s = Settings()
    assert s.TELEPORTATION_COUNT == 4096
    assert s.QUANTUM_BATCH_SIZE == 512
    assert s.VERIFICATION_SAMPLE_RATIO == 0.05
    assert s.FISHER_SIGNIFICANCE_ALPHA == 0.01
    assert s.MISMATCH_THRESHOLD_RATIO == 0.03
    assert "http://localhost:3000" in s.CORS_ORIGINS


def test_invalid_teleportation_count_zero():
    with pytest.raises(ValidationError):
        Settings(TELEPORTATION_COUNT=0)


def test_invalid_negative_batch_size():
    with pytest.raises(ValidationError):
        Settings(QUANTUM_BATCH_SIZE=-1)


def test_invalid_sample_ratio_exceeds_one():
    with pytest.raises(ValidationError):
        Settings(VERIFICATION_SAMPLE_RATIO=1.5)


def test_invalid_sample_ratio_zero():
    with pytest.raises(ValidationError):
        Settings(VERIFICATION_SAMPLE_RATIO=0.0)


def test_invalid_alpha_zero_or_negative():
    with pytest.raises(ValidationError):
        Settings(FISHER_SIGNIFICANCE_ALPHA=0.0)
    with pytest.raises(ValidationError):
        Settings(FISHER_SIGNIFICANCE_ALPHA=-0.05)


def test_invalid_empty_database_host():
    with pytest.raises(ValidationError):
        Settings(DATABASE_HOST="   ")


def test_invalid_empty_cuda_target():
    with pytest.raises(ValidationError):
        Settings(CUDA_TARGET="")


def test_cors_origins_comma_separated_string_parsing():
    s = Settings(CORS_ORIGINS="http://app.internal:3000, https://zaslon.domain.gov")
    assert isinstance(s.CORS_ORIGINS, list)
    assert len(s.CORS_ORIGINS) == 2
    assert "http://app.internal:3000" in s.CORS_ORIGINS
    assert "https://zaslon.domain.gov" in s.CORS_ORIGINS
