from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import time
from typing import Any

from .config import settings


@dataclass(frozen=True)
class SequenceNetworkConfig:
    distance_m: float = 1000.0
    attenuation_db_per_m: float = 0.0
    classical_delay_ps: int = 5_000_000
    sample_pairs: int = 32
    include_charlie: bool = False
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.distance_m <= 0:
            raise ValueError("SeQUeNCe distance must be positive")
        if self.attenuation_db_per_m < 0:
            raise ValueError("SeQUeNCe attenuation cannot be negative")
        if self.classical_delay_ps < 0:
            raise ValueError("SeQUeNCe classical delay cannot be negative")
        if not 1 <= self.sample_pairs <= 4096:
            raise ValueError("SeQUeNCe sample_pairs must be between 1 and 4096")


@dataclass(frozen=True)
class _CorrectionEnvelope:
    receiver: str
    m0: int
    m1: int
    integrity: str = "UNMODIFIED"


def configured_network(
    *, seed: int, include_charlie: bool = False, sample_pairs: int | None = None
) -> SequenceNetworkConfig:
    return SequenceNetworkConfig(
        distance_m=settings.sequence_distance_m,
        attenuation_db_per_m=settings.sequence_attenuation_db_per_m,
        classical_delay_ps=settings.sequence_classical_delay_ps,
        sample_pairs=(settings.sequence_sample_pairs if sample_pairs is None else sample_pairs),
        include_charlie=include_charlie,
        seed=seed,
    )


def simulate_sequence_network(
    *,
    requested_bell_pairs: int,
    config: SequenceNetworkConfig,
    correction_flip_mask: int = 0,
    correction_messages: list[tuple[int, int]] | None = None,
    correction_sender: str = "Alice",
    correction_receiver: str = "Bob",
    include_private_delivery_receipts: bool = False,
) -> dict[str, Any]:
    """Run a bounded SeQUeNCe delivery/timing experiment around CUDA-Q work.

    SeQUeNCe models the network envelope and gates whether the circuit experiment
    may proceed. When supplied, correction messages are actual CUDA-Q Bell bits;
    otherwise an explicit deterministic health vector is used. CUDA-Q remains the
    sole circuit/state engine. The bounded sample is not misrepresented as physical
    distribution of every simulated Bell pair.
    """

    if requested_bell_pairs < 1:
        raise ValueError("requested_bell_pairs must be positive")
    if correction_flip_mask not in {0, 1, 2, 3}:
        raise ValueError("correction_flip_mask must be 0, 1, 2, or 3")
    if correction_sender not in {"Alice", "Bob"}:
        raise ValueError("correction_sender must be Alice or Bob")
    if correction_receiver not in {"Alice", "Bob", "Charlie"}:
        raise ValueError("correction_receiver must be Alice, Bob, or Charlie")
    if correction_sender == correction_receiver:
        raise ValueError("correction sender and receiver must be different nodes")
    if correction_sender == "Bob" and correction_receiver != "Alice":
        raise ValueError("Bob-originated network execution currently targets Alice")
    if correction_receiver == "Charlie" and not config.include_charlie:
        raise ValueError("Charlie correction delivery requires include_charlie=True")
    try:
        import sequence
        from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
        from sequence.components.photon import Photon
        from sequence.kernel.event import Event
        from sequence.kernel.process import Process
        from sequence.kernel.timeline import Timeline
        from sequence.topology.node import Node
    except ImportError as exc:
        raise RuntimeError(
            "SeQUeNCe is required by the Docker quantum worker but is unavailable."
        ) from exc

    class AuditNode(Node):
        def __init__(self, name, timeline):
            super().__init__(name, timeline)
            self.received_qubits: list[dict[str, Any]] = []
            self.received_messages: list[dict[str, Any]] = []

        def receive_qubit(self, src, qubit) -> None:
            now = self.timeline.now() if callable(getattr(self.timeline, "now", None)) else 0
            self.received_qubits.append({"source": src, "name": qubit.name, "time_ps": int(now)})

        def receive_message(self, src, msg) -> None:
            now = self.timeline.now() if callable(getattr(self.timeline, "now", None)) else 0
            self.received_messages.append(
                {
                    "source": src,
                    "m0": int(msg.m0),
                    "m1": int(msg.m1),
                    "integrity": msg.integrity,
                    "time_ps": int(now),
                }
            )

    sample_pairs = min(requested_bell_pairs, config.sample_pairs)
    quantum_delay_ps = int(config.distance_m / 0.0002)
    spacing_ps = 20_000
    stop_time = max(10_000_000, quantum_delay_ps, config.classical_delay_ps) + sample_pairs * spacing_ps
    timeline = Timeline(stop_time)
    alice = AuditNode("Alice", timeline)
    bob = AuditNode("Bob", timeline)
    alice.set_seed(config.seed)
    bob.set_seed(config.seed + 1)
    nodes: list[Any] = [alice, bob]
    charlie = None
    if config.include_charlie:
        charlie = AuditNode("Charlie", timeline)
        charlie.set_seed(config.seed + 2)
        nodes.append(charlie)

    primary_quantum_name = (
        "qchannel_bob_alice" if correction_sender == "Bob" else "qchannel_alice_bob"
    )
    primary_quantum_source = bob if correction_sender == "Bob" else alice
    primary_quantum_destination = alice if correction_sender == "Bob" else bob
    quantum_channel = QuantumChannel(
        primary_quantum_name,
        timeline,
        attenuation=config.attenuation_db_per_m,
        distance=config.distance_m,
    )
    quantum_channel.set_ends(primary_quantum_source, primary_quantum_destination.name)
    classical_ab = ClassicalChannel(
        "cchannel_alice_bob",
        timeline,
        config.distance_m,
        delay=config.classical_delay_ps,
    )
    classical_ba = ClassicalChannel(
        "cchannel_bob_alice",
        timeline,
        config.distance_m,
        delay=config.classical_delay_ps,
    )
    classical_ab.set_ends(alice, bob.name)
    classical_ba.set_ends(bob, alice.name)

    quantum_channels = [quantum_channel]
    classical_channels = [classical_ab, classical_ba]
    if charlie is not None:
        quantum_ac = QuantumChannel(
            "qchannel_alice_charlie",
            timeline,
            attenuation=config.attenuation_db_per_m,
            distance=config.distance_m,
        )
        quantum_ac.set_ends(alice, charlie.name)
        classical_ac = ClassicalChannel(
            "cchannel_alice_charlie",
            timeline,
            config.distance_m,
            delay=config.classical_delay_ps,
        )
        classical_ca = ClassicalChannel(
            "cchannel_charlie_alice",
            timeline,
            config.distance_m,
            delay=config.classical_delay_ps,
        )
        classical_ac.set_ends(alice, charlie.name)
        classical_ca.set_ends(charlie, alice.name)
        quantum_channels.append(quantum_ac)
        classical_channels.extend([classical_ac, classical_ca])

    # A standalone health experiment uses a declared deterministic control
    # vector.  Production callers pass Bell-measurement bits returned by CUDA-Q;
    # SeQUeNCe must never invent quantum outcomes with a PRNG.
    source_messages = (
        list(correction_messages)
        if correction_messages is not None
        else [(0, 0)] * sample_pairs
    )
    if len(source_messages) < sample_pairs:
        raise ValueError("correction_messages must cover every sampled Bell-pair delivery")
    if any(m0 not in {0, 1} or m1 not in {0, 1} for m0, m1 in source_messages[:sample_pairs]):
        raise ValueError("correction messages must contain binary m0/m1 values")
    started = time.perf_counter()
    for index in range(sample_pairs):
        send_time = index * spacing_ps
        photon = Photon(
            f"bell-half-{index}",
            timeline,
            wavelength=1550,
            location=primary_quantum_source,
            quantum_state=(complex(1), complex(0)),
        )
        timeline.schedule(
            Event(
                send_time,
                Process(
                    primary_quantum_source,
                    "send_qubit",
                    [primary_quantum_destination.name, photon],
                ),
            )
        )
        m0, m1 = source_messages[index]
        used_m0 = m0 ^ ((correction_flip_mask >> 1) & 1)
        used_m1 = m1 ^ (correction_flip_mask & 1)
        envelope = _CorrectionEnvelope(
            receiver=primary_quantum_destination.name,
            m0=used_m0,
            m1=used_m1,
            integrity="UNMODIFIED" if correction_flip_mask == 0 else "TAMPERED_FOR_EXPERIMENT",
        )
        timeline.schedule(
            Event(
                send_time,
                Process(
                    primary_quantum_source,
                    "send_message",
                    [primary_quantum_destination.name, envelope],
                ),
            )
        )
        if charlie is not None and correction_sender == "Alice":
            charlie_photon = Photon(
                f"bell-half-charlie-{index}",
                timeline,
                wavelength=1550,
                location=alice,
                quantum_state=(complex(1), complex(0)),
            )
            timeline.schedule(
                Event(send_time, Process(alice, "send_qubit", [charlie.name, charlie_photon]))
            )
            charlie_envelope = _CorrectionEnvelope(
                receiver="Charlie",
                m0=used_m0,
                m1=used_m1,
                integrity=envelope.integrity,
            )
            timeline.schedule(
                Event(send_time, Process(alice, "send_message", [charlie.name, charlie_envelope]))
            )

    timeline.init()
    timeline.run()
    runtime_ms = (time.perf_counter() - started) * 1000
    correction_node = {
        "Alice": alice,
        "Bob": bob,
        "Charlie": charlie,
    }[correction_receiver]
    delivered = len(correction_node.received_qubits)
    messages = len(correction_node.received_messages)
    delivered_by_node = {"Bob": delivered}
    messages_by_node = {"Bob": messages}
    if charlie is not None:
        delivered_by_node["Charlie"] = len(charlie.received_qubits)
        messages_by_node["Charlie"] = len(charlie.received_messages)
    source_digest = hashlib.sha512(
        "".join(f"{m0}{m1}" for m0, m1 in source_messages[:sample_pairs]).encode("ascii")
    ).hexdigest()
    version = getattr(sequence, "__version__", "1.0.0")
    result = {
        "engine": "SeQUeNCe",
        "version": str(version),
        "claim_scope": "BOUNDED_DISCRETE_EVENT_NETWORK_ENVELOPE",
        "nodes": [node.name for node in nodes],
        "quantum_channels": [
            {
                "name": channel.name,
                "source": "Bob" if channel.name.startswith("qchannel_bob") else "Alice",
                "destination": (
                    "Alice" if channel.name.endswith("alice") else (
                        "Charlie" if channel.name.endswith("charlie") else "Bob"
                    )
                ),
                "distance_m": config.distance_m,
                "attenuation_db_per_m": config.attenuation_db_per_m,
                "propagation_delay_ps": int(getattr(channel, "delay", quantum_delay_ps)),
                "resource_representation": "BOB_OR_CHARLIE_BOUND_BELL_HALF_DELIVERY_TOKEN",
            }
            for channel in quantum_channels
        ],
        "classical_channels": [
            {
                "name": channel.name,
                "source": "Charlie" if channel.name.startswith("cchannel_charlie") else (
                    "Bob" if channel.name.startswith("cchannel_bob") else "Alice"
                ),
                "destination": "Charlie" if channel.name.endswith("charlie") else (
                    "Bob" if channel.name.endswith("bob") else "Alice"
                ),
            }
            for channel in classical_channels
        ],
        "requested_bell_pairs": requested_bell_pairs,
        "sampled_distribution_attempts": sample_pairs,
        "sampled_deliveries": delivered,
        "sampled_losses": sample_pairs - delivered,
        "sampled_delivery_rate": delivered / sample_pairs,
        "sampled_deliveries_by_node": delivered_by_node,
        "classical_correction_messages_delivered": messages,
        "classical_messages_delivered_by_node": messages_by_node,
        "correction_message_source": (
            "CUDA_Q_BELL_MEASUREMENT_RESULTS"
            if correction_messages is not None
            else "DECLARED_DETERMINISTIC_HEALTH_VECTOR"
        ),
        "correction_source_sha512": source_digest,
        "correction_integrity": "UNMODIFIED" if correction_flip_mask == 0 else "TAMPERED_FOR_EXPERIMENT",
        "network_simulation_duration_ps": int(
            timeline.now() if callable(getattr(timeline, "now", None)) else stop_time
        ),
        "wall_clock_runtime_ms": round(runtime_ms, 3),
        "configuration": asdict(config),
        "gate_to_cudaq": {
            "allowed": delivered == sample_pairs and messages == sample_pairs,
            "rule": "Every staged Bell-half resource and classical correction envelope must reach the selected receiver.",
        },
        "integration": {
            "network_physics": "SeQUeNCe",
            "circuit_state_physics": "CUDA-Q",
            "shared_state_claim": False,
            "actual_correction_bits_transported": correction_messages is not None,
            "correction_sender": correction_sender,
            "correction_receiver": correction_receiver,
            "quantum_state_handoff": "DISTRIBUTION_RESOURCE_TOKEN_ONLY",
            "note": (
                "SeQUeNCe transports actual CUDA-Q Bell-measurement control bits when supplied "
                "and models delivery of the verifier-bound Bell-half resource. It does not claim "
                "that a CUDA-Q statevector is physically shared between simulator processes."
            ),
        },
    }
    if include_private_delivery_receipts:
        # This field exists only for the in-process recovery stage. Callers must
        # remove it before persisting or returning public network metadata.
        result["_private_delivered_correction_messages"] = [
            (int(message["m0"]), int(message["m1"]))
            for message in correction_node.received_messages
        ]
    return result
