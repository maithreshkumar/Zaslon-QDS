from __future__ import annotations

import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet


SECRET_DIR = Path(os.getenv("ZASLON_SECRET_DIR", "/run/secrets/zaslon"))


def _is_usable(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    return len(value.strip()) >= 24 and not any(
        marker in lowered
        for marker in ("replace-with", "change-me", "development-only", "your_")
    )


def _create_once(filename: str, env_name: str, generator) -> str:
    destination = SECRET_DIR / filename
    if destination.exists() and destination.stat().st_size > 0:
        return "PRESERVED"

    supplied = os.getenv(env_name)
    value = supplied.strip() if _is_usable(supplied) else generator()
    temporary = SECRET_DIR / f".{filename}.{os.getpid()}.tmp"
    temporary.write_text(value + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, destination)
    # API, worker, frontend, and MySQL run as different non-root users. The
    # volume is mounted only into those containers, so read-only file mode is
    # preferable to duplicating secrets into image layers or browser bundles.
    destination.chmod(0o444)
    return "CREATED"


def main() -> None:
    SECRET_DIR.mkdir(parents=True, exist_ok=True)
    status = {
        "db_app_password": _create_once(
            "db_app_password", "ZASLON_DB_PASSWORD", lambda: secrets.token_urlsafe(48)
        ),
        "db_root_password": _create_once(
            "db_root_password",
            "ZASLON_DB_ROOT_PASSWORD",
            lambda: secrets.token_urlsafe(48),
        ),
        "alice_api_key": _create_once(
            "alice_api_key", "ZASLON_ALICE_API_KEY", lambda: secrets.token_urlsafe(48)
        ),
        "bob_api_key": _create_once(
            "bob_api_key", "ZASLON_BOB_API_KEY", lambda: secrets.token_urlsafe(48)
        ),
        "attack_api_key": _create_once(
            "attack_api_key", "ZASLON_ATTACK_API_KEY", lambda: secrets.token_urlsafe(48)
        ),
        "job_payload_key": _create_once(
            "job_payload_key",
            "ZASLON_JOB_PAYLOAD_KEY",
            lambda: Fernet.generate_key().decode("ascii"),
        ),
        "artifact_attestation_key": _create_once(
            "artifact_attestation_key",
            "ZASLON_ARTIFACT_ATTESTATION_KEY",
            lambda: secrets.token_urlsafe(64),
        ),
    }
    print(
        "ZASLON local secret volume initialized: "
        + ", ".join(f"{name}={state}" for name, state in status.items())
    )


if __name__ == "__main__":
    main()
