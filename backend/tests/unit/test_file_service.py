"""
Unit tests for FileService: chunked SHA-512 hashing, manifest creation, and certificates.
"""
import pytest
import os
import hashlib
import json
from datetime import datetime, timezone

from backend.app.services.file_service import FileService, CHUNK_SIZE, MAX_FILE_SIZE_BYTES


def test_chunked_sha512_hashing(tmp_path):
    # Test with multi-chunk data (> 64KB)
    test_data = b"ZaslonQDS_SIH26141_" * 5000  # ~95 KB
    expected_digest = hashlib.sha512(test_data).hexdigest()

    meta = FileService.hash_and_save_stream(
        session_id="test_session_chunked",
        filename="telemetry_data.bin",
        stream_bytes=test_data,
        mime_type="application/octet-stream"
    )

    assert meta["filename"] == "telemetry_data.bin"
    assert meta["file_size_bytes"] == len(test_data)
    assert meta["sha512_digest"] == expected_digest
    assert meta["is_binary_file"] is True
    assert os.path.exists(meta["storage_path"])

    # Verify read_file_bytes
    read_back = FileService.read_file_bytes(meta["storage_path"])
    assert read_back == test_data


def test_file_size_limit_rejection():
    oversized_data = b"A" * (MAX_FILE_SIZE_BYTES + 1)
    with pytest.raises(ValueError) as exc:
        FileService.hash_and_save_stream(
            session_id="test_oversized",
            filename="big.iso",
            stream_bytes=oversized_data
        )
    assert "exceeds maximum allowed size" in str(exc.value)


def test_qds_json_manifest_structure():
    manifest = FileService.build_qds_json_manifest(
        package_tracking_no="PKG-TEST-001",
        session_id="sess-001",
        filename="mission_directive.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha512_digest="a" * 128,
        signer_id="Alice",
        verifier_id="Bob",
        declaration_id="decl-001",
        signature_token="tok_abc123",
        declaration_payload_hash="b" * 128,
        quantum_run_id="qrun-001",
        teleportation_count=4096
    )

    assert manifest["format"] == "ZASLON-QDS"
    assert manifest["project_id"] == "SIH-26141"
    assert manifest["profile"] == "ZASLON-QDS-v1"
    assert manifest["package_metadata"]["package_tracking_no"] == "PKG-TEST-001"
    assert manifest["package_metadata"]["channel_type"] == "DUAL_CLASSICAL_QUANTUM"
    assert manifest["document"]["filename"] == "mission_directive.pdf"
    assert manifest["document"]["sha512_digest"] == "a" * 128
    assert manifest["signer"]["signer_id"] == "Alice"
    assert manifest["designated_verifier"]["verifier_id"] == "Bob"
    assert manifest["quantum_binding"]["total_teleportation_operations"] == 4096
    assert manifest["quantum_binding"]["quantum_network_channel"]["fiber_length_km"] == 25.0
    assert manifest["channels"]["classical_channel"]["transport"] == "APPLICATION_LEVEL_CLASSICAL_TRANSMISSION"
    assert "is_consumed" not in manifest["public_declaration"]


def test_certificate_receipt_generation():
    cert = FileService.generate_certificate_receipt(
        session_id="sess-002",
        filename="nav_data.json",
        sha512_digest="c" * 128,
        signer_id="Alice",
        verifier_id="Bob",
        decision="VERIFIED",
        statistical_verdict="STATISTICALLY_ACCEPTABLE",
        sample_size=205,
        match_count=203,
        mismatch_count=2,
        mismatch_ratio=0.00975,
        fisher_p_value=0.64,
        fisher_odds_ratio=1.02,
        contingency_table=[[203, 2], [202, 3]],
        defense_barriers=[
            {"barrier": "IDENTITY", "passed": True},
            {"barrier": "AUTHORIZATION", "passed": True},
            {"barrier": "INTEGRITY", "passed": True},
            {"barrier": "ANTI_REPLAY", "passed": True},
            {"barrier": "QUANTUM_STATISTICAL", "passed": True}
        ],
        attack_detected=False,
        attack_category=None,
        decision_reason="All 5 defense barriers passed successfully.",
        tracking_no="PKG-TEST-002"
    )

    assert cert["decision"] == "VERIFIED"
    assert cert["statistical_verdict"] == "STATISTICALLY_ACCEPTABLE"
    assert cert["attack_detected"] is False
    assert cert["certificate_serial"].startswith("QDS-CERT-")
    assert cert["quantum_statistical_proof"]["total_circuits"] == 4096
    assert cert["quantum_statistical_proof"]["sample_size"] == 205
    assert len(cert["cryptographic_receipt_signature"]) == 128
