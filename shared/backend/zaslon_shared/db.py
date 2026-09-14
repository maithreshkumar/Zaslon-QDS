from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class QDSSession(Base):
    __tablename__ = "qds_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signer_id: Mapped[str] = mapped_column(String(64), index=True)
    verifier_id: Mapped[str] = mapped_column(String(64), index=True)
    protocol: Mapped[str] = mapped_column(String(128))
    protocol_version: Mapped[str] = mapped_column(String(64))
    document_name: Mapped[str] = mapped_column(String(255))
    document_hash: Mapped[str] = mapped_column(String(128), index=True)
    public_signature_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"))
    private_evidence_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"))
    prepared_state_count: Mapped[int] = mapped_column(Integer)
    max_circuit_width: Mapped[int] = mapped_column(Integer, default=3)
    verification_threshold: Mapped[float] = mapped_column(Float)
    threshold_source: Mapped[str] = mapped_column(String(64))
    quantum_engine: Mapped[str] = mapped_column(String(64))
    quantum_target: Mapped[str] = mapped_column(String(128))
    nonce: Mapped[str] = mapped_column(String(128), unique=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AttackExperiment(Base):
    __tablename__ = "attack_experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    qds_session_id: Mapped[str] = mapped_column(String(64), index=True)
    attack_type: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(64))
    strength: Mapped[float] = mapped_column(Float)
    seed: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class QuantumJob(Base):
    """Persistent, encrypted hand-off between the CPU API and quantum worker."""

    __tablename__ = "quantum_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    payload_ciphertext: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), nullable=True
    )
    result_json: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuantumWorkerStatus(Base):
    __tablename__ = "quantum_worker_status"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    process_status: Mapped[str] = mapped_column(String(24))
    cudaq_status: Mapped[str] = mapped_column(String(24))
    gpu_status: Mapped[str] = mapped_column(String(24))
    engine: Mapped[str] = mapped_column(String(64))
    requested_target: Mapped[str] = mapped_column(String(64))
    execution_target: Mapped[str | None] = mapped_column(String(128), nullable=True)
    engine_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gpu_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fallback_used: Mapped[int] = mapped_column(Integer, default=0)
    fallback_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    health_result_json: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Backward-compatible entry point for tests/manual debugging.

    Docker uses the dedicated migration service before starting the API or worker.
    """
    from .migrations import run_migrations

    run_migrations()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
