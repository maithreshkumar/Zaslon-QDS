from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


class AttackRunRequest(BaseModel):
    qds_session_id: str
    attack_type: Literal[
        "BASELINE",
        "INTERCEPT_RESEND",
        "ENTANGLEMENT_MANIPULATION",
        "PAULI_MANIPULATION",
        "BELL_RESULT_MANIPULATION",
        "CORRECTION_MITM",
        "SIGNATURE_FORGERY",
        "PARTIAL_SIGNATURE_TAMPERING",
        "FULL_FORGERY",
        "REPLAY",
        "IMPERSONATION",
    ]
    target: str
    attack_strength: float = Field(default=0.35, ge=0.0, le=1.0)
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target")
    @classmethod
    def uppercase_target(cls, value: str) -> str:
        return value.strip().upper()


class DecryptRequest(BaseModel):
    encrypted_package: dict[str, Any]
    passphrase: str = Field(min_length=8, max_length=512)


class NoiseRequest(BaseModel):
    bit_flip: float = Field(default=0.0, ge=0.0, le=1.0)
    phase_flip: float = Field(default=0.0, ge=0.0, le=1.0)
    depolarizing: float = Field(default=0.0, ge=0.0, le=1.0)
    measurement_error: float = Field(default=0.0, ge=0.0, le=1.0)


class QiskitValidationRequest(BaseModel):
    shots: int = Field(default=512, ge=32, le=16_384)
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)
    primary_engine: Literal["configured", "cudaq", "reference"] = "configured"
    tolerance: float = Field(default=0.12, gt=0.0, le=0.5)


class DetectorBenchmarkRequest(BaseModel):
    scenarios: list[Literal[
        "HONEST", "BIT_FLIP", "PHASE_FLIP", "Y_ATTACK", "DEPOLARIZING",
        "INTERCEPT_RESEND", "BELL_RESULT_MANIPULATION", "CORRECTION_MITM",
    ]] = Field(default_factory=lambda: ["HONEST", "BIT_FLIP", "PHASE_FLIP"])
    strengths: list[float] = Field(default_factory=lambda: [0.0, 0.1, 0.25, 0.5])
    repetitions: int = Field(default=5, ge=1, le=20)
    shots_per_basis: int = Field(default=64, ge=32, le=512)
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)

    @field_validator("scenarios")
    @classmethod
    def bound_scenarios(cls, value):
        if not value or len(value) > 8:
            raise ValueError("between 1 and 8 scenarios are required")
        return value

    @field_validator("strengths")
    @classmethod
    def bound_strengths(cls, value):
        if not value or len(value) > 9 or any(not 0.0 <= item <= 1.0 for item in value):
            raise ValueError("between 1 and 9 strengths in [0, 1] are required")
        return value


class MultiVerifierExperimentRequest(BaseModel):
    scenario: Literal["HONEST", "SELECTIVE_CHARLIE_DISTURBANCE"] = "HONEST"
    trials: int = Field(default=5, ge=1, le=20)
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)
    selective_charlie_measurement_error: float = Field(default=0.20, ge=0.0, le=1.0)


class NetworkExperimentRequest(BaseModel):
    requested_bell_pairs: int = Field(default=32, ge=1, le=4096)
    include_charlie: bool = False
    correction_flip_mask: Literal[0, 1, 2, 3] = 0
    seed: int = Field(default=2026, ge=0, le=2_147_483_647)


class SignatureDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    position: StrictInt = Field(ge=0, lt=512)
    digest_bit: Literal[0, 1]
    key_bits: list[Literal[0, 1]]
    encoding: Literal["COMPUTATIONAL_BASIS", "PAULI_XZ_EIGENSTATES"]
    bases: list[Literal["Z", "X"]] | None = None


class ServerAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    scheme: Literal["HMAC-SHA512-SERVER-ATTESTED-ROLE-BINDING"]
    key_id: StrictStr = Field(min_length=1, max_length=128)
    signed_fields: Literal["ALL_ARTIFACT_FIELDS_EXCEPT_SERVER_ATTESTATION"]
    tag: StrictStr = Field(pattern=r"^[0-9a-f]{128}$")
    security_scope: Literal["TRUSTED_SERVER_INTEGRITY_AND_ROLE_BINDING"]
    non_repudiation_claim: Literal[False]


class SignatureArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    format: Literal["zaslon.qds.signature.v2", "zaslon.qds.signature.v3"]
    version: Literal["2.0", "3.0"]
    algorithm: Literal["ZASLON-TELEPORTATION-QDS-RESEARCH"]
    protocol: StrictStr = Field(min_length=1, max_length=128)
    protocol_version: StrictStr = Field(min_length=1, max_length=64)
    signature_id: StrictStr = Field(min_length=1, max_length=80)
    session_id: StrictStr = Field(min_length=1, max_length=80)
    signer_id: StrictStr = Field(min_length=1, max_length=64)
    verifier_id: StrictStr = Field(min_length=1, max_length=64)
    document_name: StrictStr = Field(min_length=1, max_length=255)
    document_hash: StrictStr = Field(pattern=r"^[0-9a-f]{128}$")
    hash_algorithm: Literal["SHA-512"]
    nonce: StrictStr = Field(min_length=48, max_length=128)
    created_at: StrictStr = Field(min_length=1, max_length=64)
    prepared_quantum_states: StrictInt = Field(gt=0)
    disclosed_quantum_states: StrictInt = Field(gt=0)
    maximum_simultaneous_circuit_qubits: StrictInt = Field(gt=0, le=64)
    verification_policy: dict[str, Any]
    verification_thresholds: dict[str, Any]
    quantum_parameters: dict[str, Any]
    teleportation_metadata: dict[str, Any]
    quantum_diagnostic: dict[str, Any]
    effective_channel_diagnostic: dict[str, Any] | None = None
    bell_state_analysis: dict[str, Any]
    noise_parameters: dict[str, Any]
    quantum_status: dict[str, Any]
    network_metadata: dict[str, Any] | None = None
    reproducibility: dict[str, Any] | None = None
    declarations: list[SignatureDeclaration]
    signature_declarations: list[SignatureDeclaration]
    server_attestation: ServerAttestation | None = None

    @model_validator(mode="after")
    def version_contract(self):
        if (self.format, self.version) not in {
            ("zaslon.qds.signature.v2", "2.0"),
            ("zaslon.qds.signature.v3", "3.0"),
        }:
            raise ValueError("signature format and version do not match")
        if self.version == "3.0":
            if self.server_attestation is None or self.reproducibility is None:
                raise ValueError("v3 signatures require attestation and reproducibility")
            if any(
                declaration.encoding != "PAULI_XZ_EIGENSTATES"
                or declaration.bases is None
                or len(declaration.bases) != len(declaration.key_bits)
                for declaration in self.declarations
            ):
                raise ValueError("v3 declarations require one X/Z basis per state")
        return self



class HealthResponse(BaseModel):
    status: str
    protocol: str
    protocol_version: str
    quantum: dict[str, Any]
    database: str
