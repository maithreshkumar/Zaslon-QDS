from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import threading

from zaslon_shared.protocol import (
    create_qds_session,
    load_qds_session,
    verify_document,
)


def _create(document: bytes = b"strict signature") -> dict:
    return create_qds_session(
        document=document,
        filename="strict.bin",
        signer_id="Alice",
        verifier_id="Bob",
        seed=260840,
    )


def _replace_declarations(signature: dict, declarations: list[dict]) -> dict:
    candidate = deepcopy(signature)
    candidate["declarations"] = deepcopy(declarations)
    candidate["signature_declarations"] = deepcopy(declarations)
    return candidate


def _diagnostic_comparison_rows(created: dict, limit: int = 8) -> list[dict]:
    """Developer-only comparison; private verifier evidence never leaves tests."""

    row, _, evidence = load_qds_session(created["session"]["id"])
    candidates = {item["position"]: item for item in evidence["candidates"]}
    rows: list[dict] = []
    for declaration in created["signature"]["declarations"]:
        position = declaration["position"]
        digest_bit = declaration["digest_bit"]
        states = candidates[position]["values"][str(digest_bit)]
        for index, state in enumerate(states):
            expected = declaration["key_bits"][index]
            actual = state["bob_outcome"]
            rows.append(
                {
                    "position": position,
                    "digest_bit": digest_bit,
                    "selected_candidate": digest_bit,
                    "disclosed_key_bit": expected,
                    "disclosed_basis": declaration["bases"][index],
                    "stored_bob_outcome": actual,
                    "stored_bob_basis": state["basis"],
                    "usable": declaration["bases"][index] == state["basis"],
                    "expected_logical_result": expected,
                    "actual_comparison": "MATCH" if actual == expected else "MISMATCH",
                    "mismatch_reason": None if actual == expected else "BOB_OUTCOME_DIFFERS",
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def test_incomplete_malformed_and_tampered_signatures_fail_closed():
    created = _create()
    original = created["signature"]
    document = b"strict signature"

    mutations: list[tuple[str, dict, set[str]]] = []
    mutations.append(("empty", _replace_declarations(original, []), {"DECLARATION_COUNT_MISMATCH", "SERVER_ATTESTATION_FAILED"}))
    mutations.append(("one", _replace_declarations(original, original["declarations"][:1]), {"DECLARATION_COUNT_MISMATCH", "SERVER_ATTESTATION_FAILED"}))
    mutations.append(("missing", _replace_declarations(original, original["declarations"][:-1]), {"DECLARATION_COUNT_MISMATCH", "SERVER_ATTESTATION_FAILED"}))

    duplicate = deepcopy(original["declarations"])
    duplicate[1]["position"] = 0
    mutations.append(("duplicate", _replace_declarations(original, duplicate), {"DUPLICATE_DECLARATION_POSITION", "SERVER_ATTESTATION_FAILED"}))

    invalid_position = deepcopy(original)
    invalid_position["declarations"][0]["position"] = 512
    invalid_position["signature_declarations"][0]["position"] = 512
    mutations.append(("invalid position", invalid_position, {"MALFORMED_SIGNATURE_STRUCTURE"}))

    reordered = _replace_declarations(
        original, [original["declarations"][1], original["declarations"][0], *original["declarations"][2:]]
    )
    mutations.append(("reordered", reordered, {"NONCANONICAL_DECLARATION_POSITIONS", "SERVER_ATTESTATION_FAILED"}))

    wrong_digest = deepcopy(original["declarations"])
    wrong_digest[0]["digest_bit"] ^= 1
    mutations.append(("digest bit", _replace_declarations(original, wrong_digest), {"DECLARED_DIGEST_BIT_MISMATCH", "SERVER_ATTESTATION_FAILED"}))

    for field, code, replacement in (
        ("signature_id", "SIGNATURE_ID_MISMATCH", "SIG-tampered"),
        ("nonce", "NONCE_MISMATCH", "0" * 48),
        ("signer_id", "SIGNER_IDENTITY_MISMATCH", "Mallory"),
        ("verifier_id", "INTENDED_VERIFIER_MISMATCH", "Mallory"),
        ("algorithm", "ALGORITHM_MISMATCH", "NOT-ZASLON"),
    ):
        candidate = deepcopy(original)
        candidate[field] = replacement
        mutations.append((field, candidate, {code, "MALFORMED_SIGNATURE_STRUCTURE", "SERVER_ATTESTATION_FAILED"}))

    changed_session = deepcopy(original)
    changed_session["session_id"] = "QDS-does-not-exist"
    mutations.append(("session", changed_session, {"UNKNOWN_SESSION"}))

    coerced = deepcopy(original)
    coerced["declarations"][0]["position"] = "0"
    coerced["signature_declarations"][0]["position"] = "0"
    mutations.append(("type coercion", coerced, {"MALFORMED_SIGNATURE_STRUCTURE"}))

    extra_field = deepcopy(original)
    extra_field["trusted_override"] = True
    mutations.append(("unexpected field", extra_field, {"MALFORMED_SIGNATURE_STRUCTURE"}))

    invalid_state_label = deepcopy(original)
    invalid_state_label["declarations"][0]["key_bits"][0] = 2
    invalid_state_label["signature_declarations"][0]["key_bits"][0] = 2
    mutations.append(("state label", invalid_state_label, {"MALFORMED_SIGNATURE_STRUCTURE"}))

    for label, signature, expected_codes in mutations:
        result = verify_document(
            document=document,
            signature=signature,
            consume=False,
            authenticated_verifier_id="Bob",
        )
        assert result.status == "INVALID", label
        assert result.failure_code in expected_codes, label
        assert result.usable_measurements == 0, label


def test_declarations_mixed_from_another_session_are_rejected():
    first = _create(b"same document")
    second = create_qds_session(
        document=b"same document",
        filename="second.bin",
        signer_id="Alice",
        verifier_id="Bob",
        seed=260841,
    )
    mixed = deepcopy(first["signature"])
    mixed["declarations"][100:200] = deepcopy(second["signature"]["declarations"][100:200])
    mixed["signature_declarations"] = deepcopy(mixed["declarations"])

    result = verify_document(
        document=b"same document",
        signature=mixed,
        consume=False,
        authenticated_verifier_id="Bob",
    )

    assert result.status == "INVALID"
    assert result.failure_code == "SERVER_ATTESTATION_FAILED"


def test_artifact_attestation_key_identifier_must_match_active_server_key():
    created = _create(b"attestation key identity")
    signature = deepcopy(created["signature"])
    signature["server_attestation"]["key_id"] = "local-attestation-deadbeefdeadbeef"

    result = verify_document(
        document=b"attestation key identity",
        signature=signature,
        consume=False,
        authenticated_verifier_id="Bob",
    )

    assert result.status == "INVALID"
    assert result.failure_code == "SERVER_ATTESTATION_FAILED"


def test_only_the_intended_authenticated_verifier_is_accepted():
    created = _create()

    unauthorized = verify_document(
        document=b"strict signature",
        signature=created["signature"],
        consume=False,
        authenticated_verifier_id="Alice",
    )
    unknown = verify_document(
        document=b"strict signature",
        signature=created["signature"],
        consume=False,
        authenticated_verifier_id="Mallory",
    )
    authorized = verify_document(
        document=b"strict signature",
        signature=created["signature"],
        consume=False,
        authenticated_verifier_id="Bob",
    )

    assert unauthorized.failure_code == "UNAUTHORIZED_VERIFIER"
    assert unknown.failure_code == "UNAUTHORIZED_VERIFIER"
    assert authorized.status == "VALID"
    assert authorized.authenticated_verifier == "Bob"


def test_atomic_replay_consumption_allows_exactly_one_concurrent_acceptance():
    created = _create(b"atomic replay")
    signature = json.loads(json.dumps(created["signature"]))
    barrier = threading.Barrier(2)

    def verify_once():
        barrier.wait(timeout=5)
        return verify_document(
            document=b"atomic replay",
            signature=deepcopy(signature),
            consume=True,
            authenticated_verifier_id="Bob",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: verify_once(), range(2)))

    assert [result.status for result in results].count("VALID") == 1
    rejected = [result for result in results if result.status == "INVALID"]
    assert len(rejected) == 1
    assert rejected[0].failure_code == "REPLAY_REJECTED"
    assert rejected[0].replay_detected is True


def test_ten_honest_sign_verify_cycles_and_strict_negative_controls():
    document = b"deterministic honest sign verify regression\n"
    honest_results = []
    for cycle in range(10):
        created = create_qds_session(
            document=document,
            filename="honest-regression.txt",
            signer_id="Alice",
            verifier_id="Bob",
            seed=261500 + cycle,
        )
        signature = deepcopy(created["signature"])

        if cycle == 0:
            rows = _diagnostic_comparison_rows(created)
            assert all(row["usable"] for row in rows), rows
            assert all(row["actual_comparison"] == "MATCH" for row in rows), rows

            modified = verify_document(
                document=document + b"!",
                signature=signature,
                consume=True,
                authenticated_verifier_id="Bob",
            )
            assert modified.failure_code == "DOCUMENT_HASH_MISMATCH"

            tampered = json.loads(json.dumps(signature))
            tampered["declarations"][0]["key_bits"][0] ^= 1
            assert verify_document(
                document=document,
                signature=tampered,
                consume=True,
                authenticated_verifier_id="Bob",
            ).failure_code == "SERVER_ATTESTATION_FAILED"

            wrong_signature_id = deepcopy(signature)
            wrong_signature_id["signature_id"] = "SIG-WRONG"
            assert verify_document(
                document=document,
                signature=wrong_signature_id,
                consume=True,
                authenticated_verifier_id="Bob",
            ).failure_code == "SERVER_ATTESTATION_FAILED"

            missing_session = deepcopy(signature)
            missing_session["session_id"] = "QDS-MISSING-TRUSTED-SESSION"
            assert verify_document(
                document=document,
                signature=missing_session,
                consume=True,
                authenticated_verifier_id="Bob",
            ).failure_code == "UNKNOWN_SESSION"

        verified = verify_document(
            document=document,
            signature=signature,
            consume=True,
            authenticated_verifier_id="Bob",
        )
        honest_results.append(verified)
        assert verified.status == "VALID"
        assert verified.mismatch_rate == 0.0
        assert verified.usable_measurements == 2048
        assert verified.threshold == 0.05

        replay = verify_document(
            document=document,
            signature=signature,
            consume=True,
            authenticated_verifier_id="Bob",
        )
        assert replay.status == "INVALID"
        assert replay.failure_code == "REPLAY_REJECTED"

    assert len(honest_results) == 10
