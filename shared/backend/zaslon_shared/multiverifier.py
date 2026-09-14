from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import uuid
from typing import Any, Literal

from .crypto import sha512_hex
from .config import settings
from .network import configured_network, simulate_sequence_network
from .protocol import create_qds_session, verify_document
from .quantum import NoiseConfig, derive_simulation_seed
from .security_analysis import wilson_interval


VerifierId = Literal["Bob", "Charlie"]


def create_multiverifier_bundle(
    *,
    document: bytes,
    filename: str,
    seed: int,
    authentication_threshold: float = 0.05,
    forwarding_threshold: float = 0.10,
    bob_noise: NoiseConfig | None = None,
    charlie_noise: NoiseConfig | None = None,
) -> dict[str, Any]:
    """Create one logical signature bundle with independent recipient evidence.

    This is an experimental extension: each recipient receives a distinct simulated
    teleportation/evidence stream for the same message. It is not claimed to be a
    formally proven standard QDS symmetrization construction.
    """
    if not 0.0 <= authentication_threshold < forwarding_threshold <= 1.0:
        raise ValueError("thresholds must satisfy 0 <= s_a < s_v <= 1")
    requested_pairs = 512 * 2 * settings.states_per_candidate
    bob_network = None
    charlie_network = None
    if settings.sequence_enabled and importlib.util.find_spec("sequence") is not None:
        bob_seed = derive_simulation_seed(seed, "MULTIVERIFIER_BOB_NETWORK")
        charlie_seed = derive_simulation_seed(seed, "MULTIVERIFIER_CHARLIE_NETWORK")
        bob_network = simulate_sequence_network(
            requested_bell_pairs=requested_pairs,
            config=configured_network(seed=bob_seed),
            correction_receiver="Bob",
        )
        charlie_network = simulate_sequence_network(
            requested_bell_pairs=requested_pairs,
            config=configured_network(seed=charlie_seed, include_charlie=True),
            correction_receiver="Charlie",
        )
        if not bob_network["gate_to_cudaq"]["allowed"]:
            raise RuntimeError("BOB_ENTANGLEMENT_DISTRIBUTION_FAILED")
        if not charlie_network["gate_to_cudaq"]["allowed"]:
            raise RuntimeError("CHARLIE_ENTANGLEMENT_DISTRIBUTION_FAILED")
    bob = create_qds_session(
        document=document,
        filename=filename,
        signer_id="Alice",
        verifier_id="Bob",
        seed=derive_simulation_seed(seed, "MULTIVERIFIER_BOB_EVIDENCE"),
        noise=bob_noise or NoiseConfig(),
        verification_threshold=authentication_threshold,
        threshold_source="MULTIVERIFIER_EXPERIMENT_S_A",
        network_context=bob_network,
    )
    charlie = create_qds_session(
        document=document,
        filename=filename,
        signer_id="Alice",
        verifier_id="Charlie",
        seed=derive_simulation_seed(seed, "MULTIVERIFIER_CHARLIE_EVIDENCE"),
        noise=charlie_noise or NoiseConfig(),
        verification_threshold=forwarding_threshold,
        threshold_source="MULTIVERIFIER_EXPERIMENT_S_V",
        network_context=charlie_network,
    )
    return {
        "format": "zaslon.qds.multiverifier.v1",
        "bundle_id": f"MV-{uuid.uuid4().hex.upper()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signer_id": "Alice",
        "document_name": filename,
        "document_hash": sha512_hex(document),
        "hash_algorithm": "SHA-512",
        "verifier_order": ["Bob", "Charlie"],
        "thresholds": {
            "s_a_authentication": authentication_threshold,
            "s_v_forwarded_verification": forwarding_threshold,
            "relation": "s_a < s_v",
            "claim": (
                "Experimental threshold structure; published QDS bounds are not "
                "automatically applicable to this construction."
            ),
        },
        "recipient_material": {
            "Bob": bob["signature"],
            "Charlie": charlie["signature"],
        },
        "independent_verifier_evidence": True,
        "shared_quantum_state_between_recipient_runs": False,
        "recipient_network_evidence": {
            "Bob": bob.get("network"),
            "Charlie": charlie.get("network"),
        },
        "construction_status": "EXPERIMENTAL_NOT_FORMALLY_PROVEN",
    }


def verify_multiverifier_bundle(
    *,
    document: bytes,
    bundle: dict[str, Any],
    verifier_id: VerifierId,
    forwarded_by: str | None = None,
    consume: bool = False,
) -> dict[str, Any]:
    if bundle.get("format") != "zaslon.qds.multiverifier.v1":
        raise ValueError("INVALID_MULTIVERIFIER_BUNDLE_FORMAT")
    if bundle.get("document_hash") != sha512_hex(document):
        raise ValueError("MULTIVERIFIER_DOCUMENT_HASH_MISMATCH")
    if verifier_id == "Charlie" and forwarded_by != "Bob":
        raise PermissionError("CHARLIE_FORWARDING_REQUIRES_AUTHENTICATED_BOB")
    material = bundle.get("recipient_material", {}).get(verifier_id)
    if not isinstance(material, dict):
        raise ValueError("MISSING_RECIPIENT_MATERIAL")
    result = verify_document(
        document=document,
        signature=material,
        consume=consume,
        authenticated_verifier_id=verifier_id,
    ).model_dump()
    return {
        "bundle_id": bundle["bundle_id"],
        "verifier_id": verifier_id,
        "verification_path": "DIRECT_RECIPIENT" if verifier_id == "Bob" else "FORWARDED_BY_BOB",
        "forwarded_by": forwarded_by,
        "result": result,
        "evidence_source": f"INDEPENDENT_{verifier_id.upper()}_EVIDENCE",
    }


def run_transferability_experiment(
    *,
    document: bytes,
    filename: str,
    trials: int,
    seed: int,
    scenario: Literal["HONEST", "SELECTIVE_CHARLIE_DISTURBANCE"] = "HONEST",
    authentication_threshold: float = 0.05,
    forwarding_threshold: float = 0.10,
    selective_charlie_measurement_error: float = 0.20,
) -> dict[str, Any]:
    if not 1 <= trials <= 100:
        raise ValueError("trials must be between 1 and 100")
    if not 0.0 <= selective_charlie_measurement_error <= 1.0:
        raise ValueError("selective_charlie_measurement_error must be in [0, 1]")
    bob_accepts = 0
    charlie_accepts = 0
    joint_accepts = 0
    transfer_failures = 0
    outcomes: list[dict[str, Any]] = []
    for trial in range(trials):
        trial_seed = derive_simulation_seed(seed, f"MULTIVERIFIER_TRIAL_{trial}")
        charlie_noise = (
            NoiseConfig(measurement_error=selective_charlie_measurement_error)
            if scenario == "SELECTIVE_CHARLIE_DISTURBANCE"
            else NoiseConfig()
        )
        bundle = create_multiverifier_bundle(
            document=document,
            filename=filename,
            seed=trial_seed,
            authentication_threshold=authentication_threshold,
            forwarding_threshold=forwarding_threshold,
            bob_noise=NoiseConfig(),
            charlie_noise=charlie_noise,
        )
        bob = verify_multiverifier_bundle(
            document=document,
            bundle=bundle,
            verifier_id="Bob",
            consume=False,
        )
        charlie = verify_multiverifier_bundle(
            document=document,
            bundle=bundle,
            verifier_id="Charlie",
            forwarded_by="Bob",
            consume=False,
        )
        bob_ok = bob["result"]["status"] == "VALID"
        charlie_ok = charlie["result"]["status"] == "VALID"
        bob_accepts += int(bob_ok)
        charlie_accepts += int(charlie_ok)
        joint_accepts += int(bob_ok and charlie_ok)
        transfer_failures += int(bob_ok and not charlie_ok)
        outcomes.append({
            "trial": trial,
            "bundle_id": bundle["bundle_id"],
            "bob_status": bob["result"]["status"],
            "bob_mismatch_rate": bob["result"]["mismatch_rate"],
            "charlie_status": charlie["result"]["status"],
            "charlie_mismatch_rate": charlie["result"]["mismatch_rate"],
            "bob_accepts_charlie_rejects": bob_ok and not charlie_ok,
        })
    return {
        "experiment": "MULTIVERIFIER_TRANSFERABILITY_AND_REPUDIATION",
        "scenario": scenario,
        "trials": trials,
        "thresholds": {
            "s_a": authentication_threshold,
            "s_v": forwarding_threshold,
            "relation": "s_a < s_v",
        },
        "counts": {
            "bob_accepts": bob_accepts,
            "charlie_accepts": charlie_accepts,
            "joint_accepts": joint_accepts,
            "bob_accepts_charlie_rejects": transfer_failures,
        },
        "metrics": {
            "legitimate_bob_acceptance_rate": bob_accepts / trials,
            "legitimate_charlie_acceptance_rate": charlie_accepts / trials,
            "joint_acceptance_rate": joint_accepts / trials,
            "p_transfer_failure_empirical": transfer_failures / trials,
            "p_transfer_failure_wilson_95": wilson_interval(transfer_failures, trials),
            "p_repudiation_empirical": transfer_failures / trials,
            "p_repudiation_wilson_95": wilson_interval(transfer_failures, trials),
        },
        "claim": "EMPIRICAL EXPERIMENT; NOT A FORMAL NON-REPUDIATION OR TRANSFERABILITY PROOF",
        "selective_disturbance_model": (
            None if scenario == "HONEST" else {
                "location": "CHARLIE_RECIPIENT_EVIDENCE_STREAM",
                "measurement_error_probability": selective_charlie_measurement_error,
                "interpretation": (
                    "Tests whether recipient-selective disturbance can produce Bob ACCEPT / "
                    "Charlie REJECT; it is not a complete malicious-signer strategy proof."
                ),
            }
        ),
        "outcomes": outcomes,
    }
