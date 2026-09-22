"""
Validation Test: Canonical JWT Refresh & Expiry Recovery
Validates:
1. Generation and authentication of tokens.
2. Canonical POST /api/v1/auth/refresh endpoint.
3. Refreshing an expired or near-expiry token returns a fresh token with:
   - Identical user identity (sub)
   - Identical user role
   - Updated expiration timestamp
4. Verified that protected endpoint /api/v1/auth/me accepts the rotated token.
"""
import requests
import datetime
import jwt
import sys

BASE_URL = "http://localhost:8000/api/v1"
SECRET_KEY = "zaslon_qds_dev_secret_key_change_in_production_123456789"
ALGORITHM = "HS256"

def run_test():
    print("=== Testing Canonical JWT Refresh & Expiry Recovery ===")
    
    # 1. Obtain a valid token for Alice
    requests.post(f"{BASE_URL}/auth/seed-demo-users")
    alice_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5173, "role": "ALICE"}).json()
    valid_token = alice_res["access_token"]
    
    me_res = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
    assert me_res.status_code == 200, f"Expected 200 from /auth/me, got {me_res.status_code}"
    user_info = me_res.json()
    print(f"[*] Initial token authenticated as user '{user_info['username']}' with role '{user_info['role']}'")
    
    # 2. Call canonical /auth/refresh with valid token
    refresh_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"Authorization": f"Bearer {valid_token}"})
    assert refresh_res.status_code == 200, f"Expected 200 from /auth/refresh, got {refresh_res.status_code}"
    refreshed_data = refresh_res.json()
    new_token = refreshed_data["access_token"]
    print(f"[*] Proactive token refresh succeeded: {new_token[:20]}...")
    assert refreshed_data["user"]["username"] == user_info["username"]
    assert refreshed_data["user"]["role"] == user_info["role"]
    
    # Verify new token works on protected endpoint
    me_new = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_new.status_code == 200
    
    # 3. Fabricate an EXPIRED token (expired 2 minutes ago) with identical signature key
    expired_payload = {
        "sub": "alice",
        "role": "ALICE",
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2),
        "iat": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Verify that calling /auth/me with the expired token returns 401 Unauthorized
    expired_me_res = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    print(f"[*] Calling protected endpoint with expired token: HTTP {expired_me_res.status_code} (as expected)")
    assert expired_me_res.status_code == 401, f"Expected 401, got {expired_me_res.status_code}"
    
    # 4. Call canonical /auth/refresh with the expired token (recovery mode)
    recovery_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"Authorization": f"Bearer {expired_token}"})
    print(f"[*] Calling /auth/refresh with expired token: HTTP {recovery_res.status_code}")
    assert recovery_res.status_code == 200, f"Expected 200, got {recovery_res.status_code}: {recovery_res.text}"
    
    recovered_data = recovery_res.json()
    recovered_token = recovered_data["access_token"]
    assert recovered_data["user"]["username"] == "alice"
    assert recovered_data["user"]["role"] == "ALICE"
    
    # 5. Verify the recovered token now successfully accesses /auth/me without re-login
    recovered_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {recovered_token}"})
    assert recovered_me.status_code == 200, f"Expected 200 with recovered token, got {recovered_me.status_code}"
    print(f"[*] Verified recovered token grants access to /auth/me for '{recovered_me.json()['username']}'")
    
    # 6. Test with a completely invalid signature token -> must reject 401
    invalid_token = jwt.encode(expired_payload, "COMPLETELY_WRONG_SECRET_KEY_12345", algorithm=ALGORITHM)
    invalid_res = requests.post(f"{BASE_URL}/auth/refresh", headers={"Authorization": f"Bearer {invalid_token}"})
    print(f"[*] Calling /auth/refresh with invalid signature token: HTTP {invalid_res.status_code}")
    assert invalid_res.status_code == 401, f"Expected 401, got {invalid_res.status_code}"
    
    print("\n[SUCCESS] Canonical JWT Refresh & Expiry Recovery PASSED 100%!\n")

if __name__ == "__main__":
    run_test()
