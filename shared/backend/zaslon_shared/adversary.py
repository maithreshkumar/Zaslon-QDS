from __future__ import annotations

from typing import Any


ADVERSARY_MODELS: dict[str, dict[str, Any]] = {
    "HONEST_PARTICIPANT": {
        "public_information": ["protocol parameters", "own artifact", "document"],
        "private_information_unavailable": ["other verifier evidence", "server role secrets"],
        "channel_access": "none",
        "prior_valid_signatures": False,
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": False,
    },
    "EXTERNAL_FORGER": {
        "public_information": ["protocol parameters", "target document/hash"],
        "private_information_unavailable": [
            "legitimate declaration key bits",
            "trusted verifier evidence",
            "server role credentials",
            "unobserved session nonce",
        ],
        "channel_access": "none",
        "prior_valid_signatures": "scenario-dependent and explicitly reported",
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": False,
    },
    "MALICIOUS_RECIPIENT": {
        "public_information": ["received signature material", "document", "own verifier evidence"],
        "private_information_unavailable": ["other verifier's independent evidence", "signer secrets"],
        "channel_access": "received endpoint only",
        "prior_valid_signatures": True,
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": False,
    },
    "IMPERSONATOR": {
        "public_information": ["public identities", "protocol parameters"],
        "private_information_unavailable": ["role credential", "trusted signer context"],
        "channel_access": "API request boundary",
        "prior_valid_signatures": False,
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": False,
    },
    "REPLAY_ATTACKER": {
        "public_information": ["previously observed valid document and artifact"],
        "private_information_unavailable": ["ability to reset atomic consume ledger"],
        "channel_access": "verification submission boundary",
        "prior_valid_signatures": True,
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": False,
    },
    "QUANTUM_CHANNEL_ATTACKER": {
        "public_information": ["protocol parameters", "channel timing"],
        "private_information_unavailable": ["diagnostic basis before interaction", "role credentials"],
        "channel_access": "declared quantum boundary during a live/counterfactual execution",
        "prior_valid_signatures": False,
        "can_intercept_quantum_states": True,
        "can_alter_correction_bits": False,
    },
    "CLASSICAL_CORRECTION_CHANNEL_MITM": {
        "public_information": ["transmitted Bell-measurement correction bits"],
        "private_information_unavailable": ["role credentials", "verifier private evidence"],
        "channel_access": "Alice-to-Bob classical correction channel",
        "prior_valid_signatures": False,
        "can_intercept_quantum_states": False,
        "can_alter_correction_bits": True,
    },
}


ATTACK_ADVERSARY_MODEL = {
    "BASELINE": "HONEST_PARTICIPANT",
    "INTERCEPT_RESEND": "QUANTUM_CHANNEL_ATTACKER",
    "ENTANGLEMENT_MANIPULATION": "QUANTUM_CHANNEL_ATTACKER",
    "PAULI_MANIPULATION": "QUANTUM_CHANNEL_ATTACKER",
    "BELL_RESULT_MANIPULATION": "MALICIOUS_RECIPIENT",
    "CORRECTION_MITM": "CLASSICAL_CORRECTION_CHANNEL_MITM",
    "SIGNATURE_FORGERY": "EXTERNAL_FORGER",
    "PARTIAL_SIGNATURE_TAMPERING": "EXTERNAL_FORGER",
    "FULL_FORGERY": "EXTERNAL_FORGER",
    "REPLAY": "REPLAY_ATTACKER",
    "IMPERSONATION": "IMPERSONATOR",
}


def adversary_model_for_attack(attack_type: str) -> dict[str, Any]:
    model_id = ATTACK_ADVERSARY_MODEL[attack_type]
    return {"id": model_id, **ADVERSARY_MODELS[model_id]}

