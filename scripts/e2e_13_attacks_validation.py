"""
Zaslon-QDS — Comprehensive 13-Attack Threat Catalog Validation (SIH 26141).
Validates 14 distinct scenarios on the live running stack:
0. Authentic Baseline (Alice signs -> Passthrough -> Bob verifies -> VERIFIED, 100% fidelity)
1. IMPERSONATION (Signer identity spoofing -> Barrier 2 -> REJECTED)
2. UNAUTHORIZED_VERIFICATION (Non-designated verifier -> Barrier 1 -> UNAUTHORIZED)
3. UNAUTHORIZED_PROBE (Adversary probes Bob resources -> HTTP 403 -> SecurityEvent logged)
4. FILE_INTEGRITY_TAMPERING (Payload modified post-hash -> Barrier 4 -> INTEGRITY_FAILURE)
5. DECLARATION_TAMPERING (Public declaration hash altered -> Barrier 3 -> INTEGRITY_FAILURE)
6. QDS_PACKAGE_TAMPERING (Manifest committed digest forged -> Barrier 4 -> INTEGRITY_FAILURE)
7. FORGERY (Synthesized token & bit-flip -> Barrier 5 -> REJECTED)
8. REPLAY (Single-use token re-executed -> Barrier 3 -> REJECTED)
9. INTERCEPT_AND_RESEND (State reconstruction collapse -> Barrier 5 -> REJECTED)
10. SESSION_SUBSTITUTION (Foreign token grafted -> Barrier 3 -> REJECTED)
11. MEASUREMENT_MANIPULATION (Pauli-X bit-flips on Bob qubits -> Barrier 5 -> REJECTED)
12. BASIS_MANIPULATION (Conjugate basis alteration -> Barrier 5 -> REJECTED)
13. QUANTUM_STATE_REPLACEMENT (Phase-damping/depolarization -> Barrier 5 -> REJECTED)
"""
import urllib.request
import urllib.error
import json
import time
import sys
import uuid

BASE_URL = "http://localhost:8000/api/v1"

FILE_SAMPLES = [
    ("defense_directive_26141.pdf", b"%PDF-1.4\n1 0 obj<< /Title (Zaslon Strategic Directive #26141) >>endobj\ntrailer<< /Root 1 0 R >>\n%%EOF", "application/pdf"),
    ("classified_payload.bin", b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x3e\x00\x01\x00\x00\x00\x00\x10\x40\x00\x00\x00\x00\x00", "application/octet-stream"),
    ("telemetry_matrix.txt", b"ZASLON-QDS CANONICAL AUTHENTICATION TOKEN STREAM 2026\nSTATION: DEFENSE-OPS\nVERIFIER: BOB-ALPHA\n", "text/plain"),
    ("satellite_recon.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82", "image/png"),
]

file_index = 0


def http_post_json(endpoint: str, data: dict, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
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


def http_upload_file(endpoint: str, filename: str, file_bytes: bytes, mime_type: str, document_title: str, recipient_id: str, token: str = None) -> tuple[int, dict]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()
    
    # document_title field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="document_title"\r\n\r\n')
    body.extend(f"{document_title}\r\n".encode())
    
    # recipient_id field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="recipient_id"\r\n\r\n')
    body.extend(f"{recipient_id}\r\n".encode())
    
    # file field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body.extend(file_bytes)
    body.extend(b"\r\n")
    
    # closing boundary
    body.extend(f"--{boundary}--\r\n".encode())
    
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body_err)
        except Exception:
            return e.code, {"raw_error": body_err}


def provision_signed_package(alice_token: str, title: str) -> dict:
    """Helper: Alice uploads real file, executes CUDA-Q 4,096 teleportation circuits, and dispatches package."""
    global file_index
    fname, fbytes, ftype = FILE_SAMPLES[file_index % len(FILE_SAMPLES)]
    file_index += 1

    # 1. Real File Upload (/alice/upload)
    code, upload_res = http_upload_file(
        "/alice/upload",
        filename=fname,
        file_bytes=fbytes,
        mime_type=ftype,
        document_title=title,
        recipient_id="bob",
        token=alice_token
    )
    if code != 200:
        raise RuntimeError(f"Failed to upload file: {upload_res}")
    sid = upload_res["session_id"]

    # 2. CUDA-Q 4,096 Teleportation Circuit Execution
    code, sign_res = http_post_json(f"/alice/sessions/{sid}/sign", {}, token=alice_token)
    if code != 200:
        raise RuntimeError(f"Failed to sign: {sign_res}")

    # 3. Verify .qds.json package export
    code, qds_json = http_get_json(f"/alice/packages/{sid}/qds-json", token=alice_token)
    if code != 200 or "package_metadata" not in qds_json:
        raise RuntimeError(f"Failed to verify .qds.json manifest: {qds_json}")

    # 4. Dispatch package to transmission channel (IN_TRANSIT)
    code, pkg = http_post_json(f"/alice/packages/{sid}/dispatch", {}, token=alice_token)
    if code != 200:
        raise RuntimeError(f"Failed to dispatch: {pkg}")

    return pkg



def run_13_attacks_suite():
    print("=" * 90)
    print("      ZASLON-QDS: CANONICAL 13-ATTACK & AUTHENTIC BASELINE E2E VALIDATION       ")
    print("=" * 90)

    # 1. Authenticate Actors
    print("\n[STEP 1] Authenticating Role-Locked Actors (Alice, Eve, Bob)...")
    http_post_json("/auth/seed-demo-users", {})
    _, alice_auth = http_post_json("/auth/login", {"username": "alice", "password": "zaslon2026"})
    _, eve_auth = http_post_json("/auth/login", {"username": "eve", "password": "zaslon2026"})
    _, bob_auth = http_post_json("/auth/login", {"username": "bob", "password": "zaslon2026"})

    alice_token = alice_auth["access_token"]
    eve_token = eve_auth["access_token"]
    bob_token = bob_auth["access_token"]
    print("         Authentication successful: Alice, Eve, and Bob tokens acquired.")

    test_results = []

    # -------------------------------------------------------------------------
    # TEST 0: AUTHENTIC BASELINE (PASSTHROUGH)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 0/13] Authentic Baseline: Alice Signs -> Eve Passthrough -> Bob Verifies")
    print("-" * 90)
    pkg0 = provision_signed_package(alice_token, "Baseline-Authentic-Directive")
    pkg0_id = pkg0["id"]

    # Eve intercepts and passes through
    http_post_json(f"/eve/intercept/{pkg0_id}", {}, token=eve_token)
    http_post_json(f"/eve/passthrough/{pkg0_id}", {}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg0_id}", {}, token=eve_token)

    # Bob verifies
    code, v0 = http_post_json(f"/bob/inbox/{pkg0_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed0 = (
        code == 200 and
        v0["security_decision"] == "VERIFIED" and
        v0["attack_detected"] is False and
        v0["mismatch_ratio"] == 0.0 and
        v0["fisher_p_value"] >= 0.01
    )
    print(f"  Decision:         {v0.get('security_decision')}")
    print(f"  Statistical:      {v0.get('statistical_verdict')} (Fisher p={v0.get('fisher_p_value')})")
    print(f"  Mismatch Ratio:   {v0.get('mismatch_ratio'):.2%}")
    print(f"  Certificate:      {v0.get('certificate_serial')}")
    print(f"  >>> RESULT:       {'PASS' if passed0 else 'FAIL'}")
    test_results.append(("Test 0: Authentic Baseline", passed0, v0.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 1: IMPERSONATION (Family 1: Identity & Authorization)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 1/13] Attack 1: Signer Identity Impersonation (IMPERSONATION)")
    print("-" * 90)
    pkg1 = provision_signed_package(alice_token, "Attack-01-Impersonation")
    pkg1_id = pkg1["id"]
    http_post_json(f"/eve/intercept/{pkg1_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg1_id}", {"attack_type": "IMPERSONATION", "mutation_params": {"spoofed_signer": "Eve_Impersonator"}}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg1_id}", {}, token=eve_token)

    code, v1 = http_post_json(f"/bob/inbox/{pkg1_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed1 = (
        code == 200 and
        v1["security_decision"] == "REJECTED" and
        v1["attack_detected"] is True and
        "IMPERSONATION" in v1.get("attack_category", "")
    )
    print(f"  Decision:         {v1.get('security_decision')} ({v1.get('attack_category')})")
    print(f"  Reason:           {v1.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed1 else 'FAIL'}")
    test_results.append(("Attack 1: IMPERSONATION", passed1, v1.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 2: UNAUTHORIZED_VERIFICATION (Family 1: Identity & Authorization)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 2/13] Attack 2: Unauthorized Verification (UNAUTHORIZED_VERIFICATION)")
    print("-" * 90)
    pkg2 = provision_signed_package(alice_token, "Attack-02-Unauthorized-Verification")
    pkg2_id = pkg2["id"]
    # Part A: Eve directly attempts to verify Bob's inbox package
    code_eve, res_eve = http_post_json(f"/bob/inbox/{pkg2_id}/verify", {"sample_ratio": 0.05}, token=eve_token)
    
    # Part B: Eve mutates recipient to rogue verifier
    http_post_json(f"/eve/intercept/{pkg2_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg2_id}", {"attack_type": "UNAUTHORIZED_VERIFICATION", "mutation_params": {"spoofed_verifier": "Mallory_Rogue"}}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg2_id}", {}, token=eve_token)
    code_bob, v2 = http_post_json(f"/bob/inbox/{pkg2_id}/verify", {"sample_ratio": 0.05}, token=bob_token)

    passed2 = (
        code_eve == 403 and
        code_bob == 200 and
        v2["security_decision"] == "UNAUTHORIZED" and
        v2["attack_detected"] is True
    )
    print(f"  Eve Probe Status: HTTP {code_eve} Forbidden (RBAC Protected)")
    print(f"  Bob Decision:     {v2.get('security_decision')} ({v2.get('attack_category')})")
    print(f"  Reason:           {v2.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed2 else 'FAIL'}")
    test_results.append(("Attack 2: UNAUTHORIZED_VERIFICATION", passed2, v2.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 3: UNAUTHORIZED_PROBE (Family 1: Identity & Authorization)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 3/13] Attack 3: Unauthorized Verifier Resource Probe (UNAUTHORIZED_PROBE)")
    print("-" * 90)
    pkg3 = provision_signed_package(alice_token, "Attack-03-Unauthorized-Probe")
    pkg3_id = pkg3["id"]
    http_post_json(f"/eve/intercept/{pkg3_id}", {}, token=eve_token)
    # Eve calls probe-verify endpoint
    code3, v3 = http_post_json(f"/eve/probe-verify/{pkg3_id}", {}, token=eve_token)
    
    # Check Bob's security events
    code_events, sec_events = http_get_json("/bob/security-events", token=bob_token)
    probe_logged = isinstance(sec_events, list) and any(
        e.get("session_id") == pkg3["session_id"] for e in sec_events if isinstance(e, dict)
    )

    passed3 = (
        code3 == 403 and
        v3.get("status") == "BLOCKED" and
        v3.get("security_verdict") == "UNAUTHORIZED" and
        probe_logged
    )
    print(f"  Probe Status:     HTTP {code3} (Status: {v3.get('status')})")
    print(f"  Security Verdict: {v3.get('security_verdict')}")
    print(f"  Barrier:          {v3.get('barrier_triggered')}")
    print(f"  Bob Alert Logged: {probe_logged}")
    print(f"  >>> RESULT:       {'PASS' if passed3 else 'FAIL'}")
    test_results.append(("Attack 3: UNAUTHORIZED_PROBE", passed3, v3.get("security_verdict")))

    # -------------------------------------------------------------------------
    # TEST 4: FILE_INTEGRITY_TAMPERING (Family 2: Artifact & Integrity)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 4/13] Attack 4: File Integrity Tampering (FILE_INTEGRITY_TAMPERING)")
    print("-" * 90)
    pkg4 = provision_signed_package(alice_token, "Attack-04-File-Tampering")
    pkg4_id = pkg4["id"]
    http_post_json(f"/eve/intercept/{pkg4_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg4_id}", {"attack_type": "FILE_INTEGRITY_TAMPERING"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg4_id}", {}, token=eve_token)

    code, v4 = http_post_json(f"/bob/inbox/{pkg4_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed4 = (
        code == 200 and
        v4["security_decision"] == "INTEGRITY_FAILURE" and
        v4["attack_detected"] is True and
        v4.get("attack_category") in ("FILE_INTEGRITY_TAMPERING", "ARTIFACT_PAYLOAD_SUBSTITUTION")
    )
    print(f"  Decision:         {v4.get('security_decision')} ({v4.get('attack_category')})")
    print(f"  Reason:           {v4.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed4 else 'FAIL'}")
    test_results.append(("Attack 4: FILE_INTEGRITY_TAMPERING", passed4, v4.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 5: DECLARATION_TAMPERING (Family 2: Artifact & Integrity)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 5/13] Attack 5: Declaration Commitment Tampering (DECLARATION_TAMPERING)")
    print("-" * 90)
    pkg5 = provision_signed_package(alice_token, "Attack-05-Decl-Tampering")
    pkg5_id = pkg5["id"]
    http_post_json(f"/eve/intercept/{pkg5_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg5_id}", {"attack_type": "DECLARATION_TAMPERING"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg5_id}", {}, token=eve_token)

    code, v5 = http_post_json(f"/bob/inbox/{pkg5_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed5 = (
        code == 200 and
        v5["security_decision"] == "INTEGRITY_FAILURE" and
        v5["attack_detected"] is True
    )
    print(f"  Decision:         {v5.get('security_decision')} ({v5.get('attack_category')})")
    print(f"  Reason:           {v5.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed5 else 'FAIL'}")
    test_results.append(("Attack 5: DECLARATION_TAMPERING", passed5, v5.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 6: QDS_PACKAGE_TAMPERING (Family 2: Artifact & Integrity)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 6/13] Attack 6: QDS Package Manifest Tampering (QDS_PACKAGE_TAMPERING)")
    print("-" * 90)
    pkg6 = provision_signed_package(alice_token, "Attack-06-Pkg-Tampering")
    pkg6_id = pkg6["id"]
    http_post_json(f"/eve/intercept/{pkg6_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg6_id}", {"attack_type": "QDS_PACKAGE_TAMPERING"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg6_id}", {}, token=eve_token)

    code, v6 = http_post_json(f"/bob/inbox/{pkg6_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed6 = (
        code == 200 and
        v6["security_decision"] == "INTEGRITY_FAILURE" and
        v6["attack_detected"] is True and
        v6.get("attack_category") in ("QDS_PACKAGE_TAMPERING", "ARTIFACT_DIGEST_MISMATCH")
    )
    print(f"  Decision:         {v6.get('security_decision')} ({v6.get('attack_category')})")
    print(f"  Reason:           {v6.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed6 else 'FAIL'}")
    test_results.append(("Attack 6: QDS_PACKAGE_TAMPERING", passed6, v6.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 7: FORGERY (Family 2: Artifact & Integrity / Quantum Binding)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 7/13] Attack 7: Quantum Bit-Flip Forgery (FORGERY)")
    print("-" * 90)
    pkg7 = provision_signed_package(alice_token, "Attack-07-Forgery")
    pkg7_id = pkg7["id"]
    http_post_json(f"/eve/intercept/{pkg7_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg7_id}", {"attack_type": "FORGERY"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg7_id}", {}, token=eve_token)

    code, v7 = http_post_json(f"/bob/inbox/{pkg7_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed7 = (
        code == 200 and
        v7["security_decision"] == "REJECTED" and
        v7["attack_detected"] is True and
        v7["statistical_verdict"] == "SUSPICIOUS" and
        v7["fisher_p_value"] < 0.01
    )
    print(f"  Decision:         {v7.get('security_decision')} ({v7.get('attack_category')})")
    print(f"  Statistical:      {v7.get('statistical_verdict')} (Fisher p={v7.get('fisher_p_value'):.4e})")
    print(f"  Mismatch Ratio:   {v7.get('mismatch_ratio'):.2%}")
    print(f"  >>> RESULT:       {'PASS' if passed7 else 'FAIL'}")
    test_results.append(("Attack 7: FORGERY", passed7, v7.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 8: REPLAY (Family 3: Protocol Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 8/13] Attack 8: Single-Use Token Replay (REPLAY)")
    print("-" * 90)
    pkg8 = provision_signed_package(alice_token, "Attack-08-Replay")
    pkg8_id = pkg8["id"]
    http_post_json(f"/eve/intercept/{pkg8_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg8_id}", {"attack_type": "REPLAY"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg8_id}", {}, token=eve_token)

    code, v8 = http_post_json(f"/bob/inbox/{pkg8_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed8 = (
        code == 200 and
        v8["security_decision"] == "REJECTED" and
        v8["attack_detected"] is True and
        "REPLAY" in v8.get("attack_category", "")
    )
    print(f"  Decision:         {v8.get('security_decision')} ({v8.get('attack_category')})")
    print(f"  Reason:           {v8.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed8 else 'FAIL'}")
    test_results.append(("Attack 8: REPLAY", passed8, v8.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 9: INTERCEPT_AND_RESEND (Family 3: Protocol Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 9/13] Attack 9: Quantum Intercept-and-Resend (INTERCEPT_AND_RESEND)")
    print("-" * 90)
    pkg9 = provision_signed_package(alice_token, "Attack-09-Intercept-Resend")
    pkg9_id = pkg9["id"]
    http_post_json(f"/eve/intercept/{pkg9_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg9_id}", {"attack_type": "INTERCEPT_AND_RESEND"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg9_id}", {}, token=eve_token)

    code, v9 = http_post_json(f"/bob/inbox/{pkg9_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed9 = (
        code == 200 and
        v9["security_decision"] == "REJECTED" and
        v9["attack_detected"] is True and
        v9["statistical_verdict"] == "SUSPICIOUS" and
        v9["fisher_p_value"] < 0.01
    )
    print(f"  Decision:         {v9.get('security_decision')} ({v9.get('attack_category')})")
    print(f"  Statistical:      {v9.get('statistical_verdict')} (Fisher p={v9.get('fisher_p_value'):.4e})")
    print(f"  Mismatch Ratio:   {v9.get('mismatch_ratio'):.2%}")
    print(f"  >>> RESULT:       {'PASS' if passed9 else 'FAIL'}")
    test_results.append(("Attack 9: INTERCEPT_AND_RESEND", passed9, v9.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 10: SESSION_SUBSTITUTION (Family 3: Protocol Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 10/13] Attack 10: Cross-Session Token Substitution (SESSION_SUBSTITUTION)")
    print("-" * 90)
    pkg10 = provision_signed_package(alice_token, "Attack-10-Session-Sub")
    pkg10_id = pkg10["id"]
    http_post_json(f"/eve/intercept/{pkg10_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg10_id}", {"attack_type": "SESSION_SUBSTITUTION"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg10_id}", {}, token=eve_token)

    code, v10 = http_post_json(f"/bob/inbox/{pkg10_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed10 = (
        code == 200 and
        v10["security_decision"] in ("REJECTED", "INTEGRITY_FAILURE") and
        v10["attack_detected"] is True
    )
    print(f"  Decision:         {v10.get('security_decision')} ({v10.get('attack_category')})")
    print(f"  Reason:           {v10.get('decision_reason')[:70]}...")
    print(f"  >>> RESULT:       {'PASS' if passed10 else 'FAIL'}")
    test_results.append(("Attack 10: SESSION_SUBSTITUTION", passed10, v10.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 11: MEASUREMENT_MANIPULATION (Family 4: Quantum Evidence Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 11/13] Attack 11: Measurement Bit Manipulation (MEASUREMENT_MANIPULATION)")
    print("-" * 90)
    pkg11 = provision_signed_package(alice_token, "Attack-11-Measurement-Manip")
    pkg11_id = pkg11["id"]
    http_post_json(f"/eve/intercept/{pkg11_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg11_id}", {"attack_type": "MEASUREMENT_MANIPULATION"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg11_id}", {}, token=eve_token)

    code, v11 = http_post_json(f"/bob/inbox/{pkg11_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed11 = (
        code == 200 and
        v11["security_decision"] == "REJECTED" and
        v11["attack_detected"] is True and
        v11["statistical_verdict"] == "SUSPICIOUS" and
        v11["fisher_p_value"] < 0.01
    )
    print(f"  Decision:         {v11.get('security_decision')} ({v11.get('attack_category')})")
    print(f"  Statistical:      {v11.get('statistical_verdict')} (Fisher p={v11.get('fisher_p_value'):.4e})")
    print(f"  Mismatch Ratio:   {v11.get('mismatch_ratio'):.2%}")
    print(f"  >>> RESULT:       {'PASS' if passed11 else 'FAIL'}")
    test_results.append(("Attack 11: MEASUREMENT_MANIPULATION", passed11, v11.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 12: BASIS_MANIPULATION (Family 4: Quantum Evidence Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 12/13] Attack 12: Conjugate Basis Manipulation (BASIS_MANIPULATION)")
    print("-" * 90)
    pkg12 = provision_signed_package(alice_token, "Attack-12-Basis-Manip")
    pkg12_id = pkg12["id"]
    http_post_json(f"/eve/intercept/{pkg12_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg12_id}", {"attack_type": "BASIS_MANIPULATION"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg12_id}", {}, token=eve_token)

    code, v12 = http_post_json(f"/bob/inbox/{pkg12_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed12 = (
        code == 200 and
        v12["security_decision"] == "REJECTED" and
        v12["attack_detected"] is True and
        v12["statistical_verdict"] == "SUSPICIOUS" and
        v12["fisher_p_value"] < 0.01
    )
    print(f"  Decision:         {v12.get('security_decision')} ({v12.get('attack_category')})")
    print(f"  Statistical:      {v12.get('statistical_verdict')} (Fisher p={v12.get('fisher_p_value'):.4e})")
    print(f"  Mismatch Ratio:   {v12.get('mismatch_ratio'):.2%}")
    print(f"  >>> RESULT:       {'PASS' if passed12 else 'FAIL'}")
    test_results.append(("Attack 12: BASIS_MANIPULATION", passed12, v12.get("security_decision")))

    # -------------------------------------------------------------------------
    # TEST 13: QUANTUM_STATE_REPLACEMENT (Family 4: Quantum Evidence Attacks)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 90)
    print("[TEST 13/13] Attack 13: Quantum State Replacement & Phase Depolarization")
    print("-" * 90)
    pkg13 = provision_signed_package(alice_token, "Attack-13-State-Replacement")
    pkg13_id = pkg13["id"]
    http_post_json(f"/eve/intercept/{pkg13_id}", {}, token=eve_token)
    http_post_json(f"/eve/mutate/{pkg13_id}", {"attack_type": "QUANTUM_STATE_REPLACEMENT"}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg13_id}", {}, token=eve_token)

    code, v13 = http_post_json(f"/bob/inbox/{pkg13_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    passed13 = (
        code == 200 and
        v13["security_decision"] == "REJECTED" and
        v13["attack_detected"] is True and
        v13["statistical_verdict"] == "SUSPICIOUS" and
        v13["fisher_p_value"] < 0.01
    )
    print(f"  Decision:         {v13.get('security_decision')} ({v13.get('attack_category')})")
    print(f"  Statistical:      {v13.get('statistical_verdict')} (Fisher p={v13.get('fisher_p_value'):.4e})")
    print(f"  Mismatch Ratio:   {v13.get('mismatch_ratio'):.2%}")
    print(f"  >>> RESULT:       {'PASS' if passed13 else 'FAIL'}")
    test_results.append(("Attack 13: QUANTUM_STATE_REPLACEMENT", passed13, v13.get("security_decision")))

    # -------------------------------------------------------------------------
    # SUMMARY MATRIX
    # -------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("                      ZASLON-QDS 14-TEST VALIDATION SUMMARY MATRIX                      ")
    print("=" * 90)
    print(f"{'#':<4} | {'Scenario Name':<42} | {'Expected Verdict':<18} | {'Status':<8}")
    print("-" * 90)
    all_passed = True
    for idx, (name, passed, verdict) in enumerate(test_results):
        status_str = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"{idx:<4} | {name:<42} | {str(verdict):<18} | {status_str:<8}")
    print("=" * 90)
    print(f"OVERALL RESULT: {'>>> ALL 14 TESTS PASSED (100%) <<<' if all_passed else '>>> SOME TESTS FAILED <<<'}")
    print("=" * 90)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_13_attacks_suite()
