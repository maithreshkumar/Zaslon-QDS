# ZASLON-QDS Security and Adversary Model

Status: research prototype model, not a complete or standardized QDS security
proof. This document defines the assumptions used by the executable experiments.

## Claim boundary

ZASLON-QDS simulates three-qubit, discrete-variable teleportation and evaluates
cryptographic bindings, one-time use, measurement disturbance, and statistical
detectors. It does not implement a physical quantum network and has not established
information-theoretic unforgeability, transferability, or non-repudiation for the
whole construction. The 5% default verification threshold is a configured
experimental operating point until calibration output supports a selected value.

## Attacker classes

| Model | Knows | Does not know | Can control |
|---|---|---|---|
| Honest participant | Protocol, own document/artifact/evidence | Other verifier evidence and server credentials | Nothing adversarial |
| External forger | Protocol and target message/hash; an observed artifact only in the explicitly named observed-signature scenario | Unobserved nonce, trusted evidence, role credentials, and legitimate declaration key bits in the independent-forger experiment | Submits a newly constructed artifact |
| Malicious recipient | Received signature and its own verifier evidence | Another verifier's independent evidence and signer secrets | Its forwarding/submission behavior |
| Impersonator | Public role names and protocol | Authenticated role secret/context | User-supplied identity claims only |
| Replay attacker | A previously valid document/artifact | Ability to reset the atomic consume ledger | Resubmission timing, including concurrency |
| Quantum-channel attacker | Protocol and channel timing | Random control-state basis before interaction and role credentials | Intercept/resend or a declared Pauli operation at a named quantum boundary |
| Correction-channel MITM | Transmitted Bell-result bits | Verifier evidence and role credentials | Alice-to-Bob classical correction bits |

Every stored attack result includes the selected model and capabilities. Attack
runs are counterfactual executions using the same logical session configuration;
they do not claim to alter qubits after a past transmission was measured.

## Evidence boundaries

Production v3 signature evidence alternates Z- and X-basis Pauli eigenstates and
reports per-basis usable measurements, mismatches and error rates. Dedicated Z/X
channel-control diagnostics remain separate fresh transmissions and are never
substituted for signature declarations. Both paths expose phase-sensitive
disturbance, but neither is a formal QDS security proof.

For Docker signing, execution is staged as CUDA-Q Bell measurement, SeQUeNCe
classical delivery, then CUDA-Q receiver correction/measurement. The delivered
bits therefore determine receiver correction. CUDA-Q 0.15 cannot retain the same
q2 allocation while the Python SeQUeNCe timeline runs, so the second kernel
reconstructs the exact conditional receiver state from the measured Bell result.
This is a declared co-simulation boundary, not a claim that the two simulators
share one persistent physical qubit or statevector.

Noise is composed in this order: Bell source, Bell-distribution X/Z/depolarizing
events, declared attacker boundary, teleportation and feed-forward correction,
Bob output/memory X/Z/depolarizing events, basis rotation, then classical readout
error. Each event is an independent Bernoulli draw. Pauli effects compose; a later
depolarizing event never silently replaces an earlier event.

## Statistical meaning

Fisher-test p-values are tail probabilities under a null model. They are not attack
probabilities, confidence that an attack happened, or probabilities that the null
is true. Pre-declared test families use Holm family-wise correction. Wilson
intervals quantify uncertainty in repeated empirical success proportions.

The optional binomial forgery calculation uses
`X ~ Binomial(L, p_e)` and `P_accept = P[X <= floor(tL)]`. It is a **REFERENCE
BOUND** unless independent Bernoulli mismatch behavior and a fixed, justified
attacker error probability are both established for the scenario. It must not be
presented as a universal ZASLON-QDS security guarantee.

## Current security-capability status

- Teleportation core: validated across explicit NumPy, Qiskit Aer, and CUDA-Q tests.
- Artifact/session binding and replay: implementation-supported and tested.
- Channel attack detection: empirically tested in normal X/Z evidence and independent controls.
- Forgery: independent empirical experiments plus a restricted reference model.
- Transferability/non-repudiation: experimental multi-verifier work only; no formal proof.
- Information-theoretic security: not formally proven.
