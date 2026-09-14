from __future__ import annotations

import importlib.util

import pytest

from zaslon_shared.network import SequenceNetworkConfig, simulate_sequence_network


@pytest.mark.skipif(importlib.util.find_spec("sequence") is None, reason="SeQUeNCe is installed in the Docker worker")
def test_sequence_connects_nodes_quantum_and_classical_channels():
    result = simulate_sequence_network(
        requested_bell_pairs=8,
        config=SequenceNetworkConfig(
            distance_m=1000,
            attenuation_db_per_m=0,
            classical_delay_ps=5_000_000,
            sample_pairs=8,
            include_charlie=True,
            seed=26141,
        ),
    )
    assert result["engine"] == "SeQUeNCe"
    assert result["nodes"] == ["Alice", "Bob", "Charlie"]
    assert len(result["quantum_channels"]) == 2
    assert len(result["classical_channels"]) == 4
    assert result["sampled_deliveries"] == 8
    assert result["classical_correction_messages_delivered"] == 8
    assert result["gate_to_cudaq"]["allowed"] is True
    assert result["integration"]["shared_state_claim"] is False
    assert result["sampled_deliveries_by_node"]["Charlie"] == 8


@pytest.mark.skipif(importlib.util.find_spec("sequence") is None, reason="SeQUeNCe is installed in the Docker worker")
def test_sequence_correction_tampering_is_explicitly_labelled():
    result = simulate_sequence_network(
        requested_bell_pairs=2,
        config=SequenceNetworkConfig(sample_pairs=2, seed=7),
        correction_flip_mask=3,
    )
    assert result["correction_integrity"] == "TAMPERED_FOR_EXPERIMENT"


@pytest.mark.skipif(importlib.util.find_spec("sequence") is None, reason="SeQUeNCe is installed in the Docker worker")
def test_sequence_transports_supplied_quantum_correction_results_without_random_generation():
    controls = [(0, 0), (0, 1), (1, 0), (1, 1)]
    result = simulate_sequence_network(
        requested_bell_pairs=4,
        config=SequenceNetworkConfig(sample_pairs=4, seed=11),
        correction_messages=controls,
        include_private_delivery_receipts=True,
    )
    assert result["correction_message_source"] == "CUDA_Q_BELL_MEASUREMENT_RESULTS"
    assert result["integration"]["actual_correction_bits_transported"] is True
    assert result.pop("_private_delivered_correction_messages") == controls


@pytest.mark.skipif(importlib.util.find_spec("sequence") is None, reason="SeQUeNCe is installed in the Docker worker")
def test_sequence_returns_charlie_delivery_controls_to_charlie_recovery_only():
    controls = [(0, 1), (1, 0)]
    result = simulate_sequence_network(
        requested_bell_pairs=2,
        config=SequenceNetworkConfig(sample_pairs=2, include_charlie=True, seed=12),
        correction_messages=controls,
        correction_receiver="Charlie",
        include_private_delivery_receipts=True,
    )
    assert result["integration"]["correction_receiver"] == "Charlie"
    assert result.pop("_private_delivered_correction_messages") == controls
    assert result["gate_to_cudaq"]["allowed"] is True


@pytest.mark.skipif(importlib.util.find_spec("sequence") is None, reason="SeQUeNCe is installed in the Docker worker")
def test_sequence_supports_bob_to_alice_reverse_signing_path():
    controls = [(1, 1), (0, 0)]
    result = simulate_sequence_network(
        requested_bell_pairs=2,
        config=SequenceNetworkConfig(sample_pairs=2, seed=13),
        correction_messages=controls,
        correction_sender="Bob",
        correction_receiver="Alice",
        include_private_delivery_receipts=True,
    )
    assert result["quantum_channels"][0]["source"] == "Bob"
    assert result["quantum_channels"][0]["destination"] == "Alice"
    assert result.pop("_private_delivered_correction_messages") == controls
    assert result["gate_to_cudaq"]["allowed"] is True
