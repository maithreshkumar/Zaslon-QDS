"""
Validation Test: Unauthorized Probe & Verification Isolation
Validates:
1. Unauthorized actor verification attempts on /inbox/{trans_id}/verify return HTTP 403.
2. Direct probe attempts on Bob-private samples return HTTP 403.
3. SecurityEventModel is recorded with UNAUTHORIZED_PROBE / UNAUTHORIZED_VERIFICATION.
4. The authentic package in Bob's inbox is NOT mutated (recipient remains Bob, status remains intact, is_tampered is False, token not consumed).
5. Bob can verify normally and achieve VERIFIED.
"""
import requests
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    print("=== Testing Unauthorized Probe & Verification Semantics ===")
    
    # 1. Seed demo users and get tokens
    requests.post(f"{BASE_URL}/auth/seed-demo-users")
    
    alice_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5173, "role": "ALICE"}).json()
    eve_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5174, "role": "EVE"}).json()
    bob_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5175, "role": "BOB"}).json()
    
    alice_token = alice_res["access_token"]
    eve_token = eve_res["access_token"]
    bob_token = bob_res["access_token"]
    
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    eve_headers = {"Authorization": f"Bearer {eve_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    
    # 2. Alice drafts and dispatches a package
    draft_res = requests.post(
        f"{BASE_URL}/alice/draft",
        json={
            "document_title": "Top Secret Directive - Probe Test",
            "message_payload": "Classified quantum routing instructions for verifier node Bob.",
            "recipient_id": "bob"
        },
        headers=alice_headers
    ).json()
    session_id = draft_res["session_id"]
    
    sign_res = requests.post(f"{BASE_URL}/alice/sessions/{session_id}/sign", headers=alice_headers).json()
    
    dispatch_res = requests.post(f"{BASE_URL}/alice/packages/{session_id}/dispatch", headers=alice_headers).json()
    trans_id = dispatch_res["id"]
    tracking_no = dispatch_res["package_tracking_no"]
    token_val = dispatch_res["signature_token"]
    print(f"[*] Package #{tracking_no} dispatched by Alice (trans_id: {trans_id})")
    
    # 3. Eve intercepts and attempts UNAUTHORIZED_PROBE (probe verify endpoint)
    intercept_res = requests.post(f"{BASE_URL}/eve/intercept/{trans_id}", headers=eve_headers)
    print(f"[*] Eve intercepted package: HTTP {intercept_res.status_code}")
    
    probe_res = requests.post(f"{BASE_URL}/eve/probe-verify/{trans_id}", headers=eve_headers)
    print(f"[*] Eve probe-verify response: HTTP {probe_res.status_code}")
    assert probe_res.status_code == 403, f"Expected HTTP 403, got {probe_res.status_code}"
    
    # 4. Eve attempts direct call to Bob's inbox verification endpoint
    direct_verify_res = requests.post(f"{BASE_URL}/bob/inbox/{trans_id}/verify", headers=eve_headers)
    print(f"[*] Eve direct verify attempt response: HTTP {direct_verify_res.status_code}")
    assert direct_verify_res.status_code == 403, f"Expected HTTP 403, got {direct_verify_res.status_code}"
    
    # 5. Eve forwards package to Bob untouched
    fwd_res = requests.post(f"{BASE_URL}/eve/forward/{trans_id}", headers=eve_headers)
    print(f"[*] Eve forward response: HTTP {fwd_res.status_code}")
    assert fwd_res.status_code == 200, f"Expected 200, got {fwd_res.status_code}: {fwd_res.text}"
    
    # 6. Verify Bob's inbox state: Package MUST be intact, recipient == 'bob', is_tampered == False, status == 'RECEIVED'
    inbox_res = requests.get(f"{BASE_URL}/bob/inbox", headers=bob_headers).json()
    target_pkg = next((p for p in inbox_res if p["id"] == trans_id), None)
    assert target_pkg is not None, "Target package not found in Bob's inbox"
    print(f"[*] Package status in Bob's inbox: {target_pkg['status']}")
    print(f"[*] Recipient ID: {target_pkg['recipient_id']}")
    print(f"[*] is_tampered: {target_pkg['is_tampered']}")
    print(f"[*] signature_token: {target_pkg['signature_token'][:16]}...")
    
    assert target_pkg["recipient_id"] == "bob", f"Recipient was corrupted: {target_pkg['recipient_id']}"
    assert target_pkg["status"] == "RECEIVED", f"Status corrupted: {target_pkg['status']}"
    assert target_pkg["is_tampered"] is False, "Package falsely marked as tampered"
    assert target_pkg["signature_token"] == token_val, "Token altered"
    
    # 7. Verify security events recorded for Bob
    sec_events_res = requests.get(f"{BASE_URL}/bob/security-events", headers=bob_headers).json()
    probe_events = [e for e in sec_events_res if e.get("session_id") == session_id]
    print(f"[*] Security events logged for this session: {len(probe_events)}")
    assert len(probe_events) >= 1, "Expected at least 1 security event logged"
    ev = probe_events[0]
    print(f"[*] Event type: {ev['event_type']}, Actor: {ev['actor']}, Severity: {ev['severity']}")
    assert "UNAUTHORIZED" in ev["event_type"]
    
    # 8. Bob executes legitimate verification
    verify_raw = requests.post(f"{BASE_URL}/bob/inbox/{trans_id}/verify", json={"sample_ratio": 0.05}, headers=bob_headers)
    print(f"[*] Bob verify raw response: {verify_raw.status_code} -> {verify_raw.text}")
    verify_res = verify_raw.json()
    verdict = verify_res.get("security_decision") or verify_res.get("decision")
    print(f"[*] Bob verification outcome: {verdict}")
    assert verdict == "VERIFIED", f"Expected VERIFIED, got {verdict}"
    
    print("\n[SUCCESS] Unauthorized Probe & Verification Isolation PASSED 100%!\n")

if __name__ == "__main__":
    run_test()
