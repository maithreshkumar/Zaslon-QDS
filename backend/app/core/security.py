"""
Cryptographic and Security Helpers for Zaslon-QDS.
"""
import hashlib
import secrets
import hmac
from typing import Tuple, Optional


def compute_sha512(data: bytes) -> str:
    """Computes standard SHA-512 hex digest from byte stream."""
    return hashlib.sha512(data).hexdigest()


def generate_secure_token(prefix: str = "qds_tok_") -> str:
    """Generates a high-entropy cryptographically secure token."""
    return f"{prefix}{secrets.token_hex(32)}"


def verify_hmac(key: bytes, message: bytes, expected_signature: str) -> bool:
    """Constant-time HMAC validation."""
    computed = hmac.new(key, message, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, expected_signature)


class SecurityVerdicts:
    # Signature Verification Status
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    
    # Integrity Status
    INTEGRITY_VALID = "INTEGRITY_VALID"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"

    # Authorization Status
    AUTHORIZED = "AUTHORIZED"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Attack Detection Status
    NO_ATTACK_DETECTED = "NO_ATTACK_DETECTED"
    ATTACK_DETECTED = "ATTACK_DETECTED"

    # Statistical Evaluation
    STATISTICALLY_ACCEPTABLE = "STATISTICALLY_ACCEPTABLE"
    STATISTICALLY_SUSPICIOUS = "STATISTICALLY_SUSPICIOUS"


class ThreatCategories:
    # -------------------------------------------------------------------------
    # Technical Underlying Threat Identifiers
    # -------------------------------------------------------------------------
    QUANTUM_BIT_FLIP_FORGERY = "QUANTUM_BIT_FLIP_FORGERY"
    QUANTUM_PHASE_FLIP_DEPOLARIZATION = "QUANTUM_PHASE_FLIP_DEPOLARIZATION"
    QUANTUM_BASIS_ALTERATION = "QUANTUM_BASIS_ALTERATION"
    QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS = "QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS"
    ARTIFACT_METADATA_TAMPERING = "ARTIFACT_METADATA_TAMPERING"
    ARTIFACT_DIGEST_MISMATCH = "ARTIFACT_DIGEST_MISMATCH"
    ARTIFACT_PAYLOAD_SUBSTITUTION = "ARTIFACT_PAYLOAD_SUBSTITUTION"
    PROTOCOL_SIGNER_IMPERSONATION = "PROTOCOL_SIGNER_IMPERSONATION"
    PROTOCOL_VERIFIER_SPOOFING = "PROTOCOL_VERIFIER_SPOOFING"
    PROTOCOL_REPLAY_CONSUMED_TOKEN = "PROTOCOL_REPLAY_CONSUMED_TOKEN"
    PROTOCOL_EXPIRED_WINDOW_REPLAY = "PROTOCOL_EXPIRED_WINDOW_REPLAY"
    ACCESS_UNAUTHORIZED_VERIFIER_PROBE = "ACCESS_UNAUTHORIZED_VERIFIER_PROBE"
    SYSTEM_CROSS_SESSION_SUBSTITUTION = "SYSTEM_CROSS_SESSION_SUBSTITUTION"

    # -------------------------------------------------------------------------
    # Canonical 13 Attack Names
    # -------------------------------------------------------------------------
    # Family 1: Identity & Authorization Attacks
    IMPERSONATION = "IMPERSONATION"
    UNAUTHORIZED_VERIFICATION = "UNAUTHORIZED_VERIFICATION"
    UNAUTHORIZED_PROBE = "UNAUTHORIZED_PROBE"

    # Family 2: Artifact & Integrity Attacks
    FILE_INTEGRITY_TAMPERING = "FILE_INTEGRITY_TAMPERING"
    DECLARATION_TAMPERING = "DECLARATION_TAMPERING"
    QDS_PACKAGE_TAMPERING = "QDS_PACKAGE_TAMPERING"
    FORGERY = "FORGERY"

    # Family 3: Protocol Attacks
    REPLAY = "REPLAY"
    INTERCEPT_AND_RESEND = "INTERCEPT_AND_RESEND"
    SESSION_SUBSTITUTION = "SESSION_SUBSTITUTION"

    # Family 4: Quantum Evidence Attacks
    MEASUREMENT_MANIPULATION = "MEASUREMENT_MANIPULATION"
    BASIS_MANIPULATION = "BASIS_MANIPULATION"
    QUANTUM_STATE_REPLACEMENT = "QUANTUM_STATE_REPLACEMENT"

    # Legacy Backward-Compatibility Alias
    INTEGRITY_TAMPERING = "INTEGRITY_TAMPERING"

    ALL_ATTACK_VECTORS = [
        # Canonical 13
        IMPERSONATION,
        UNAUTHORIZED_VERIFICATION,
        UNAUTHORIZED_PROBE,
        FILE_INTEGRITY_TAMPERING,
        DECLARATION_TAMPERING,
        QDS_PACKAGE_TAMPERING,
        FORGERY,
        REPLAY,
        INTERCEPT_AND_RESEND,
        SESSION_SUBSTITUTION,
        MEASUREMENT_MANIPULATION,
        BASIS_MANIPULATION,
        QUANTUM_STATE_REPLACEMENT,
        # Technical aliases
        QUANTUM_BIT_FLIP_FORGERY,
        QUANTUM_PHASE_FLIP_DEPOLARIZATION,
        QUANTUM_BASIS_ALTERATION,
        QUANTUM_ENTANGLEMENT_INTERCEPTION_DOS,
        ARTIFACT_METADATA_TAMPERING,
        ARTIFACT_DIGEST_MISMATCH,
        ARTIFACT_PAYLOAD_SUBSTITUTION,
        PROTOCOL_SIGNER_IMPERSONATION,
        PROTOCOL_VERIFIER_SPOOFING,
        PROTOCOL_REPLAY_CONSUMED_TOKEN,
        PROTOCOL_EXPIRED_WINDOW_REPLAY,
        ACCESS_UNAUTHORIZED_VERIFIER_PROBE,
        SYSTEM_CROSS_SESSION_SUBSTITUTION,
        INTEGRITY_TAMPERING,
    ]
