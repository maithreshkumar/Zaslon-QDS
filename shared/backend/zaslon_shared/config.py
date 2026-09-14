from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from urllib.parse import quote_plus

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.auth", override=False)


def _setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None and value != "":
        return value
    secret_file = os.getenv(f"{name}_FILE")
    if secret_file:
        try:
            secret = Path(secret_file).read_text(encoding="utf-8").strip()
        except OSError:
            secret = ""
        if secret:
            return secret
    return default


def _get_wsl_windows_host() -> str | None:
    try:
        proc_version = Path("/proc/version")
        if proc_version.exists() and (
            "microsoft" in proc_version.read_text().lower()
            or "wsl" in proc_version.read_text().lower()
        ):
            proc_route = Path("/proc/net/route")
            if proc_route.exists():
                with open(proc_route, "r") as f:
                    for line in f:
                        fields = line.strip().split()
                        if len(fields) >= 3 and fields[1] == "00000000":
                            import socket, struct

                            return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
            resolv = Path("/etc/resolv.conf")
            if resolv.exists():
                for line in resolv.read_text().splitlines():
                    if line.strip().startswith("nameserver"):
                        parts = line.strip().split()
                        if len(parts) >= 2 and parts[1] != "127.0.0.1":
                            return parts[1]
    except Exception:
        pass
    return None


def _is_port_open(host: str, port: int | str) -> bool:
    try:
        import socket

        with socket.create_connection((host, int(port)), timeout=0.3):
            return True
    except Exception:
        return False


def _resolve_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        url = os.environ["DATABASE_URL"]
        if url.startswith("mysql") and ("@127.0.0.1:" in url or "@localhost:" in url):
            wsl_host = _get_wsl_windows_host()
            if wsl_host and not _is_port_open("127.0.0.1", 3306):
                url = url.replace("@127.0.0.1:", f"@{wsl_host}:").replace(
                    "@localhost:", f"@{wsl_host}:"
                )
        return url

    user = _setting("MYSQL_USER") or _setting("DB_USER")
    password = (
        _setting("MYSQL_PASSWORD")
        if _setting("MYSQL_PASSWORD") is not None
        else _setting("DB_PASSWORD")
    )
    host = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME", "zaslon_qds")

    if host in ("127.0.0.1", "localhost"):
        wsl_host = _get_wsl_windows_host()
        if wsl_host and not _is_port_open(host, port):
            host = wsl_host

    if user is not None:
        quoted_user = quote_plus(user)
        quoted_pass = quote_plus(password) if password is not None else ""
        auth = f"{quoted_user}:{quoted_pass}" if password is not None else quoted_user
        return f"mysql+pymysql://{auth}@{host}:{port}/{database}"

    wsl_host = _get_wsl_windows_host()
    default_host = (
        wsl_host if (wsl_host and not _is_port_open("127.0.0.1", 3306)) else "127.0.0.1"
    )
    return f"mysql+pymysql://zaslon:zaslon_dev@{default_host}:3306/zaslon_qds"


@dataclass(frozen=True)
class Settings:
    database_url: str = _resolve_database_url()
    quantum_engine: str = os.getenv("ZASLON_QUANTUM_ENGINE", "cudaq").lower()
    cudaq_target: str = os.getenv("ZASLON_CUDAQ_TARGET", "auto").lower()
    cudaq_target_option: str = os.getenv("ZASLON_CUDAQ_TARGET_OPTION", "fp32").lower()
    alice_api_key: str = _setting("ZASLON_ALICE_API_KEY", "") or ""
    bob_api_key: str = _setting("ZASLON_BOB_API_KEY", "") or ""
    attack_api_key: str = _setting("ZASLON_ATTACK_API_KEY", "") or ""
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "ZASLON_CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175",
        ).split(",")
        if item.strip()
    )
    verification_threshold: float = float(
        os.getenv("ZASLON_VERIFICATION_THRESHOLD", "0.05")
    )
    threshold_source: str = os.getenv(
        "ZASLON_THRESHOLD_SOURCE", "CONFIGURED_EXPERIMENTAL"
    )
    protocol_name: str = "Teleportation-Based-QDS-Research-Simulation"
    protocol_version: str = "0.3.0-basis-aware-teleportation"
    states_per_candidate: int = 4
    entanglement_diagnostic_shots: int = int(
        os.getenv("ZASLON_ENTANGLEMENT_DIAGNOSTIC_SHOTS", "2048")
    )
    entanglement_correlation_threshold: float = float(
        os.getenv("ZASLON_ENTANGLEMENT_CORRELATION_THRESHOLD", "0.90")
    )
    max_document_bytes: int = int(os.getenv("ZASLON_MAX_DOCUMENT_BYTES", str(25 * 1024 * 1024)))
    max_signature_bytes: int = int(os.getenv("ZASLON_MAX_SIGNATURE_BYTES", str(5 * 1024 * 1024)))
    max_parallel_quantum_jobs: int = int(
        os.getenv("ZASLON_MAX_PARALLEL_QUANTUM_JOBS", "1")
    )
    execution_mode: str = os.getenv("ZASLON_EXECUTION_MODE", "direct").strip().lower()
    job_payload_key: str = _setting("ZASLON_JOB_PAYLOAD_KEY", "") or ""
    artifact_attestation_key: str = _setting("ZASLON_ARTIFACT_ATTESTATION_KEY", "") or ""
    job_wait_timeout_seconds: float = float(
        os.getenv("ZASLON_JOB_WAIT_TIMEOUT_SECONDS", "300")
    )
    job_poll_interval_seconds: float = float(
        os.getenv("ZASLON_JOB_POLL_INTERVAL_SECONDS", "0.20")
    )
    worker_id: str = os.getenv("ZASLON_WORKER_ID", "quantum-worker-1")
    worker_heartbeat_seconds: float = float(
        os.getenv("ZASLON_WORKER_HEARTBEAT_SECONDS", "5")
    )
    worker_stale_seconds: float = float(
        os.getenv("ZASLON_WORKER_STALE_SECONDS", "120")
    )
    worker_max_attempts: int = int(os.getenv("ZASLON_WORKER_MAX_ATTEMPTS", "2"))
    allow_cudaq_cpu_fallback: bool = os.getenv(
        "ZASLON_ALLOW_CUDAQ_CPU_FALLBACK", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}
    sequence_enabled: bool = os.getenv("ZASLON_SEQUENCE_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }
    sequence_distance_m: float = float(os.getenv("ZASLON_SEQUENCE_DISTANCE_M", "1000"))
    sequence_attenuation_db_per_m: float = float(
        os.getenv("ZASLON_SEQUENCE_ATTENUATION_DB_PER_M", "0")
    )
    sequence_classical_delay_ps: int = int(
        os.getenv("ZASLON_SEQUENCE_CLASSICAL_DELAY_PS", "5000000")
    )
    sequence_sample_pairs: int = int(os.getenv("ZASLON_SEQUENCE_SAMPLE_PAIRS", "32"))


settings = Settings()
