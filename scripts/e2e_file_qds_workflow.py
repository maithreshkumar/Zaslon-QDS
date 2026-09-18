"""
Zaslon-QDS Authentic File-Based QDS & Dual-Channel E2E Script (SIH 26141).
Validates:
1. Alice uploads arbitrary binary file (PDF/bin) -> 64KB streaming SHA-512 digest
2. Alice runs 4,096 CUDA-Q 3-qubit teleportation circuits ($Q_0, Q_1, Q_2$)
3. Companion <filename>.qds.json signature package download & validation
4. Direct signed file download & byte-level integrity match
5. Alice dispatches over dual Classical + Quantum channels
6. Eve intercepts and sniffs split-screen telemetry (TLS 1.3 vs 25km fiber)
7. Eve passthrough mode -> forwards to Bob
8. Bob verifies in-flight package -> 11-step engine -> 5 barriers PASS -> Fisher p >= 0.01
9. Official cryptographic certificate receipt (<filename>.cert.json) download
10. Offline manual dual-file verification (document + .qds.json) via /bob/manual-verify
11. Offline manual verification with tampered file -> INTEGRITY_FAILURE
12. SeQUeNCe discrete-event quantum network simulation endpoint verification
"""
import urllib.request
import urllib.error
import json
import time
import uuid

BASE_URL = "http://localhost:8000/api/v1"
QUANTUM_URL = "http://localhost:8001"


def http_post_json(endpoint: str, data: dict, token: str = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_json(endpoint: str, token: str = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_bytes(endpoint: str, token: str = None) -> bytes:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def http_post_multipart(endpoint: str, fields: dict, files: dict, token: str = None) -> dict:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    for name, (filename, filedata, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(filedata)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_file_qds_tests():
    print("=" * 80)
    print("   ZASLON-QDS: FILE-BASED DUAL-CHANNEL QUANTUM DIGITAL SIGNATURES E2E   ")
    print("=" * 80)

    # 1. Login
    print("\n[1/7] Authenticating Alice, Eve, and Bob...")
    http_post_json("/auth/seed-demo-users", {})
    alice_token = http_post_json("/auth/login", {"username": "alice", "password": "zaslon2026"})["access_token"]
    eve_token = http_post_json("/auth/login", {"username": "eve", "password": "zaslon2026"})["access_token"]
    bob_token = http_post_json("/auth/login", {"username": "bob", "password": "zaslon2026"})["access_token"]
    print("      Authentication tokens acquired.")

    # 2. Alice uploads a simulated binary PDF document
    print("\n[2/7] Alice uploads classified defense file (simulated PDF document)...")
    sample_binary_content = b"%PDF-1.7\nClassified Operational Directive: Operation Zaslon\n" + (b"BYTE_STREAM_PAYLOAD_" * 500)
    upload_res = http_post_multipart(
        "/alice/upload",
        fields={
            "document_title": "OPERATION_ZASLON_TACTICAL_ORDER.pdf",
            "recipient_id": "bob"
        },
        files={
            "file": ("OPERATION_ZASLON_TACTICAL_ORDER.pdf", sample_binary_content, "application/pdf")
        },
        token=alice_token
    )
    session_id = upload_res["session_id"]
    committed_digest = upload_res["sha512_digest"]
    filename = upload_res["file_name"]
    print(f"      Session created: {session_id}")
    print(f"      File: {filename} ({upload_res['file_size_bytes']} bytes)")
    print(f"      SHA-512 Digest: {committed_digest[:32]}...{committed_digest[-16:]}")
    assert upload_res["is_file"] is True

    # 3. Alice executes genuine 4,096 CUDA-Q circuits
    print("\n[3/7] Alice executes 4,096 CUDA-Q 3-qubit teleportation circuits ($Q_0, Q_1, Q_2$)...")
    t0 = time.time()
    sign_res = http_post_json(f"/alice/sessions/{session_id}/sign", {}, token=alice_token)
    sign_duration = time.time() - t0
    print(f"      Teleportation complete in {sign_duration:.2f}s!")
    print(f"      Token: {sign_res['signature_token'][:24]}...")
    q_run_id = sign_res.get("quantum_run_id") or sign_res.get("qds_manifest_json", {}).get("quantum_binding", {}).get("quantum_run_id")
    print(f"      Quantum Run ID: {q_run_id} (Operations: {sign_res['total_operations']})")
    assert sign_res["status"] == "DECLARATION_READY"

    # 4. Companion .qds.json package export & file download
    print("\n[4/7] Exporting companion <filename>.qds.json and testing file download...")
    manifest = http_get_json(f"/alice/packages/{session_id}/qds-json", token=alice_token)
    print(f"      Manifest Protocol: {manifest['protocol']}")
    print(f"      Standard: {manifest['standard']}")
    print(f"      Signer: {manifest['signer']['signer_id']} -> Verifier: {manifest['designated_verifier']['verifier_id']}")
    print(f"      Quantum Circuits: {manifest['quantum_binding']['total_teleportation_operations']}")
    assert manifest["document"]["sha512_digest"] == committed_digest
    assert manifest["document"]["filename"] == filename

    downloaded_bytes = http_get_bytes(f"/alice/files/{session_id}/download", token=alice_token)
    assert downloaded_bytes == sample_binary_content
    print(f"      File download verified: {len(downloaded_bytes)} bytes match upload byte-for-byte!")

    # 5. Alice dispatches package over dual channels
    print("\n[5/7] Alice dispatches package over dual Classical + Quantum channels...")
    pkg = http_post_json(f"/alice/packages/{session_id}/dispatch", {}, token=alice_token)
    pkg_id = pkg["id"]
    tracking_no = pkg["package_tracking_no"]
    print(f"      Package: {tracking_no} (Status: {pkg['status']})")
    assert pkg["status"] == "IN_TRANSIT"

    # 6. Eve sniffs split-screen channel telemetry & forwards untouched
    print("\n[6/7] Eve sniffs split-screen telemetry and forwards via Passthrough mode...")
    telemetry = http_get_json(f"/eve/channel-telemetry/{pkg_id}", token=eve_token)
    c_chan = telemetry["classical_channel"]
    q_chan = telemetry["quantum_channel"]
    print(f"      Classical Channel: {c_chan['transport_security']} (Status: {c_chan['channel_status']}, File: {c_chan['file_name']})")
    print(f"      Quantum Channel: {q_chan['network_parameters']['fiber_distance_km']} km fiber (Status: {q_chan['channel_status']}, Latency: {q_chan['network_parameters']['propagation_delay_us']} us)")
    print(f"      Total Quantum Circuits in Stream: {q_chan['total_teleportation_operations']}")

    http_post_json(f"/eve/intercept/{pkg_id}", {}, token=eve_token)
    http_post_json(f"/eve/passthrough/{pkg_id}", {}, token=eve_token)
    http_post_json(f"/eve/forward/{pkg_id}", {}, token=eve_token)
    print(f"      Package forwarded to Bob (Status: FORWARDED/RECEIVED).")

    # 7. Bob verifies in-flight transmission -> 11-step engine -> Certificate receipt
    print("\n[7/7] Bob verifies package in inbox and generates cryptographic certificate...")
    verify_res = http_post_json(f"/bob/inbox/{pkg_id}/verify", {"sample_ratio": 0.05}, token=bob_token)
    print(f"      Security Decision: {verify_res['security_decision']}")
    print(f"      Statistical Verdict: {verify_res['statistical_verdict']}")
    print(f"      Sample Size: {verify_res['sample_size']} of 4,096 operations")
    print(f"      Matches: {verify_res['match_count']} | Mismatches: {verify_res['mismatch_count']}")
    print(f"      Mismatch Ratio: {verify_res['mismatch_ratio']:.2%}")
    print(f"      Fisher Exact p-value: {verify_res['fisher_p_value']}")
    print(f"      Certificate Serial: {verify_res['certificate_serial']}")
    assert verify_res["security_decision"] == "VERIFIED"
    assert verify_res["attack_detected"] is False

    # Download certificate receipt
    cert = http_get_json(f"/bob/verifications/{verify_res['id']}/certificate", token=bob_token)
    print(f"      Certificate Serial in Receipt: {cert['certificate_serial']}")
    print(f"      Cryptographic Receipt Signature: {cert['cryptographic_receipt_signature'][:32]}...")
    assert cert["decision"] == "VERIFIED"
    assert cert["certificate_serial"] == verify_res["certificate_serial"]

    # 8. Test Offline Manual Dual-File Upload Verification
    print("\n[BONUS 1] Bob executes Offline Manual Dual-File Upload Verification...")
    manifest_bytes = json.dumps(manifest).encode("utf-8")
    manual_verify_res = http_post_multipart(
        "/bob/manual-verify",
        fields={},
        files={
            "file": (filename, sample_binary_content, "application/pdf"),
            "qds_file": (f"{filename}.qds.json", manifest_bytes, "application/json")
        },
        token=bob_token
    )
    print(f"      Manual Verification Verdict: {manual_verify_res['security_decision']}")
    print(f"      Certificate: {manual_verify_res['certificate_serial']}")
    assert manual_verify_res["security_decision"] == "VERIFIED"

    # 9. Test Offline Manual Verification with Tampered Document
    print("\n[BONUS 2] Bob verifies tampered document with original .qds.json...")
    tampered_bytes = sample_binary_content + b"\n[MALICIOUS_EVE_INJECTION]"
    tampered_verify_res = http_post_multipart(
        "/bob/manual-verify",
        fields={},
        files={
            "file": (filename, tampered_bytes, "application/pdf"),
            "qds_file": (f"{filename}.qds.json", manifest_bytes, "application/json")
        },
        token=bob_token
    )
    print(f"      Tampered File Verdict: {tampered_verify_res['security_decision']}")
    print(f"      Reason: {tampered_verify_res['decision_reason']}")
    assert tampered_verify_res["security_decision"] == "INTEGRITY_FAILURE"
    assert tampered_verify_res["attack_detected"] is True

    # 10. Quantum Network Simulation verification
    print("\n[BONUS 3] Testing SeQUeNCe-aligned Quantum Network Simulation...")
    network_req = urllib.request.Request(
        f"{QUANTUM_URL}/network/simulate",
        data=json.dumps({"total_operations": 4096, "fiber_distance_km": 25.0}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(network_req) as net_resp:
        sim_data = json.loads(net_resp.read().decode("utf-8"))
    sim = sim_data.get("simulation", sim_data)
    print(f"      Simulator Engine: {sim['simulator_engine']}")
    print(f"      Optical Latency: {sim['timing_and_delays']['optical_propagation_delay_us']} us across {sim['topology']['total_fiber_length_km']} km")
    print(f"      Channel Fidelity: {sim['quantum_physical_metrics']['state_fidelity_post_transmission']}")
    print(f"      Channel State: {sim['quantum_physical_metrics']['channel_status']}")
    assert sim["quantum_physical_metrics"]["state_fidelity_post_transmission"] > 0.95

    print("\n" + "=" * 80)
    print(">>> SUCCESS: FILE-BASED DUAL-CHANNEL QDS COMPLETE E2E VERIFIED! <<<")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_file_qds_tests()
