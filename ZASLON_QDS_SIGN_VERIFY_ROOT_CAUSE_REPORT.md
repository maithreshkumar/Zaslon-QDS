# ZASLON-QDS Sign/Verify Root-Cause Report

Date: 2026-09-14  
Final status: **PASS**

## 1. Exact root cause

The failed manual run did not pair Alice's original document with the artifact generated for that document. The generated `SIH26141.pdf.qds.json` was accidentally submitted to Alice's signing page as a new source document. That created a second, nested signature session for the JSON artifact itself. When the nested artifact was later paired with the original PDF, Bob correctly rejected it because the trusted SHA-512 document binding was for the JSON bytes, not the PDF bytes.

Database evidence:

| Session | Signed source name | Signature ID | Trusted SHA-512 | Consumed before diagnosis |
| --- | --- | --- | --- | --- |
| `QDS-20260914-31A869AD6C` | `SIH26141.pdf` | `SIG-20260914-3FF9B108C8` | `b9856152c10c389c75114cb6d7bba4f9bf3ff8d9e6f10516d439fcfaeb9c72bda3641dfe67e494e0502881ae2ea1e0c415185746d15141df5246df68834ae87c` | No |
| `QDS-20260914-ECCCA41BD8` | `SIH26141.pdf.qds.json` | `SIG-20260914-F22B663E79` | `4224820faab560ccc62b54f730b768ee8f5f4ed85de5c31529e1531db06f0d06e658daa8eb4e4b4bca1bb3e43a84b31cb6c29ebddd3662f1995858303c0cea55` | No |

The SHA-512 of the first artifact using the frontend's exact `JSON.stringify(value, null, 2)` representation was also `4224820f...c0cea55`. This is a byte-for-byte cryptographic match with the second session's trusted document hash and proves the artifact was re-signed as a document.

## 2. Why the legitimate-looking pair became INVALID

The pair looked related because both filenames began with `SIH26141.pdf`, but the second artifact authenticated the first `.qds.json`, not the original PDF. Bob's strict document-binding check therefore rejected the mismatched pair. The verifier did not fabricate mismatches and did not consume either failed session.

## 3. Repair made

The smallest safe repair was added at the Alice/Bob signing boundary:

- `read_signing_document()` reads the source bytes normally.
- When a selected filename ends in `.qds.json`, it checks whether the content is a valid ZASLON `SignatureArtifact`.
- A real QDS artifact is rejected with HTTP 400 and a clear instruction to open Bob's verifier and upload the original document plus the artifact separately.
- Ordinary JSON documents are still signable, even when their filename happens to end in `.qds.json`, unless their content validates as an actual QDS artifact.
- The same guard is applied to both Alice and Bob signing routes.

No verifier rule was removed or relaxed.

## 4. Component-by-component finding

| Area requested for audit | Finding |
| --- | --- |
| SHA-512 | Correct and directly involved: it exposed the document/artifact mismatch. Exact raw bytes are hashed on both paths. |
| Session lookup | Correct. The uploaded artifact's `session_id` selected its exact trusted session. No “latest session” lookup was used. |
| Signature/export | Correct. Fresh exact endpoint bytes verified. A diagnostic PowerShell copy was separately rejected because reserialization changed the signed UTC timestamp representation; this confirmed HMAC strictness and was not the user bug. |
| Candidate selection | Correct in the honest regression: all 512 digest positions selected the expected candidate. |
| Bob evidence mapping | Correct: 512 private-evidence positions existed for each checked session; fresh sessions produced 2,048 usable measurements and zero mismatches. |
| Teleportation outcome semantics | Correct in the tested path: corrected CUDA-Q outcomes matched Bob's trusted evidence. |
| X/Z basis handling | Correct: 1,024 usable Z and 1,024 usable X measurements in the browser run; both error rates were 0%. |
| Mismatch denominator | Correct: `mismatches / usable_measurements`; honest result was `0 / 2048 = 0`. |
| Threshold | Correct: trusted `0.05` was displayed as 5.0%; provenance remained `CONFIGURED_EXPERIMENTAL`. |
| Replay/consumption | Correct: signing, download, failed document checks, and tampered artifacts did not consume sessions. The first successful verification consumed the nonce; the second was `REPLAY_REJECTED`. |
| Protocol version | Correct and consistent: `0.3.0-basis-aware-teleportation`. |
| Database transaction/timing | No incomplete evidence or READY-before-commit race was found. Browser-created sessions had all 512 evidence positions before verification. |
| Worker race | Not observed. Alice returned only after the committed worker result and trusted evidence were available. |
| Serialization/schema | Strict schema and server HMAC worked. Signed artifacts must be transferred byte-preservingly; reserializing a signed JSON object is correctly treated as tampering. |

## 5. Diagnostic comparison

A backend-test-only diagnostic now reports the first positions with:

`Position`, `Digest bit`, `Selected candidate`, `Disclosed key bit`, `Disclosed basis`, `Stored Bob outcome`, `Stored Bob basis`, `Usable?`, `Expected logical result`, `Actual comparison`, and `Mismatch reason`.

It is not exposed through React or any public API, so Bob's private evidence remains private.

## 6. Automated regression results

Command:

```powershell
python -m pytest shared/backend/tests/test_api.py shared/backend/tests/test_signature_security.py -q
```

Result: **12 passed in 38.34 seconds**.

The new deterministic regression performed 10 independent honest Sign → Verify cycles using seeds `261500` through `261509`:

- Honest VALID: 10
- Honest INVALID: 0
- Honest pass rate: 100%
- Mean mismatch rate: 0.0%
- Maximum mismatch rate: 0.0%
- Usable measurements per signature: 2,048
- Threshold: 5.0% (`CONFIGURED_EXPERIMENTAL`)
- Modified document: `DOCUMENT_HASH_MISMATCH`
- Tampered declaration: `SERVER_ATTESTATION_FAILED`
- Wrong signature ID: `SERVER_ATTESTATION_FAILED`
- Missing trusted session: `UNKNOWN_SESSION`
- First valid verification: VALID
- Second valid verification: `REPLAY_REJECTED`

These 10 deterministic cycles use the repository's reference test engine. They are supplemented by two complete real-browser cycles using the live CUDA-Q `nvidia` target.

## 7. Code changes

Modified:

- `shared/backend/zaslon_shared/http.py`
- `Alice/backend/alice_service/communication.py`
- `Alice/backend/alice_service/router.py`
- `Bob/backend/bob_service/communication.py`
- `Bob/backend/bob_service/router.py`
- `shared/backend/tests/test_api.py`
- `shared/backend/tests/test_signature_security.py`

Created:

- `ZASLON_QDS_SIGN_VERIFY_ROOT_CAUSE_REPORT.md`

Database migrations: none.  
Dependencies added: none.  
Verification thresholds changed: none.  
Schema changes: none.

## 8. Real browser end-to-end validation

1. **Test file:** `shared/backend/zaslon_shared/__init__.py`
2. **File size:** 77 bytes
3. **Calculated SHA-512:** `a989174e65841ea10ab9626b947d372ba8b993f90505487ab59eeb19773055f2a8bd3400d3746a84a83db12277c77df3e2291a68fa4bc7a650538eb377864483`
4. **Browser URLs:** Alice `http://127.0.0.1:5173/`, Attack `http://127.0.0.1:5174/`, Bob `http://127.0.0.1:5175/`
5. **First Sign result:** SESSION COMMITTED
6. **First session ID:** `QDS-20260914-FEAA350116`
7. **First signature ID:** `SIG-20260914-EC364C2F35`
8. **Generated filename:** `__init__.py.qds.json`
9. **Backend job result:** completed; 4,096 sequential teleportations/Bell pairs; 2,048 usable verifier measurements; zero baseline errors
10. **CUDA-Q target:** `nvidia`, GPU `NVIDIA GeForce RTX 4050 Laptop GPU`, no fallback
11. **Honest Verify:** VALID
12. **Mismatch count:** 0
13. **Usable measurements:** 2,048
14. **Mismatch rate:** 0.0%
15. **Threshold:** 5.0%, `CONFIGURED_EXPERIMENTAL`
16. **Modified-file result:** INVALID, `DOCUMENT_HASH_MISMATCH`
17. **Tampered-signature result:** INVALID, `SERVER_ATTESTATION_FAILED`
18. **Replay result:** INVALID, `REPLAY_REJECTED`
19. **Attack Lab:** Baseline completed as VALID/NO ATTACK DETECTED; intercept–resend completed as INVALID/ATTACK DETECTED; Pauli Z completed as INVALID/ATTACK DETECTED with X-basis phase sensitivity
20. **Browser console errors:** none on Alice, Bob, or Attack validation tabs before restart; none on Alice/Bob after restart
21. **Failed network requests:** none in the successful flows
22. **MySQL cross-check:** exact session/signature/hash mappings; 512 private-evidence positions per tested session; only successful verification consumed the nonce; failed negative tests did not consume it
23. **Docker restart:** PASS. `docker compose down` was used without `-v`; after `docker compose up -d`, MySQL, API, frontend, and quantum worker were all healthy and all prior sessions/evidence persisted
24. **Complete real-browser Sign → Verify cycles:** 2, including one fresh cycle after restart
25. **Final browser acceptance:** **PASS**

The post-restart browser cycle created:

- Session: `QDS-20260914-5A8C152298`
- Signature: `SIG-20260914-BB70812231`
- Result: VALID
- Hash binding: MATCH
- Usable evidence: 2,048
- Z-basis error: 0.00%
- X-basis error: 0.00%
- Mismatch rate: 0.00%
- Verification latency: 85.83 ms
- MySQL private-evidence positions: 512
- Consumed only after successful verification: yes

The in-app browser triggered the application's automatic JSON download, but its automation surface did not expose the blob-download filesystem location. For upload verification, the exact artifact bytes were materialized from the same authenticated session download endpoint; no JSON reserialization was used.

## 9. Final security confirmation

- SHA-512 remains mandatory.
- Server-side HMAC attestation remains mandatory.
- Exact session, signature, nonce, signer, and verifier bindings remain mandatory.
- Bob's trusted evidence stays server-side.
- The 5% threshold stays server-controlled and experimentally labelled.
- One-time replay protection remains enabled.
- Failed checks do not consume the signature.
- No response is hard-coded VALID.
- No mismatch is ignored.
- No threshold was raised.
- No database row was manually edited.
- No verification security check was weakened.

The observed user failure is fixed by preventing the accidental signing of a QDS artifact as a new source document, while all strict verification behavior remains fail-closed.
