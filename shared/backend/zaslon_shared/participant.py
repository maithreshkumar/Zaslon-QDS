from __future__ import annotations

import time
import platform

from .config import settings
from .protocol import create_qds_session, get_session_summary, verify_document
from .quantum import NoiseConfig, create_quantum_engine


def _process_peak_rss_mb() -> float | None:
    try:
        import resource

        peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux reports KiB; macOS reports bytes.
        divisor = 1024.0 if platform.system() != "Darwin" else 1024.0 * 1024.0
        return round(peak / divisor, 3)
    except (ImportError, OSError, ValueError):
        return None


def normalize_identity(value: str, default: str) -> str:
    identity = value.strip() or default
    if len(identity) > 64 or any(ord(char) < 32 for char in identity):
        raise ValueError("Participant identity is invalid")
    return identity


def node_status() -> dict:
    return create_quantum_engine(settings.quantum_engine, 11).metadata.model_dump()


def sign_document(**kwargs):
    started = time.perf_counter()
    noise_values = kwargs.pop("noise", {})
    passphrase = kwargs.get("encryption_passphrase")
    if passphrase and len(passphrase) < 8:
        raise ValueError("Encryption passphrase must contain at least 8 characters")
    result = create_qds_session(**kwargs, noise=NoiseConfig(**noise_values))
    elapsed = time.perf_counter() - started
    teleportations = int(result["signature"]["prepared_quantum_states"])
    result["performance"] = {
        "signature_generation_latency_ms": round(elapsed * 1000, 2),
        "production_teleportations": teleportations,
        "production_bell_pairs_consumed_sequentially": result["quantum_status"]["teleportation"][
            "bell_pairs_consumed"
        ],
        "teleportations_per_second": teleportations / elapsed if elapsed else None,
        "maximum_simultaneous_qubits": result["quantum"]["maximum_circuit_width"],
        "engine": result["quantum"]["engine"],
        "target": result["quantum"]["target"],
        "diagnostic_shots": (
            result["signature"]["quantum_diagnostic"]["total_diagnostic_shots"]
            + result["signature"]["effective_channel_diagnostic"]["total_diagnostic_shots"]
        ),
        "memory_measurement": (
            "PROCESS_PEAK_RSS" if _process_peak_rss_mb() is not None else "NOT_AVAILABLE_ON_HOST"
        ),
        "process_peak_rss_mb": _process_peak_rss_mb(),
        "gpu_memory_measurement": "NOT_MEASURED_BY_REQUEST_PATH",
    }
    network = result.get("network")
    if isinstance(network, dict):
        result["performance"].update(
            {
                "sequence_wall_clock_runtime_ms": network.get("wall_clock_runtime_ms"),
                "sequence_simulation_duration_ps": network.get(
                    "network_simulation_duration_ps"
                ),
                "sequence_sampled_distribution_attempts": network.get(
                    "sampled_distribution_attempts"
                ),
                "sequence_sampled_delivery_rate": network.get("sampled_delivery_rate"),
            }
        )
    return result


def verify_received_document(*, document: bytes, signature: dict, verifier_id: str):
    started = time.perf_counter()
    result = verify_document(
        document=document,
        signature=signature,
        consume=True,
        authenticated_verifier_id=verifier_id,
    ).model_dump()
    result["performance"] = {
        "verification_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "usable_measurements": result["usable_measurements"],
        "memory_measurement": (
            "PROCESS_PEAK_RSS" if _process_peak_rss_mb() is not None else "NOT_AVAILABLE_ON_HOST"
        ),
        "process_peak_rss_mb": _process_peak_rss_mb(),
    }
    return result


def public_material(session_id: str) -> dict:
    return get_session_summary(session_id)["signature"]
