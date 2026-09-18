"""
Zaslon-QDS Authentic Multi-Actor Role Workflow E2E Script.
Validates:
1. Alice Signer -> Eve Interceptor (Passthrough) -> Bob Verifier (VERIFIED)
2. Alice Signer -> Eve Forgery -> Bob Verifier (REJECTED / FORGERY)
3. Alice Signer -> Eve Impersonation -> Bob Verifier (REJECTED / IMPERSONATION)
4. Alice Signer -> Eve Replay -> Bob Verifier (REJECTED / REPLAY)
5. Alice Signer -> Eve Unauthorized Probe -> Blocked by RBAC (UNAUTHORIZED)
6. Alice Signer -> Eve Integrity Tampering -> Bob Verifier (INTEGRITY_FAILURE)
"""
import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://localhost:8000/api/v1"


def http_post(endpoint: str, data: dict, token: str = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get(endpoint: str, token: str = None) -> any:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_tests():
    print("=" * 80)
    print("   ZASLON-QDS: ROLE-BASED APPLICATION WORKFLOW (ALICE -> EVE -> BOB)   ")
    print("=" * 80)

    # 1. Seed demo users and login
    print("\n[1/7] Seeding demo users and authenticating roles...")
    seed_res = http_post("/auth/seed-demo-users", {})
    print(f"      Seeded {seed_res['seeded_count']} demo accounts.")

    alice_login = http_post("/auth/login", {"username": "alice", "password": "zaslon2026"})
    eve_login = http_post("/auth/login", {"username": "eve", "password": "zaslon2026"})
    bob_login = http_post("/auth/login", {"username": "bob", "password": "zaslon2026"})

    alice_token = alice_login["access_token"]
    eve_token = eve_login["access_token"]
    bob_token = bob_login["access_token"]
    print("      Alice, Eve, and Bob authenticated successfully with JWT tokens.")

    # 2. Test 1: Authentic Passthrough (No Attack) -> VERIFIED
    print("\n[2/7] TEST 1: Authentic Passthrough (Alice Signs -> Eve Passthrough -> Bob Verifies)...")
    draft1 = http_post("/alice/draft", {
        "document_title": "DEFENSE DIRECTIVE #001: GRID TELEMETRY",
        "message_payload": "AUTHENTIC QUANTUM TELEMETRY PACKET FOR BRANCH POWER CONTROL",
        "recipient_id": "bob"
    }, token=alice_token)
    session1_id = draft1["session_id"]
    print(f"      Alice created draft session {session1_id} with SHA-512 digest: {draft1['sha512_digest'][:16]}...")

    sign1 = http_post(f"/alice/sessions/{session1_id}/sign", {}, token=alice_token)
    print(f"      Alice executed 4,096 CUDA-Q circuits in {sign1['duration_ms']:.1f}ms. Token: {sign1['signature_token'][:20]}...")

    pkg1 = http_post(f"/alice/packages/{session1_id}/dispatch", {}, token=alice_token)
    pkg1_id = pkg1["id"]
    print(f"      Alice dispatched package {pkg1['package_tracking_no']} (Status: {pkg1['status']})")

    # Eve intercepts and passes through untouched
    intercept1 = http_post(f"/eve/intercept/{pkg1_id}", {}, token=eve_token)
    print(f"      Eve intercepted package (Status: {intercept1['status']})")

    pass1 = http_post(f"/eve/passthrough/{pkg1_id}", {}, token=eve_token)
    print(f"      Eve marked package as PASSTHROUGH (untouched).")

    fwd1 = http_post(f"/eve/forward/{pkg1_id}", {}, token=eve_token)
    print(f"      Eve forwarded package to Bob (Status: {fwd1['status']})")

    # Bob verifies
    bob_inbox = http_get("/bob/inbox", token=bob_token)
    assert any(p["id"] == pkg1_id for p in bob_inbox), "Package not found in Bob's inbox!"
    print(f"      Bob sees package in inbox ({len(bob_inbox)} total packages).")

    verify1 = http_post(f"/bob/inbox/{pkg1_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Bob Verification Verdict: {verify1['security_decision']} (Fisher p={verify1['fisher_p_value']}, Mismatch: {verify1['mismatch_ratio']:.2%})")
    assert verify1["security_decision"] == "VERIFIED", f"Expected VERIFIED but got {verify1['security_decision']}"
    print("      >>> TEST 1 RESULT: PASS (100% Authentic Verification)")

    # 3. Test 2: Forgery Attack
    print("\n[3/7] TEST 2: Quantum Forgery Attack (Invert Measurement Bits)...")
    draft2 = http_post("/alice/draft", {
        "document_title": "DEFENSE DIRECTIVE #002: CLASSIFIED DISPATCH",
        "message_payload": "TRANSMISSION TARGETED FOR QUANTUM MEASUREMENT FORGERY",
        "recipient_id": "bob"
    }, token=alice_token)
    session2_id = draft2["session_id"]
    http_post(f"/alice/sessions/{session2_id}/sign", {}, token=alice_token)
    pkg2 = http_post(f"/alice/packages/{session2_id}/dispatch", {}, token=alice_token)
    pkg2_id = pkg2["id"]

    http_post(f"/eve/intercept/{pkg2_id}", {}, token=eve_token)
    http_post(f"/eve/mutate/{pkg2_id}", {
        "attack_type": "FORGERY",
        "mutation_params": {"affected_measurements_count": 600}
    }, token=eve_token)
    http_post(f"/eve/forward/{pkg2_id}", {}, token=eve_token)

    verify2 = http_post(f"/bob/inbox/{pkg2_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Bob Verification Verdict: {verify2['security_decision']} (Threat: {verify2['attack_category']}, Mismatch: {verify2['mismatch_ratio']:.2%})")
    assert verify2["security_decision"] == "REJECTED" and ("FORGERY" in verify2["attack_category"])
    print("      >>> TEST 2 RESULT: PASS (Forgery Intercepted by Fisher Test)")

    # 4. Test 3: Signer Impersonation Attack
    print("\n[4/7] TEST 3: Signer Impersonation Attack...")
    draft3 = http_post("/alice/draft", {
        "document_title": "DEFENSE DIRECTIVE #003: FUNDS TRANSFER",
        "message_payload": "TRANSFER $10,000,000 FROM STRATEGIC RESERVE",
        "recipient_id": "bob"
    }, token=alice_token)
    session3_id = draft3["session_id"]
    http_post(f"/alice/sessions/{session3_id}/sign", {}, token=alice_token)
    pkg3 = http_post(f"/alice/packages/{session3_id}/dispatch", {}, token=alice_token)
    pkg3_id = pkg3["id"]

    http_post(f"/eve/intercept/{pkg3_id}", {}, token=eve_token)
    http_post(f"/eve/mutate/{pkg3_id}", {
        "attack_type": "IMPERSONATION",
        "mutation_params": {"spoofed_signer": "Eve_Impersonator"}
    }, token=eve_token)
    http_post(f"/eve/forward/{pkg3_id}", {}, token=eve_token)

    verify3 = http_post(f"/bob/inbox/{pkg3_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Bob Verification Verdict: {verify3['security_decision']} (Threat: {verify3['attack_category']})")
    assert verify3["security_decision"] == "REJECTED" and ("IMPERSONATION" in verify3["attack_category"])
    print("      >>> TEST 3 RESULT: PASS (Impersonation Detected)")

    # 5. Test 4: Replay Attack (Resubmit Consumed Token)
    print("\n[5/7] TEST 4: Signature Replay Attack...")
    draft4 = http_post("/alice/draft", {
        "document_title": "DEFENSE DIRECTIVE #004: ONE-TIME LAUNCH CODE",
        "message_payload": "SINGLE-USE CIPHER NONCE 9823472039",
        "recipient_id": "bob"
    }, token=alice_token)
    session4_id = draft4["session_id"]
    http_post(f"/alice/sessions/{session4_id}/sign", {}, token=alice_token)
    pkg4 = http_post(f"/alice/packages/{session4_id}/dispatch", {}, token=alice_token)
    pkg4_id = pkg4["id"]

    http_post(f"/eve/intercept/{pkg4_id}", {}, token=eve_token)
    http_post(f"/eve/mutate/{pkg4_id}", {
        "attack_type": "REPLAY",
        "mutation_params": {"replayed_token": "sig_qds_replayed_stale_token"}
    }, token=eve_token)
    http_post(f"/eve/forward/{pkg4_id}", {}, token=eve_token)

    verify4 = http_post(f"/bob/inbox/{pkg4_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Bob Verification Verdict: {verify4['security_decision']} (Threat: {verify4['attack_category']})")
    assert verify4["security_decision"] == "REJECTED" and ("REPLAY" in verify4["attack_category"])
    print("      >>> TEST 4 RESULT: PASS (Replay Attack Detected)")

    # 6. Test 5: Unauthorized Verification Probe
    print("\n[6/7] TEST 5: Unauthorized Verification Probe by Eve...")
    probe_res = http_post(f"/eve/probe-verify/{pkg1_id}", {}, token=eve_token)
    print(f"      Eve Probe Verdict: {probe_res['security_verdict']} (Barrier: {probe_res['barrier_triggered']})")
    assert probe_res["security_verdict"] == "UNAUTHORIZED"
    print("      >>> TEST 5 RESULT: PASS (Unauthorized Verification Intercepted)")

    # 7. Test 6: Plaintext Integrity Tampering
    print("\n[7/7] TEST 6: Plaintext Message Integrity Tampering...")
    draft6 = http_post("/alice/draft", {
        "document_title": "DEFENSE DIRECTIVE #006: PAYLOAD TAMPERING",
        "message_payload": "AUTHORIZE AIRLIFT FLIGHT 409 TO BASE CHARLIE",
        "recipient_id": "bob"
    }, token=alice_token)
    session6_id = draft6["session_id"]
    http_post(f"/alice/sessions/{session6_id}/sign", {}, token=alice_token)
    pkg6 = http_post(f"/alice/packages/{session6_id}/dispatch", {}, token=alice_token)
    pkg6_id = pkg6["id"]

    http_post(f"/eve/intercept/{pkg6_id}", {}, token=eve_token)
    http_post(f"/eve/mutate/{pkg6_id}", {
        "attack_type": "INTEGRITY_TAMPERING",
        "mutation_params": {"tampered_message": "AUTHORIZE AIRLIFT FLIGHT 409 TO HOSTILE SECTOR"}
    }, token=eve_token)
    http_post(f"/eve/forward/{pkg6_id}", {}, token=eve_token)

    verify6 = http_post(f"/bob/inbox/{pkg6_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Bob Verification Verdict: {verify6['security_decision']} (Threat: {verify6['attack_category']})")
    assert verify6["security_decision"] == "INTEGRITY_FAILURE" and ("INTEGRITY" in verify6["attack_category"] or "TAMPERING" in verify6["attack_category"] or "SUBSTITUTION" in verify6["attack_category"])
    print("      >>> TEST 6 RESULT: PASS (Integrity Tampering Intercepted)")

    print("\n" + "=" * 80)
    print(">>> SUCCESS: ALL MULTI-ACTOR WORKFLOWS & ATTACKS 100% PROVEN! <<<")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_tests()
