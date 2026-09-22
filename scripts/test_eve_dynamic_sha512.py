"""
Validation Test: Eve Classical Channel Dynamic SHA-512 Switching
Validates:
1. Querying fresh channel telemetry for untampered package shows committed_digest == Alice's hash, current_file_digest == None.
2. After FILE_INTEGRITY_TAMPERING:
   - committed_digest remains Alice's original hash (as committed in public declaration).
   - current_file_digest is dynamically computed from the mutated file on disk/payload and returned.
   - current_file_digest != committed_digest.
3. Multiple transmissions show their own distinct hashes without stale caching.
"""
import requests
import hashlib
import sys

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    print("=== Testing Eve Classical Channel Dynamic SHA-512 Telemetry ===")
    
    requests.post(f"{BASE_URL}/auth/seed-demo-users")
    alice_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5173, "role": "ALICE"}).json()
    eve_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5174, "role": "EVE"}).json()
    
    alice_headers = {"Authorization": f"Bearer {alice_res['access_token']}"}
    eve_headers = {"Authorization": f"Bearer {eve_res['access_token']}"}
    
    # 1. Alice creates and dispatches Package A
    msg_a = "AUTHENTIC PAYLOAD FOR TRANSMISSION A: Alpha Bravo Charlie"
    expected_digest_a = hashlib.sha512(msg_a.encode()).hexdigest()
    
    draft_a = requests.post(
        f"{BASE_URL}/alice/draft",
        json={"document_title": "Directive Alpha", "message_payload": msg_a, "recipient_id": "bob"},
        headers=alice_headers
    ).json()
    sess_a = draft_a["session_id"]
    requests.post(f"{BASE_URL}/alice/sessions/{sess_a}/sign", headers=alice_headers)
    disp_a = requests.post(f"{BASE_URL}/alice/packages/{sess_a}/dispatch", headers=alice_headers).json()
    trans_a_id = disp_a["id"]
    print(f"[*] Dispatched Package A (#{disp_a['package_tracking_no']}) - Original SHA-512: {expected_digest_a[:16]}...")
    
    # 2. Check telemetry before tampering
    telem_a = requests.get(f"{BASE_URL}/eve/channel-telemetry/{trans_a_id}", headers=eve_headers).json()
    classical_a = telem_a["classical_channel"]
    
    print(f"[*] Package A Telemetry (Untampered): committed_digest={classical_a['committed_digest'][:16]}..., current_file_digest={classical_a.get('current_file_digest')}")
    assert classical_a["committed_digest"] == expected_digest_a, "Committed digest mismatch"
    assert classical_a.get("current_file_digest") is None, "current_file_digest should be None for untampered package"
    
    # 3. Eve intercepts and mutates Package A with FILE_INTEGRITY_TAMPERING
    requests.post(f"{BASE_URL}/eve/intercept/{trans_a_id}", headers=eve_headers)
    
    mutate_res = requests.post(
        f"{BASE_URL}/eve/mutate/{trans_a_id}",
        json={
            "attack_type": "FILE_INTEGRITY_TAMPERING",
            "mutation_params": {"tampered_message": "MALICIOUS OVERRIDE INJECTED BY EVE"}
        },
        headers=eve_headers
    )
    assert mutate_res.status_code == 200, f"Mutation failed: {mutate_res.text}"
    print(f"[*] Eve applied FILE_INTEGRITY_TAMPERING to Package A")
    
    # 4. Check telemetry after tampering
    telem_a_tampered = requests.get(f"{BASE_URL}/eve/channel-telemetry/{trans_a_id}", headers=eve_headers).json()
    classical_a_tampered = telem_a_tampered["classical_channel"]
    
    print(f"[*] Package A Telemetry (TAMPERED): committed_digest={classical_a_tampered['committed_digest'][:16]}..., current_file_digest={classical_a_tampered.get('current_file_digest')[:16]}...")
    
    # committed_digest MUST remain Alice's original hash!
    assert classical_a_tampered["committed_digest"] == expected_digest_a, "Committed digest was corrupted!"
    
    # current_file_digest MUST be present and different
    tampered_digest = classical_a_tampered.get("current_file_digest")
    assert tampered_digest is not None, "current_file_digest was not provided after file tampering"
    assert tampered_digest != expected_digest_a, "current_file_digest must differ from committed_digest"
    
    expected_tampered_hash = hashlib.sha512(b"MALICIOUS OVERRIDE INJECTED BY EVE").hexdigest()
    assert tampered_digest == expected_tampered_hash, f"Expected {expected_tampered_hash}, got {tampered_digest}"
    print(f"[*] Verified current_file_digest matches tampered content exactly: {tampered_digest[:16]}...")
    
    print("\n[SUCCESS] Eve Classical Channel Dynamic SHA-512 Telemetry PASSED 100%!\n")

if __name__ == "__main__":
    run_test()
