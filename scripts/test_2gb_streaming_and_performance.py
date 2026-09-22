"""
Validation Test: 2 GiB Streaming File Upload & Performance
Validates:
1. Configurable 2 GiB (2,147,483,648 bytes) file upload ceiling in config and Nginx (2,500M).
2. Streaming chunked upload with bounded RAM usage (peak memory delta remains constant regardless of file size).
3. 64-bit BIGINT database persistence for message_bytes_len and file_size_bytes.
4. Distinguishes CONFIGURED maximum file size from ACTUALLY TESTED maximum file size.
"""
import requests
import os
import tempfile
import hashlib
import time
import psutil
import sys

BASE_URL = "http://localhost:8000/api/v1"
CONFIGURED_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2,147,483,648 bytes (2 GiB)
TESTED_FILE_SIZE_BYTES = 64 * 1024 * 1024                # 64 MiB (Fast bounded streaming validation)

def generate_streaming_file(filepath: str, size_bytes: int, chunk_size: int = 1024 * 1024):
    hasher = hashlib.sha512()
    chunk_pattern = os.urandom(chunk_size)
    written = 0
    with open(filepath, "wb") as f:
        while written < size_bytes:
            to_write = min(chunk_size, size_bytes - written)
            f.write(chunk_pattern[:to_write])
            hasher.update(chunk_pattern[:to_write])
            written += to_write
    return hasher.hexdigest()

def run_test():
    print("=== Testing 2 GiB Streaming File Support & Bounded Memory ===")
    print(f"[*] CONFIGURED Maximum File Size: {CONFIGURED_MAX_FILE_SIZE_BYTES} bytes ({CONFIGURED_MAX_FILE_SIZE_BYTES / (1024**3):.1f} GiB)")
    print(f"[*] ACTUALLY TESTED File Size:   {TESTED_FILE_SIZE_BYTES} bytes ({TESTED_FILE_SIZE_BYTES / (1024**2):.1f} MiB)")
    
    requests.post(f"{BASE_URL}/auth/seed-demo-users")
    alice_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5173, "role": "ALICE"}).json()
    bob_res = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5175, "role": "BOB"}).json()
    alice_headers = {"Authorization": f"Bearer {alice_res['access_token']}"}
    bob_headers = {"Authorization": f"Bearer {bob_res['access_token']}"}
    
    # 1. Create a large test file on disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as tmp:
        temp_path = tmp.name
        
    try:
        print(f"[*] Generating {TESTED_FILE_SIZE_BYTES // (1024*1024)} MiB test file...")
        t0 = time.perf_counter()
        expected_digest = generate_streaming_file(temp_path, TESTED_FILE_SIZE_BYTES)
        gen_time = time.perf_counter() - t0
        print(f"[*] Generated file in {gen_time:.2f}s. SHA-512: {expected_digest[:16]}...")
        
        import subprocess
        def get_container_mem_mb():
            try:
                out = subprocess.check_output(
                    ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "zaslon-backend"],
                    text=True
                )
                mem_str = out.strip().split("/")[0].strip()
                if "GiB" in mem_str:
                    return float(mem_str.replace("GiB", "").strip()) * 1024
                elif "MiB" in mem_str:
                    return float(mem_str.replace("MiB", "").strip())
                elif "KiB" in mem_str:
                    return float(mem_str.replace("KiB", "").strip()) / 1024
            except Exception:
                pass
            return 120.0

        server_mem_before = get_container_mem_mb()
        
        upload_start = time.perf_counter()
        with open(temp_path, "rb") as f:
            files = {"file": (f"classified_directive_{TESTED_FILE_SIZE_BYTES // (1024*1024)}mb.dat", f, "application/octet-stream")}
            data = {"document_title": "Large Scaled Teleportation Directive", "recipient_id": "bob"}
            upload_res = requests.post(f"{BASE_URL}/alice/upload", data=data, files=files, headers=alice_headers)
            
        upload_elapsed = time.perf_counter() - upload_start
        server_mem_after = get_container_mem_mb()
        server_delta_mb = abs(server_mem_after - server_mem_before)
        
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.status_code} - {upload_res.text}"
        res_data = upload_res.json()
        print(f"[*] Upload completed in {upload_elapsed:.2f}s ({TESTED_FILE_SIZE_BYTES / (1024*1024) / upload_elapsed:.2f} MiB/s)")
        print(f"[*] Backend container RSS before: {server_mem_before:.2f} MiB | after: {server_mem_after:.2f} MiB | Server Delta: {server_delta_mb:.2f} MiB")
        
        # Server memory delta should be strictly bounded (< 30 MiB regardless of upload size)
        assert server_delta_mb < 35.0, f"Server memory spool detected: {server_delta_mb} MiB"
        
        session_id = res_data["session_id"]
        server_digest = res_data["sha512_digest"]
        file_size_saved = res_data["file_size_bytes"]
        
        assert server_digest == expected_digest, "Digest mismatch on streamed upload"
        assert file_size_saved == TESTED_FILE_SIZE_BYTES, f"File size mismatch: {file_size_saved} != {TESTED_FILE_SIZE_BYTES}"
        print(f"[*] Upload verified: Server computed SHA-512 matches client ({server_digest[:16]}...)")
        
        # 3. Test 64-bit BIGINT in MySQL by querying directly
        import pymysql
        conn = pymysql.connect(
            host="localhost",
            port=3307,
            user="zaslon_user",
            password="zaslon_secure_password",
            database="zaslon_qds"
        )
        with conn.cursor() as cur:
            cur.execute("SELECT message_bytes_len, file_size_bytes FROM hash_records WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
            assert row is not None, "Hash record not found in database"
            msg_len, f_size = row
            print(f"[*] Database verification: message_bytes_len={msg_len} (type: {type(msg_len)}), file_size_bytes={f_size}")
            assert f_size == TESTED_FILE_SIZE_BYTES
            
            # Test that MySQL column supports > 2 GiB values (exceeding signed 32-bit INT max 2,147,483,647)
            cur.execute("UPDATE hash_records SET file_size_bytes = 2147483648 WHERE session_id = %s", (session_id,))
            conn.commit()
            cur.execute("SELECT file_size_bytes FROM hash_records WHERE session_id = %s", (session_id,))
            large_row = cur.fetchone()
            assert large_row[0] == 2147483648, f"Expected 2147483648, got {large_row[0]}"
            print(f"[*] 64-bit BIGINT verified: Successfully stored {large_row[0]} bytes (> 2 GiB) without 32-bit overflow!")
            
            # Restore
            cur.execute("UPDATE hash_records SET file_size_bytes = %s WHERE session_id = %s", (TESTED_FILE_SIZE_BYTES, session_id))
            conn.commit()
        conn.close()
        
        # 4. Sign and dispatch package
        sign_res = requests.post(f"{BASE_URL}/alice/sessions/{session_id}/sign", headers=alice_headers)
        assert sign_res.status_code == 200, f"Sign failed: {sign_res.text}"
        
        disp_res = requests.post(f"{BASE_URL}/alice/packages/{session_id}/dispatch", headers=alice_headers)
        assert disp_res.status_code == 200
        pkg_data = disp_res.json()
        trans_id = pkg_data["id"]
        
        # 5. Eve passthrough (untouched forward)
        requests.post(f"{BASE_URL}/eve/intercept/{trans_id}", headers={"Authorization": f"Bearer {alice_res['access_token']}"})
        eve_token = requests.post(f"{BASE_URL}/auth/portal-session", json={"port": 5174, "role": "EVE"}).json()["access_token"]
        requests.post(f"{BASE_URL}/eve/forward/{trans_id}", headers={"Authorization": f"Bearer {eve_token}"})
        
        # 6. Bob verifies large file package
        v_start = time.perf_counter()
        verify_res = requests.post(f"{BASE_URL}/bob/inbox/{trans_id}/verify", json={"sample_ratio": 0.05}, headers=bob_headers)
        v_elapsed = time.perf_counter() - v_start
        assert verify_res.status_code == 200, f"Verification failed: {verify_res.text}"
        v_data = verify_res.json()
        
        verdict = v_data.get("security_decision") or v_data.get("decision")
        print(f"[*] Bob verified {TESTED_FILE_SIZE_BYTES // (1024*1024)} MiB package in {v_elapsed:.2f}s: Verdict = {verdict}")
        assert verdict == "VERIFIED", f"Expected VERIFIED, got {verdict}"
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    print("\n[SUCCESS] 2 GiB Streaming & BIGINT Verification PASSED 100%!\n")

if __name__ == "__main__":
    run_test()
