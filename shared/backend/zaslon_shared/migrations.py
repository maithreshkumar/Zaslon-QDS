from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import inspect, select, text

from .db import (
    Base,
    QuantumJob,
    QuantumWorkerStatus,
    SchemaMigration,
    engine,
    session_scope,
)


def _create_model_schema() -> None:
    Base.metadata.create_all(engine)


def _ensure_mysql_longtext() -> None:
    if engine.dialect.name != "mysql":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE qds_sessions "
                "MODIFY public_signature_json LONGTEXT, "
                "MODIFY private_evidence_json LONGTEXT"
            )
        )
        connection.execute(
            text("ALTER TABLE attack_experiments MODIFY result_json LONGTEXT")
        )


def _ensure_worker_schema() -> None:
    QuantumJob.__table__.create(engine, checkfirst=True)
    QuantumWorkerStatus.__table__.create(engine, checkfirst=True)


def _widen_worker_engine_version() -> None:
    if engine.dialect.name != "mysql":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE quantum_worker_status "
                "MODIFY engine_version VARCHAR(255) NULL"
            )
        )


MIGRATIONS: tuple[tuple[int, str, Callable[[], None]], ...] = (
    (1, "create_core_qds_schema", _create_model_schema),
    (2, "ensure_mysql_longtext_evidence", _ensure_mysql_longtext),
    (3, "add_persistent_quantum_job_queue", _ensure_worker_schema),
    (4, "widen_worker_engine_version", _widen_worker_engine_version),
)


def run_migrations() -> list[dict[str, object]]:
    """Apply each schema migration once and record it in the database."""

    SchemaMigration.__table__.create(engine, checkfirst=True)
    applied: list[dict[str, object]] = []
    for version, name, operation in MIGRATIONS:
        with session_scope() as db:
            existing = db.scalar(
                select(SchemaMigration).where(SchemaMigration.version == version)
            )
        if existing is not None:
            applied.append({"version": version, "name": name, "status": "ALREADY_APPLIED"})
            continue
        operation()
        with session_scope() as db:
            db.add(
                SchemaMigration(
                    version=version,
                    name=name,
                    applied_at=datetime.now(timezone.utc),
                )
            )
        applied.append({"version": version, "name": name, "status": "APPLIED"})
    return applied


def verify_schema() -> bool:
    required = {
        "schema_migrations",
        "participants",
        "qds_sessions",
        "attack_experiments",
        "quantum_jobs",
        "quantum_worker_status",
    }
    try:
        return required <= set(inspect(engine).get_table_names())
    except Exception:
        return False
