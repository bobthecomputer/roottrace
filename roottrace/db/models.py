from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from roottrace.db.base import Base


class ArtifactKind(str, Enum):
    """Supported artifact kinds."""

    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"
    TEXT = "text"
    URL = "url"


class IngestStatus(str, Enum):
    """Lifecycle status for ingestion jobs."""

    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestJob(Base):
    """Persisted ingestion request with artifacts and derived data."""

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    artifact_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_kind: Mapped[ArtifactKind] = mapped_column(
        SqlEnum(ArtifactKind),
        nullable=False,
    )
    status: Mapped[IngestStatus] = mapped_column(
        SqlEnum(IngestStatus),
        default=IngestStatus.RECEIVED,
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON()),
        default=dict,
    )
    text_content: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON()), default=dict)

    entities: Mapped[list[ExtractedEntity]] = relationship(
        "ExtractedEntity",
        back_populates="ingest",
        cascade="all, delete-orphan",
    )
    logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="ingest",
        cascade="all, delete-orphan",
    )
    derived_artifacts: Mapped[list[DerivedArtifact]] = relationship(
        "DerivedArtifact",
        back_populates="ingest",
        cascade="all, delete-orphan",
    )


class ExtractedEntity(Base):
    """Entity extracted from the artifact."""

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingest_id: Mapped[int] = mapped_column(
        ForeignKey("ingest_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized: Mapped[str | None] = mapped_column(String(255))
    context: Mapped[str | None] = mapped_column(String(255))
    score: Mapped[float | None] = mapped_column(Float)

    ingest: Mapped[IngestJob] = relationship("IngestJob", back_populates="entities")


class DerivedArtifact(Base):
    """Artifacts produced during processing (e.g., keyframes, OCR text)."""

    __tablename__ = "derived_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingest_id: Mapped[int] = mapped_column(
        ForeignKey("ingest_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON()),
        default=dict,
    )

    ingest: Mapped[IngestJob] = relationship("IngestJob", back_populates="derived_artifacts")


class AuditLog(Base):
    """Structured audit log entry."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingest_id: Mapped[int] = mapped_column(
        ForeignKey("ingest_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON()),
        default=dict,
    )

    ingest: Mapped[IngestJob] = relationship("IngestJob", back_populates="logs")


__all__ = [
    "ArtifactKind",
    "AuditLog",
    "DerivedArtifact",
    "ExtractedEntity",
    "IngestJob",
    "IngestStatus",
]
