from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import httpx


ALICE = "http://frontend:5173"
ATTACK = "http://frontend:5174"
BOB = "http://frontend:5175"
API = "http://127.0.0.1:8000"


def require(response: httpx.Response, expected: int = 200) -> httpx.Response:
    if response.status_code != expected:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}: {response.text[:500]}"
        )
    return response


def main() -> None:
    document = b"ZASLON-QDS Docker acceptance artifact\n"
    with httpx.Client(timeout=310.0, trust_env=False) as client:
        health = require(client.get(f"{API}/api/v1/health")).json()
        if health.get("status") != "ok":
            raise RuntimeError(f"API health is degraded: {health}")

        # The central API must not accept an unauthenticated role request.
        require(client.get(f"{API}/api/v1/sessions"), expected=401)

        signed = require(
            client.post(
                f"{ALICE}/api/v1/alice/sessions",
                files={"document": ("docker-acceptance.txt", document, "text/plain")},
                data={
                    "signer_id": "Alice",
                    "verifier_id": "Bob",
                    "seed": "26141",
                    "encryption_passphrase": "docker-acceptance-passphrase",
                },
            )
        ).json()
        session_id = signed["session"]["id"]
        artifact_name = signed["artifact"]["filename"]
        if not artifact_name.endswith(".qds.json"):
            raise RuntimeError("Alice did not return a .qds.json artifact filename")
        if signed["quantum"].get("engine") != "CUDA-Q":
            raise RuntimeError("Live signing did not use CUDA-Q")
        if signed["quantum"].get("target") != "nvidia":
            raise RuntimeError("Live signing did not use the NVIDIA target")

        downloaded = require(
            client.get(f"{ALICE}/api/v1/sessions/{session_id}/signature")
        )
        artifact = downloaded.json()
        if artifact != signed["signature"]:
            raise RuntimeError("Downloaded QDS artifact differs from the signed response")
        if artifact.get("session_id") != session_id:
            raise RuntimeError("QDS artifact is not bound to its trusted session")
        if artifact.get("format") != "zaslon.qds.signature.v3":
            raise RuntimeError("Live signing did not produce the basis-aware v3 artifact")
        if not artifact.get("server_attestation", {}).get("tag"):
            raise RuntimeError("QDS artifact is missing its server integrity attestation")
        if not artifact.get("reproducibility", {}).get("manifest_sha512"):
            raise RuntimeError("QDS artifact is missing machine-readable provenance")
        if not artifact.get("network_metadata", {}).get("integration", {}).get(
            "actual_correction_bits_transported"
        ):
            raise RuntimeError("SeQUeNCe did not transport actual CUDA-Q Bell bits")
        network_integration = artifact["network_metadata"]["integration"]
        expected_order = [
            "CUDA_Q_BELL_MEASUREMENT",
            "SEQUENCE_CLASSICAL_DELIVERY",
            "CUDA_Q_RECEIVER_CORRECTION_AND_MEASUREMENT",
        ]
        if network_integration.get("control_effect") != (
            "SEQUENCE_DELIVERED_BITS_CAUSALLY_DRIVE_RECEIVER_RECOVERY_STAGE"
        ) or network_integration.get("execution_order") != expected_order:
            raise RuntimeError("Signing did not use the staged causal network recovery path")
        provenance = artifact["reproducibility"]
        if provenance.get("container_image") in {None, "UNDECLARED"}:
            raise RuntimeError("Container image provenance is undeclared")
        if provenance.get("randomness_policy", {}).get("python_hash_seed") in {
            None, "UNDECLARED"
        }:
            raise RuntimeError("Python hash-seed provenance is undeclared")
        if len(str(provenance.get("source_tree_sha512", ""))) != 128:
            raise RuntimeError("Source-tree provenance digest is missing")
        if any(
            declaration.get("bases") != ["Z", "X", "Z", "X"]
            for declaration in artifact.get("declarations", [])
        ):
            raise RuntimeError("Signature declarations are not X/Z basis-aware")
        forbidden = {"private_evidence", "bob_private_bases", "bob_private_outcomes"}
        if forbidden.intersection(artifact):
            raise RuntimeError("QDS artifact exposed verifier-private evidence")

        signature_bytes = json.dumps(artifact).encode("utf-8")
        altered = require(
            client.post(
                f"{BOB}/api/v1/bob/verify",
                files={
                    "document": ("docker-acceptance.txt", b"altered", "text/plain"),
                    "signature": (artifact_name, signature_bytes, "application/json"),
                },
            )
        ).json()
        if altered.get("status") != "INVALID":
            raise RuntimeError("Document-hash tampering was not rejected")

        verified = require(
            client.post(
                f"{BOB}/api/v1/bob/verify",
                files={
                    "document": ("docker-acceptance.txt", document, "text/plain"),
                    "signature": (artifact_name, signature_bytes, "application/json"),
                },
            )
        ).json()
        if verified.get("status") != "VALID":
            raise RuntimeError(f"Bob rejected the live Alice signature: {verified}")
        if not verified.get("basis_statistics", {}).get("phase_sensitive_evidence"):
            raise RuntimeError("Bob's normal verification path lacks phase-sensitive evidence")

        baseline = require(
            client.post(
                f"{ATTACK}/api/v1/attacks/runs",
                json={
                    "qds_session_id": session_id,
                    "attack_type": "BASELINE",
                    "target": "PROTOCOL",
                    "attack_strength": 0,
                    "seed": 26141,
                },
            )
        ).json()
        if baseline.get("verification", {}).get("status") != "VALID":
            raise RuntimeError("Attack Lab baseline did not preserve a valid signature")
        if baseline.get("record_integrity", {}).get("scheme") != (
            "HMAC-SHA512-TRUSTED-SERVER-RECORD-V2"
        ) or not baseline.get("record_integrity", {}).get("key_id"):
            raise RuntimeError("Experiment integrity metadata is not authenticated")

        def run_attack(attack_type: str, target: str, **parameters):
            return require(
                client.post(
                    f"{ATTACK}/api/v1/attacks/runs",
                    json={
                        "qds_session_id": session_id,
                        "attack_type": attack_type,
                        "target": target,
                        "attack_strength": parameters.pop("strength", 1.0),
                        "seed": parameters.pop("seed", 26142),
                        "parameters": parameters,
                    },
                )
            ).json()

        intercept = run_attack("INTERCEPT_RESEND", "QUANTUM_CHANNEL")
        phase = run_attack("PAULI_MANIPULATION", "QUANTUM_STATE", pauli_operation="Z")
        correction = run_attack("CORRECTION_MITM", "CLASSICAL_CORRECTION_CHANNEL")
        partial = run_attack(
            "PARTIAL_SIGNATURE_TAMPERING", "SIGNATURE", strength=0.10, forgery_trials=16
        )
        full = run_attack(
            "FULL_FORGERY", "SIGNATURE", scenario="OBSERVED_SIGNATURE", forgery_trials=16
        )
        impersonation = run_attack("IMPERSONATION", "IDENTITY", strength=0.0)
        replay = run_attack("REPLAY", "PROTOCOL_SESSION", strength=0.0)
        if intercept["detection"]["decision"] != "ATTACK_DETECTED":
            raise RuntimeError("Intercept-resend was not detected")
        phase_basis = phase["verification"]["basis_statistics"]
        if phase_basis["Z"]["error_rate"] != 0 or phase_basis["X"]["error_rate"] != 1:
            raise RuntimeError("Normal verification did not distinguish Z phase sensitivity")
        for label, attack in {
            "correction MITM": correction,
            "partial tampering": partial,
            "full forgery": full,
            "impersonation": impersonation,
            "replay": replay,
        }.items():
            if attack["verification"]["status"] != "INVALID":
                raise RuntimeError(f"{label} was not rejected")

        network = require(
            client.post(
                f"{ATTACK}/api/v1/attacks/network",
                json={
                    "requested_bell_pairs": 4,
                    "include_charlie": True,
                    "correction_flip_mask": 0,
                    "seed": 26141,
                },
            )
        ).json()
        if network.get("engine") != "SeQUeNCe" or not network.get(
            "gate_to_cudaq", {}
        ).get("allowed"):
            raise RuntimeError("SeQUeNCe network gate failed")
        if network.get("nodes") != ["Alice", "Bob", "Charlie"]:
            raise RuntimeError("Charlie was not connected to the network experiment")

        decrypted = require(
            client.post(
                f"{BOB}/api/v1/bob/decrypt",
                json={
                    "encrypted_package": signed["encryption"],
                    "passphrase": "docker-acceptance-passphrase",
                },
            )
        )
        if decrypted.content != document:
            raise RuntimeError("Authenticated payload decryption did not round-trip")

        # Role-specific reverse proxies must reject cross-role paths.
        require(client.get(f"{BOB}/api/v1/attacks/runs"), expected=403)
        require(client.post(f"{ATTACK}/api/v1/bob/verify"), expected=403)

    report = {
        "schema": "zaslon.docker-acceptance.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASSED",
        "session_id": session_id,
        "artifact_filename": artifact_name,
        "signing_engine": signed["quantum"]["engine"],
        "signing_target": signed["quantum"]["target"],
        "staged_network_recovery": "PASSED",
        "network_execution_order": expected_order,
        "receiver_state_continuity": network_integration.get(
            "receiver_state_continuity"
        ),
        "bob_verification": verified["status"],
        "tampered_document": altered["status"],
        "attack_baseline": baseline["verification"]["status"],
        "intercept_resend": intercept["detection"]["decision"],
        "phase_attack_x_error": phase_basis["X"]["error_rate"],
        "correction_mitm": correction["verification"]["status"],
        "partial_tampering": partial["verification"]["status"],
        "full_forgery": full["verification"]["status"],
        "impersonation": impersonation["verification"]["status"],
        "replay": replay["verification"]["status"],
        "sequence_version": network.get("version"),
        "charlie_network": "PASSED",
        "artifact_attestation": "PASSED",
        "experiment_integrity_metadata": "PASSED",
        "reproducibility_manifest": "PASSED",
        "container_image_provenance": provenance["container_image"],
        "source_tree_sha512": provenance["source_tree_sha512"],
        "decryption": "PASSED",
        "role_isolation": "PASSED",
        "runtime_health": {
            "protocol_version": health.get("protocol_version"),
            "database": health.get("database"),
            "cudaq": health.get("quantum", {}).get("cudaq"),
            "gpu": health.get("quantum", {}).get("gpu"),
            "gpu_name": health.get("quantum", {}).get("gpu_name"),
            "execution_target": health.get("quantum", {}).get("execution_target"),
            "sequence": health.get("quantum", {}).get("sequence"),
            "staged_network_receiver_recovery": health.get("quantum", {}).get(
                "staged_network_receiver_recovery"
            ),
        },
    }
    output = os.getenv("ZASLON_ACCEPTANCE_OUTPUT")
    if output:
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
