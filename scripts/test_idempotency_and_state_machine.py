"""
Zaslon-QDS — Workflow Idempotency, One-Time Actions, and State Machine Test Suite.
Tests:
1. Alice Sign-Once & Send-Once (idempotent /sign and /dispatch).
2. Eve One-Time Attack & State Machine (single intercept, single mutate, single forward, HTTP 409 on duplicates).
3. Bob Exactly-Once Verification per transmission_id (reopening returns stored verdict, does NOT trigger replay).
4. Distinguishing Legitimate Reopen vs Genuine Replay (T1 stays VERIFIED, T2 with consumed token gets REJECTED as REPLAY).
5. Concurrent Verification Safety (row-locking ensures exactly 1 verification record per transmission_id).
"""
import urllib.request
import urllib.error
import json
import time
import sys
import threading

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000/api/v1"


def http_post_json(endpoint: str, data: dict = None, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data or {}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw_error": body}


def http_get_json(endpoint: str, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw_error": body}


def get_tokens():
    http_post_json("/auth/seed-demo-users", {})
    _, a = http_post_json("/auth/login", {"username": "alice", "password": "zaslon2026"})
    _, e = http_post_json("/auth/login", {"username": "eve", "password": "zaslon2026"})
    _, b = http_post_json("/auth/login", {"username": "bob", "password": "zaslon2026"})
    return a["access_token"], e["access_token"], b["access_token"]


def run_tests():
    print("=" * 75)
    print("ZASLON-QDS: WORKFLOW IDEMPOTENCY & STATE MACHINE TEST SUITE")
    print("=" * 75)

    alice_tok, eve_tok, bob_tok = get_tokens()

    passed_tests = 0
    total_tests = 0

    # -------------------------------------------------------------
    # TEST 1: Alice Sign-Once & Send-Once Idempotency
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[TEST 1] Alice Sign-Once & Send-Once Idempotency")
    st, draft = http_post_json("/alice/draft", {
        "document_title": "Idempotency Directive #001",
        "message_payload": "TOP SECRET MILITARY SATELLITE KEY SCHEDULE 2026",
        "recipient_id": "bob"
    }, alice_tok)
    assert st == 200, f"Draft creation failed: {draft}"
    sess_id = draft["session_id"]

    # First Sign
    t0 = time.time()
    st1, sign1 = http_post_json(f"/alice/sessions/{sess_id}/sign", {}, alice_tok)
    dur1 = time.time() - t0
    assert st1 == 200, f"First sign failed: {sign1}"
    assert sign1["total_operations"] == 4096

    # Second Sign (Must be instantaneous, return existing without re-running CUDA-Q)
    t0 = time.time()
    st2, sign2 = http_post_json(f"/alice/sessions/{sess_id}/sign", {}, alice_tok)
    dur2 = time.time() - t0
    assert st2 == 200, f"Second sign failed: {sign2}"
    assert sign2["signature_token"] == sign1["signature_token"], "Signature token mismatch!"
    assert dur2 < 1.0, f"Second sign took too long ({dur2:.2f}s); expected cached return (<1s)"
    print(f"  [PASS] Sign-Once: 1st took {dur1:.2f}s, 2nd returned cached in {dur2:.4f}s")

    # First Dispatch
    st_d1, pkg1 = http_post_json(f"/alice/packages/{sess_id}/dispatch", {}, alice_tok)
    assert st_d1 == 200, f"First dispatch failed: {pkg1}"
    assert pkg1["status"] == "IN_TRANSIT"

    # Second Dispatch (Idempotent, returns existing package without resetting downstream state)
    st_d2, pkg2 = http_post_json(f"/alice/packages/{sess_id}/dispatch", {}, alice_tok)
    assert st_d2 == 200, f"Second dispatch failed: {pkg2}"
    assert pkg2["id"] == pkg1["id"]
    print(f"  [PASS] Send-Once: Package #{pkg1['package_tracking_no']} returned identically")
    passed_tests += 1

    # -------------------------------------------------------------
    # TEST 2: Eve One-Time Actions & State Machine HTTP 409
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[TEST 2] Eve One-Time Actions & State Machine (HTTP 409 on duplicates)")
    trans_id = pkg1["id"]

    # Intercept
    st_i1, _ = http_post_json(f"/eve/intercept/{trans_id}", {}, eve_tok)
    assert st_i1 == 200, f"Intercept failed: {st_i1}"

    # Intercept again -> Must 409
    st_i2, err_i2 = http_post_json(f"/eve/intercept/{trans_id}", {}, eve_tok)
    assert st_i2 == 409, f"Expected 409 on duplicate intercept, got {st_i2}: {err_i2}"
    print("  [PASS] Duplicate intercept returned HTTP 409 Conflict")

    # Mutate with FILE_INTEGRITY_TAMPERING
    st_m1, mut1 = http_post_json(f"/eve/mutate/{trans_id}", {
        "attack_type": "FILE_INTEGRITY_TAMPERING",
        "mutation_params": {"tampered_message": "TAMPERED PAYLOAD"}
    }, eve_tok)
    assert st_m1 == 200, f"First mutate failed: {mut1}"
    assert mut1["status"] == "MODIFIED"
    assert mut1["is_tampered"] is True

    # Mutate again -> Must 409
    st_m2, err_m2 = http_post_json(f"/eve/mutate/{trans_id}", {
        "attack_type": "FORGERY",
        "mutation_params": {"affected_count": 300}
    }, eve_tok)
    assert st_m2 == 409, f"Expected 409 on duplicate attack, got {st_m2}: {err_m2}"
    print("  [PASS] Duplicate attack mutation returned HTTP 409 Conflict")

    # Passthrough after mutate -> Must 409
    st_p, err_p = http_post_json(f"/eve/passthrough/{trans_id}", {}, eve_tok)
    assert st_p == 409, f"Expected 409 on passthrough of mutated package, got {st_p}: {err_p}"
    print("  [PASS] Passthrough on mutated package returned HTTP 409 Conflict")

    # Forward
    st_f1, fwd1 = http_post_json(f"/eve/forward/{trans_id}", {}, eve_tok)
    assert st_f1 == 200, f"Forward failed: {fwd1}"
    assert fwd1["status"] == "RECEIVED"

    # Forward again -> Must 409
    st_f2, err_f2 = http_post_json(f"/eve/forward/{trans_id}", {}, eve_tok)
    assert st_f2 == 409, f"Expected 409 on duplicate forward, got {st_f2}: {err_f2}"
    print("  [PASS] Duplicate forward returned HTTP 409 Conflict")

    # Mutate after forward -> Must 409
    st_m3, err_m3 = http_post_json(f"/eve/mutate/{trans_id}", {
        "attack_type": "FORGERY",
        "mutation_params": {"affected_count": 300}
    }, eve_tok)
    assert st_m3 == 409, f"Expected 409 on mutate after forward, got {st_m3}: {err_m3}"
    print("  [PASS] Mutation on forwarded package returned HTTP 409 Conflict")
    passed_tests += 1

    # -------------------------------------------------------------
    # TEST 3: Bob Verification Idempotency (Reopen vs Reverification)
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[TEST 3] Bob Verification Idempotency (transmission_id boundary)")
    # Create authentic package T_auth
    st_a, d_auth = http_post_json("/alice/draft", {
        "document_title": "Authentic Package T_auth",
        "message_payload": "AUTHENTIC TRANSMISSION #777 FOR BOB",
        "recipient_id": "bob"
    }, alice_tok)
    s_auth = d_auth["session_id"]
    http_post_json(f"/alice/sessions/{s_auth}/sign", {}, alice_tok)
    _, p_auth = http_post_json(f"/alice/packages/{s_auth}/dispatch", {}, alice_tok)
    t_auth_id = p_auth["id"]

    # Passthrough via Eve
    http_post_json(f"/eve/intercept/{t_auth_id}", {}, eve_tok)
    http_post_json(f"/eve/passthrough/{t_auth_id}", {}, eve_tok)

    # Bob verifies T_auth first time
    st_v1, v1 = http_post_json(f"/bob/inbox/{t_auth_id}/verify", {"sample_ratio": 0.05}, bob_tok)
    assert st_v1 == 200, f"Initial verification failed: {v1}"
    assert v1["security_decision"] == "VERIFIED", f"Expected VERIFIED, got {v1['security_decision']}"
    assert v1["attack_detected"] is False
    assert v1["transmission_id"] == t_auth_id
    verif_id = v1["id"]
    print(f"  [PASS] First verification of T_auth succeeded: {v1['security_decision']}")

    # Check UI rehydration endpoint GET /bob/inbox/{t_auth_id}/verification
    st_inbox_v, inbox_v = http_get_json(f"/bob/inbox/{t_auth_id}/verification", bob_tok)
    assert st_inbox_v == 200
    assert inbox_v["has_verification"] is True
    assert inbox_v["verification_id"] == verif_id
    assert inbox_v["evidence"]["security_decision"] == "VERIFIED"
    print("  [PASS] GET /bob/inbox/{id}/verification returned stored evidence for UI rehydration")

    # Bob reopens / verifies T_auth a second time (Reopen)
    # Must NOT re-verify, must NOT trigger REPLAY attack!
    st_v2, v2 = http_post_json(f"/bob/inbox/{t_auth_id}/verify", {"sample_ratio": 0.05}, bob_tok)
    assert st_v2 == 200, f"Second verification call failed: {v2}"
    assert v2["id"] == verif_id, "Verification ID changed! A new verification was created instead of returning stored!"
    assert v2["security_decision"] == "VERIFIED", f"Expected VERIFIED on reopen, but got {v2['security_decision']}! (Did it trigger REPLAY?)"
    assert v2["attack_detected"] is False
    print("  [PASS] Reopening T_auth returned existing stored verdict: VERIFIED (Did NOT trigger replay)")
    passed_tests += 1

    # -------------------------------------------------------------
    # TEST 4: Distinguishing Reopen vs Genuine Replay in New Transmission
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[TEST 4] Distinguishing Legitimate Reopen vs Genuine Replay (T2)")
    # Alice creates a second package T2
    st_r, d_r = http_post_json("/alice/draft", {
        "document_title": "Package T2 (Replay Target)",
        "message_payload": "AUTHENTIC TRANSMISSION T2",
        "recipient_id": "bob"
    }, alice_tok)
    s_r = d_r["session_id"]
    http_post_json(f"/alice/sessions/{s_r}/sign", {}, alice_tok)
    _, p_r = http_post_json(f"/alice/packages/{s_r}/dispatch", {}, alice_tok)
    t_replay_id = p_r["id"]

    # Eve intercepts T2 and injects REPLAY attack (substituting already-consumed declaration token from T_auth)
    http_post_json(f"/eve/intercept/{t_replay_id}", {}, eve_tok)
    st_rep, mut_rep = http_post_json(f"/eve/mutate/{t_replay_id}", {
        "attack_type": "REPLAY",
        "mutation_params": {}
    }, eve_tok)
    assert st_rep == 200, f"Replay mutation failed: {mut_rep}"

    # Forward T2 to Bob
    http_post_json(f"/eve/forward/{t_replay_id}", {}, eve_tok)

    # Bob verifies T2
    st_vr, vr = http_post_json(f"/bob/inbox/{t_replay_id}/verify", {"sample_ratio": 0.05}, bob_tok)
    assert st_vr == 200, f"Verification of T2 failed: {vr}"
    assert vr["security_decision"] == "REJECTED", f"Expected REJECTED for Replay attack, got {vr['security_decision']}"
    assert vr["attack_detected"] is True
    assert vr["attack_category"] == "REPLAY"
    assert vr["transmission_id"] == t_replay_id
    print(f"  [PASS] Genuine Replay on T2 properly rejected: {vr['security_decision']} ({vr['attack_category']})")

    # Now verify that original T_auth is STILL VERIFIED (untouched)!
    st_check, v_check = http_get_json(f"/bob/inbox/{t_auth_id}/verification", bob_tok)
    assert st_check == 200
    assert v_check["has_verification"] is True
    assert v_check["evidence"]["security_decision"] == "VERIFIED", "Original T_auth verdict was mutated!"
    print("  [PASS] Original T_auth remains strictly VERIFIED; T2 remains REJECTED. Boundary verified.")
    passed_tests += 1

    # -------------------------------------------------------------
    # TEST 5: Concurrent Verification Safety
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[TEST 5] Concurrent Verification Safety (row-locking test)")
    st_c, d_c = http_post_json("/alice/draft", {
        "document_title": "Concurrency Test Directive",
        "message_payload": "PARALLEL CONCURRENT VERIFICATION SAFETY",
        "recipient_id": "bob"
    }, alice_tok)
    s_c = d_c["session_id"]
    http_post_json(f"/alice/sessions/{s_c}/sign", {}, alice_tok)
    _, p_c = http_post_json(f"/alice/packages/{s_c}/dispatch", {}, alice_tok)
    t_concur_id = p_c["id"]
    http_post_json(f"/eve/intercept/{t_concur_id}", {}, eve_tok)
    http_post_json(f"/eve/passthrough/{t_concur_id}", {}, eve_tok)

    results = []
    errors = []

    def verify_worker():
        try:
            st, res = http_post_json(f"/bob/inbox/{t_concur_id}/verify", {"sample_ratio": 0.05}, bob_tok)
            if st == 200:
                results.append(res)
            else:
                errors.append((st, res))
        except Exception as ex:
            errors.append(str(ex))

    t1 = threading.Thread(target=verify_worker)
    t2 = threading.Thread(target=verify_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(errors) == 0, f"Errors in concurrent verification: {errors}"
    assert len(results) == 2, f"Expected 2 successful responses, got {len(results)}"
    assert results[0]["id"] == results[1]["id"], f"Race condition! Two different verification IDs created: {results[0]['id']} vs {results[1]['id']}"
    print(f"  [PASS] Concurrent verification safety passed: Both requests resolved to single record #{results[0]['id'][:8]}")
    passed_tests += 1

    print("\n" + "=" * 75)
    print(f"IDEMPOTENCY & STATE MACHINE TEST RESULTS: {passed_tests}/{total_tests} SUITES PASSED")
    print("=" * 75)


if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
