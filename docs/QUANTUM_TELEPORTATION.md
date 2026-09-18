# Quantum Teleportation Architecture — Zaslon-QDS

NVIDIA CUDA-Q 3-Qubit Teleportation Protocol for Quantum Digital Signatures (SIH 26141).

---

## 1. The 3-Qubit Teleportation Model

Quantum teleportation is the core quantum primitive utilized in Zaslon-QDS. A pure state $|\psi\rangle$ is transmitted from Alice to Bob without physically sending the qubit, utilizing a pre-shared entangled Bell pair and 2 classical communication bits.

### Qubit Allocations
1. **$Q_0$ (Message Qubit)**: Owned by Alice. Initialized to the state determined by the SHA-512 digest:
   $$|\psi\rangle = \cos\left(\frac{\theta}{2}\right)|0\rangle + e^{i\phi}\sin\left(\frac{\theta}{2}\right)|1\rangle$$
2. **$Q_1$ (Alice's Entangled Qubit)**: Initialized to $|0\rangle$, then entangled with $Q_2$.
3. **$Q_2$ (Bob's Entangled Qubit)**: Initialized to $|0\rangle$. After teleportation, this qubit reconstructs $|\psi\rangle$.

---

## 2. Mathematical Circuit Steps

### Step 1: Bell Pair Creation
Alice and Bob share an EPR pair $|\Phi^+\rangle$:
$$|\Phi^+\rangle_{12} = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)_{12}$$
Achieved by applying Hadamard $H$ to $Q_1$, followed by CNOT with control $Q_1$ and target $Q_2$:
$$\text{CX}_{1 \to 2} (H_1 \otimes I_2) |00\rangle_{12} = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)_{12}$$

### Step 2: Full Three-Qubit Composite State
The three-qubit state $|\Psi_{\text{total}}\rangle$ prior to Alice's Bell measurement is:
$$|\Psi_0\rangle = |\psi\rangle_0 \otimes |\Phi^+\rangle_{12} = \frac{1}{\sqrt{2}}\left[\alpha|0\rangle(|00\rangle + |11\rangle) + \beta|1\rangle(|00\rangle + |11\rangle)\right]$$

### Step 3: Bell Basis Interaction
Alice applies $\text{CX}_{0 \to 1}$ followed by $H_0$:
$$|\Psi_1\rangle = (H_0 \otimes I_1 \otimes I_2) \text{CX}_{0 \to 1} |\Psi_0\rangle$$

Expanding in Alice's computational basis for qubits 0 and 1:
$$|\Psi_1\rangle = \frac{1}{2}\left[ |00\rangle_{01}(\alpha|0\rangle + \beta|1\rangle)_2 + |01\rangle_{01}(\alpha|1\rangle + \beta|0\rangle)_2 + |10\rangle_{01}(\alpha|0\rangle - \beta|1\rangle)_2 + |11\rangle_{01}(\alpha|1\rangle - \beta|0\rangle)_2 \right]$$

### Step 4: Alice's Measurement
Alice measures $Q_0$ and $Q_1$ in the computational ($Z$) basis:
* Outcome $m_0 \in \{0, 1\}$ from $Q_0$.
* Outcome $m_1 \in \{0, 1\}$ from $Q_1$.

### Step 5: Conditional Classical Corrections on Bob's Qubit ($Q_2$)
Based on classical measurement pair $(m_0, m_1)$, Bob applies Pauli unitary operations:

| Outcome $(m_0, m_1)$ | State of $Q_2$ before correction | Correction Operator $U = X^{m_1} Z^{m_0}$ | State of $Q_2$ after correction |
| :---: | :---: | :---: | :---: |
| **00** | $\alpha|0\rangle + \beta|1\rangle$ | $I$ | $\alpha|0\rangle + \beta|1\rangle = |\psi\rangle$ |
| **01** | $\alpha|1\rangle + \beta|0\rangle$ | $X$ | $\alpha|0\rangle + \beta|1\rangle = |\psi\rangle$ |
| **10** | $\alpha|0\rangle - \beta|1\rangle$ | $Z$ | $\alpha|0\rangle + \beta|1\rangle = |\psi\rangle$ |
| **11** | $\alpha|1\rangle - \beta|0\rangle$ | $ZX$ | $\alpha|0\rangle + \beta|1\rangle = |\psi\rangle$ |

### Step 6: Verification Measurement
Bob applies basis transformation (if $X$-basis was prepared, Bob applies Hadamard $H$ on $Q_2$) and measures $Q_2$. In an undisturbed transmission:
$$\text{Pr}(\text{Observed} = \text{Expected}) = 1.0$$
Any eavesdropping, intercept-resend, state forgery, or tampering disturbs the entanglement, causing measurable mismatch between expected and observed outcomes.

---

## 3. CUDA-Q Implementation

The teleportation kernel is implemented using NVIDIA CUDA-Q:
```python
import cudaq

@cudaq.kernel
def three_qubit_teleport_kernel(theta: float, phi: float, basis_flag: int):
    q = cudaq.qvector(3)

    # 1. State preparation
    ry(theta, q[0])
    rz(phi, q[0])

    # 2. Bell pair generation
    h(q[1])
    cx(q[1], q[2])

    # 3. Alice entanglement
    cx(q[0], q[1])
    h(q[0])

    # 4. Measurements
    m0 = mz(q[0])
    m1 = mz(q[1])

    # 5. Conditional feed-forward corrections
    if m1:
        x(q[2])
    if m0:
        z(q[2])

    # 6. Verification measurement in target basis
    if basis_flag == 1:
        h(q[2])

    mz(q[2])
```
CUDA-Q executes the circuits on the designated target backend (`default`, `nvidia`, etc.) without random approximations.
