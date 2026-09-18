"""
File Service for Zaslon-QDS.
Handles chunked streaming SHA-512 hashing, storage of uploaded documents,
generation of portable <filename>.qds.json signature bundles,
and verification certificate receipts.
"""
import os
import hashlib
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import uuid
import logging

from ..core.datetime_utils import utc_now
from ..core.security import compute_sha512

logger = logging.getLogger("zaslon.services.file")

CHUNK_SIZE = 65536  # 64 KB chunks for streaming
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
BASE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


class FileService:
    @classmethod
    def get_upload_path(cls, session_id: str, filename: str) -> str:
        session_dir = os.path.join(BASE_UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        # Sanitize filename
        safe_filename = os.path.basename(filename).replace(" ", "_")
        return os.path.join(session_dir, safe_filename)

    @classmethod
    def hash_and_save_stream(
        cls,
        session_id: str,
        filename: str,
        stream_bytes: bytes,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Hashes byte stream using SHA-512 in chunks and writes to disk.
        Returns file metadata dictionary.
        """
        file_size = len(stream_bytes)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File exceeds maximum allowed size of 50 MB (got {file_size / (1024*1024):.2f} MB)")

        hasher = hashlib.sha512()
        for i in range(0, file_size, CHUNK_SIZE):
            hasher.update(stream_bytes[i:i + CHUNK_SIZE])

        sha512_digest = hasher.hexdigest()
        storage_path = cls.get_upload_path(session_id, filename)

        with open(storage_path, "wb") as f:
            f.write(stream_bytes)

        logger.info(f"Saved file {filename} ({file_size} bytes) for session {session_id} with SHA-512 {sha512_digest[:16]}...")

        return {
            "filename": os.path.basename(filename),
            "mime_type": mime_type or "application/octet-stream",
            "file_size_bytes": file_size,
            "sha512_digest": sha512_digest,
            "storage_path": storage_path,
            "is_binary_file": True
        }

    @classmethod
    def read_file_bytes(cls, storage_path: str) -> bytes:
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"File not found at {storage_path}")
        with open(storage_path, "rb") as f:
            return f.read()

    @classmethod
    def build_qds_json_manifest(
        cls,
        package_tracking_no: str,
        session_id: str,
        filename: str,
        file_size_bytes: int,
        mime_type: str,
        sha512_digest: str,
        signer_id: str,
        verifier_id: str,
        declaration_id: str,
        signature_token: str,
        declaration_payload_hash: str,
        quantum_run_id: str,
        teleportation_count: int = 4096,
        sample_ratio: float = 0.05,
        baseline_error_rate: float = 0.01,
        mismatch_threshold_ratio: float = 0.03,
        fisher_significance_alpha: float = 0.01,
        declared_at: Optional[datetime] = None,
        replay_window_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Builds the standardized <filename>.qds.json cryptographic signature bundle.
        """
        now = utc_now()
        declared_iso = (declared_at or now).isoformat()
        
        manifest = {
            "$schema": "https://zaslon-qds.org/schemas/qds-package-v1.json",
            "format": "ZASLON-QDS",
            "version": "1.0",
            "project_id": "SIH-26141",
            "profile": "ZASLON-QDS-v1",
            "package_metadata": {
                "package_tracking_no": package_tracking_no,
                "session_id": session_id,
                "created_at": now.isoformat(),
                "channel_type": "DUAL_CLASSICAL_QUANTUM"
            },
            "document": {
                "filename": filename,
                "filesize_bytes": file_size_bytes,
                "mime_type": mime_type,
                "sha512_digest": sha512_digest,
                "digest_algorithm": "SHA-512",
                "encoding": "hex"
            },
            "signer": {
                "signer_id": signer_id,
                "role": "Signer",
                "signature_timestamp": declared_iso
            },
            "designated_verifier": {
                "verifier_id": verifier_id,
                "role": "Verifier"
            },
            "public_declaration": {
                "declaration_id": declaration_id,
                "signature_token": signature_token,
                "declaration_payload_hash": declaration_payload_hash,
                "nonce": f"nonce_{uuid.uuid4().hex[:32]}",
                "declared_at": declared_iso,
                "replay_window_seconds": replay_window_seconds
            },
            "quantum_binding": {
                "quantum_run_id": quantum_run_id,
                "circuit_topology": "3-Qubit Quantum Teleportation (Nielsen & Chuang §4.4)",
                "total_teleportation_operations": teleportation_count,
                "state_prep_algorithm": "SHA512-Deterministic-Expansion-v1",
                "verification_sample_ratio": sample_ratio,
                "channel_baseline_error_rate": baseline_error_rate,
                "mismatch_threshold_ratio": mismatch_threshold_ratio,
                "fisher_significance_alpha": fisher_significance_alpha,
                "quantum_network_channel": {
                    "medium_profile": "demo-fiber-25km",
                    "fiber_length_km": 25.0,
                    "attenuation_db_per_km": 0.20,
                    "propagation_velocity_mps": 204000000.0,
                    "expected_latency_us": 122.5
                }
            },
            "channels": {
                "classical_channel": {
                    "payload_type": "DOCUMENT_BYTES_AND_SIGNATURE_MANIFEST",
                    "transport": "APPLICATION_LEVEL_CLASSICAL_TRANSMISSION"
                },
                "quantum_channel": {
                    "payload_type": "3_QUBIT_TELEPORTED_STATES_AND_CORRECTIONS",
                    "operations_count": teleportation_count
                }
            }
        }
        return manifest

    @classmethod
    def generate_certificate_receipt(
        cls,
        session_id: str,
        filename: str,
        sha512_digest: str,
        signer_id: str,
        verifier_id: str,
        decision: str,
        statistical_verdict: str,
        sample_size: int,
        match_count: int,
        mismatch_count: int,
        mismatch_ratio: float,
        fisher_p_value: Optional[float],
        fisher_odds_ratio: Optional[float],
        contingency_table: Optional[list],
        defense_barriers: list,
        attack_detected: bool,
        attack_category: Optional[str],
        decision_reason: str,
        tracking_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds the official cryptographic verification certificate receipt (<filename>.cert.json).
        """
        now = utc_now()
        date_str = now.strftime("%Y%m%d")
        rand_hex = hashlib.sha256(f"{session_id}_{now.isoformat()}".encode()).hexdigest()[:8].upper()
        cert_serial = f"QDS-CERT-{date_str}-{rand_hex}"

        certificate = {
            "certificate_serial": cert_serial,
            "protocol": "Zaslon-QDS-Verification-v1",
            "standard": "SIH 26141",
            "verification_timestamp": now.isoformat(),
            "tracking_no": tracking_no or f"QDS-PKG-{date_str}-{rand_hex}",
            "decision": decision,
            "statistical_verdict": statistical_verdict,
            "attack_detected": attack_detected,
            "attack_category": attack_category,
            "decision_reason": decision_reason,
            "document": {
                "filename": filename,
                "sha512_digest": sha512_digest,
                "verification_source": "AUTHENTIC_DUAL_CHANNEL"
            },
            "parties": {
                "signer": signer_id,
                "verifier": verifier_id
            },
            "quantum_statistical_proof": {
                "total_circuits": 4096,
                "sample_size": sample_size,
                "match_count": match_count,
                "mismatch_count": mismatch_count,
                "mismatch_ratio": mismatch_ratio,
                "mismatch_ratio_percent": f"{mismatch_ratio * 100:.2f}%",
                "threshold_ratio_percent": "3.00%",
                "channel_baseline_error_percent": "1.00%",
                "fisher_p_value": fisher_p_value if fisher_p_value is not None else 1.0,
                "fisher_odds_ratio": fisher_odds_ratio,
                "contingency_table": contingency_table,
                "hypothesis_test": "Hypergeometric Fisher's Exact Test (one-sided: alternative='less')"
            },
            "defense_barriers_evaluated": defense_barriers,
            "cryptographic_receipt_signature": compute_sha512(
                f"{cert_serial}:{session_id}:{decision}:{sha512_digest}:{fisher_p_value}".encode()
            )
        }
        return certificate
