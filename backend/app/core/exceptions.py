"""
Custom Typed Domain Exceptions for Zaslon-QDS.
"""
from typing import Optional, Dict, Any


class ZaslonBaseException(Exception):
    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class SessionNotFoundError(ZaslonBaseException):
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session '{session_id}' not found.",
            code="SESSION_NOT_FOUND",
            details={"session_id": session_id}
        )


class CudaQUnavailableError(ZaslonBaseException):
    def __init__(self, detail: str = "NVIDIA CUDA-Q is unavailable in the execution environment."):
        super().__init__(
            message=detail,
            code="CUDA_Q_UNAVAILABLE",
            details={"resolution": "Run within the CUDA-Q enabled container or environment."}
        )


class QuantumExecutionError(ZaslonBaseException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="QUANTUM_EXECUTION_ERROR",
            details=details
        )


class UnauthorizedError(ZaslonBaseException):
    def __init__(self, reason: str, actor: Optional[str] = None):
        super().__init__(
            message=f"Unauthorized operation: {reason}",
            code="UNAUTHORIZED",
            details={"actor": actor, "reason": reason}
        )


class IntegrityTamperingError(ZaslonBaseException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INTEGRITY_FAILURE",
            details=details
        )


class ReplayAttackError(ZaslonBaseException):
    def __init__(self, message: str, token: str):
        super().__init__(
            message=message,
            code="REPLAY_DETECTED",
            details={"token": token}
        )


class VerificationStateError(ZaslonBaseException):
    def __init__(self, current_status: str, expected_status: str):
        super().__init__(
            message=f"Cannot verify session in status '{current_status}'. Expected status: '{expected_status}'.",
            code="INVALID_STATE_TRANSITION",
            details={"current_status": current_status, "expected_status": expected_status}
        )
