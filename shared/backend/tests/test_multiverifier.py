import pytest

from zaslon_shared.multiverifier import (
    create_multiverifier_bundle,
    run_transferability_experiment,
    verify_multiverifier_bundle,
)


def test_bob_and_charlie_have_independent_verifier_material() -> None:
    bundle = create_multiverifier_bundle(
        document=b"transferable message",
        filename="message.bin",
        seed=261000,
    )
    bob = bundle["recipient_material"]["Bob"]
    charlie = bundle["recipient_material"]["Charlie"]
    assert bob["session_id"] != charlie["session_id"]
    assert bob["signature_id"] != charlie["signature_id"]
    assert bob["verifier_id"] == "Bob"
    assert charlie["verifier_id"] == "Charlie"
    assert bob["declarations"] != charlie["declarations"]
    assert bundle["thresholds"]["s_a_authentication"] < bundle["thresholds"]["s_v_forwarded_verification"]


def test_honest_direct_and_forwarded_verification_are_independent_and_valid() -> None:
    document = b"honest transfer"
    bundle = create_multiverifier_bundle(
        document=document,
        filename="honest.bin",
        seed=261001,
    )
    bob = verify_multiverifier_bundle(
        document=document, bundle=bundle, verifier_id="Bob"
    )
    charlie = verify_multiverifier_bundle(
        document=document,
        bundle=bundle,
        verifier_id="Charlie",
        forwarded_by="Bob",
    )
    assert bob["result"]["status"] == "VALID"
    assert charlie["result"]["status"] == "VALID"
    assert bob["evidence_source"] != charlie["evidence_source"]


def test_charlie_requires_authenticated_bob_forwarding_path() -> None:
    document = b"forward authorization"
    bundle = create_multiverifier_bundle(
        document=document,
        filename="forward.bin",
        seed=261002,
    )
    with pytest.raises(PermissionError, match="CHARLIE_FORWARDING_REQUIRES_AUTHENTICATED_BOB"):
        verify_multiverifier_bundle(
            document=document,
            bundle=bundle,
            verifier_id="Charlie",
            forwarded_by="Mallory",
        )


def test_honest_transferability_metrics_and_selective_repudiation_case() -> None:
    honest = run_transferability_experiment(
        document=b"multi trial",
        filename="trials.bin",
        trials=2,
        seed=261003,
        scenario="HONEST",
    )
    assert honest["metrics"]["p_transfer_failure_empirical"] == 0.0
    assert honest["metrics"]["joint_acceptance_rate"] == 1.0

    selective = run_transferability_experiment(
        document=b"multi trial",
        filename="trials.bin",
        trials=2,
        seed=261004,
        scenario="SELECTIVE_CHARLIE_DISTURBANCE",
        selective_charlie_measurement_error=1.0,
    )
    assert selective["metrics"]["p_repudiation_empirical"] == 1.0
    assert selective["counts"]["bob_accepts_charlie_rejects"] == 2
    assert "NOT A FORMAL" in selective["claim"]

