from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from roottrace.config import Settings, settings
from roottrace.db.models import (
    ArtifactKind,
    AuditLog,
    DerivedArtifact,
    ExtractedEntity,
    IngestJob,
    IngestStatus,
)
from roottrace.db.session import get_sessionmaker
from roottrace.extraction.entities import EntityMatch, extract_entities
from roottrace.extraction.image import extract_image
from roottrace.extraction.pdf import extract_pdf
from roottrace.extraction.text import extract_text
from roottrace.extraction.types import DerivedFile, ExtractionResult
from roottrace.extraction.video import extract_video
from roottrace.ingest.detector import ArtifactDetector
from roottrace.proof.package import ProofBuilder
from roottrace.utils.audit import AuditTrail
from roottrace.utils.files import download_url, resolve_artifact_path, save_stream_to_path
from roottrace.utils.hash import sha256_file


class IngestService:
    """Coordinate ingestion, extraction, entity detection and persistence."""

    def __init__(
        self,
        config: Settings = settings,
        detector: ArtifactDetector | None = None,
    ) -> None:
        self.config = config
        self.detector = detector or ArtifactDetector()
        self.session_factory = get_sessionmaker(config)

    def ingest_upload(self, upload: UploadFile, source_uri: str | None = None) -> IngestJob:
        """Ingest a FastAPI UploadFile."""

        upload.file.seek(0)
        destination = resolve_artifact_path(upload.filename, self.config.data_dir)
        save_stream_to_path(upload.file, destination)
        return self._process_artifact(
            path=destination,
            source_uri=source_uri or (upload.filename or "upload"),
            original_filename=upload.filename,
            declared_mime=upload.content_type,
        )

    def ingest_path(self, path: Path, source_uri: str | None = None) -> IngestJob:
        """Copy and ingest a file from disk."""

        destination = resolve_artifact_path(path.name, self.config.data_dir)
        shutil.copy2(path, destination)
        return self._process_artifact(
            path=destination,
            source_uri=source_uri or str(path),
            original_filename=path.name,
            declared_mime=None,
        )

    def ingest_url(self, url: str) -> IngestJob:
        """Download and ingest an artifact from a URL."""

        destination = resolve_artifact_path(
            Path(url).name or "download.bin",
            self.config.data_dir,
        )
        path, mime = download_url(url, destination, config=self.config)
        return self._process_artifact(
            path=path,
            source_uri=url,
            original_filename=path.name,
            declared_mime=mime,
        )

    def get_job(self, job_id: int) -> IngestJob | None:
        """Retrieve a job with eager loaded relations."""

        stmt = (
            select(IngestJob)
            .options(
                selectinload(IngestJob.entities),
                selectinload(IngestJob.derived_artifacts),
                selectinload(IngestJob.logs),
            )
            .where(IngestJob.id == job_id)
        )
        with self.session_factory() as session:
            return session.scalars(stmt).first()

    def _process_artifact(
        self,
        path: Path,
        source_uri: str,
        original_filename: str | None,
        declared_mime: str | None,
    ) -> IngestJob:
        audit = AuditTrail(self.config.log_dir)
        audit.record("info", "ingest.received", source=source_uri, path=str(path))

        sha256 = sha256_file(path)
        size_bytes = path.stat().st_size
        kind, mime = self.detector.detect(path, override_mime=declared_mime)
        audit.record("info", "ingest.detected", kind=kind.value, mime=mime, size=size_bytes)

        with self.session_factory() as session:
            job = self._create_job(
                session=session,
                source_uri=source_uri,
                original_filename=original_filename,
                artifact_path=path,
                kind=kind,
                sha256=sha256,
                mime=mime,
                size=size_bytes,
                audit=audit,
            )
            job_id = job.id
            try:
                result = self._run_extraction(kind, path, audit)
                entities = self._store_entities(session, job, result.text or "")
                self._store_derived(session, job, result.derived_files)
                self._persist_audit_logs(session, job, audit)
                job.artifact_metadata = result.metadata
                job.text_content = result.text
                job.summary = self._summarize(job, entities)
                job.status = IngestStatus.COMPLETED
                job.completed_at = datetime.now(tz=UTC)
                session.add(job)
                session.commit()
                session.refresh(job)
                proof_builder = ProofBuilder(config=self.config)
                archive_path = proof_builder.index_job(job=job, audit=audit, session=session)
                job.summary["proof_archive"] = str(archive_path)
                session.add(job)
                session.commit()
                session.refresh(job)
                session.expunge(job)
            except Exception as error:
                session.rollback()
                job.status = IngestStatus.FAILED
                session.add(job)
                session.commit()
                audit.record("error", "ingest.failed", error=str(error))
                raise
        audit.record("info", "ingest.completed", job_id=job_id)
        return job

    def _create_job(
        self,
        session: Session,
        source_uri: str,
        original_filename: str | None,
        artifact_path: Path,
        kind: ArtifactKind,
        sha256: str,
        mime: str,
        size: int,
        audit: AuditTrail,
    ) -> IngestJob:
        job = IngestJob(
            source_uri=source_uri,
            original_filename=original_filename,
            artifact_path=str(artifact_path),
            artifact_kind=kind,
            status=IngestStatus.PROCESSING,
            sha256=sha256,
            size_bytes=size,
            content_type=mime,
            created_at=datetime.now(tz=UTC),
        )
        session.add(job)
        session.flush()
        audit.record("info", "ingest.job_created", job_id=job.id)
        return job

    def _run_extraction(
        self,
        kind: ArtifactKind,
        path: Path,
        audit: AuditTrail,
    ) -> ExtractionResult:
        if kind is ArtifactKind.IMAGE:
            audit.record("info", "extract.image", path=str(path))
            return extract_image(path)
        if kind is ArtifactKind.PDF:
            audit.record("info", "extract.pdf", path=str(path))
            return extract_pdf(path)
        if kind is ArtifactKind.VIDEO:
            audit.record("info", "extract.video", path=str(path))
            keyframe_dir = Path(path.parent) / "keyframes"
            return extract_video(path, keyframe_dir)
        audit.record("info", "extract.text", path=str(path))
        return extract_text(path)

    def _store_entities(self, session: Session, job: IngestJob, text: str) -> list[EntityMatch]:
        if not text:
            return []
        matches = extract_entities(text)
        for match in matches:
            entity = ExtractedEntity(
                ingest_id=job.id,
                kind=match.kind,
                value=match.value,
                normalized=match.normalized,
                context=match.context,
                score=match.score,
            )
            session.add(entity)
        session.flush()
        return matches

    def _store_derived(
        self,
        session: Session,
        job: IngestJob,
        derived_files: list[DerivedFile],
    ) -> None:
        for derived in derived_files:
            sha256 = sha256_file(derived.path)
            artifact = DerivedArtifact(
                ingest_id=job.id,
                label=derived.label,
                path=str(derived.path),
                sha256=sha256,
                artifact_metadata={
                    key: str(value)
                    for key, value in derived.metadata.items()
                },
            )
            session.add(artifact)
        session.flush()

    def _persist_audit_logs(self, session: Session, job: IngestJob, audit: AuditTrail) -> None:
        for event in audit.events:
            log = AuditLog(
                ingest_id=job.id,
                created_at=event.timestamp,
                level=event.level,
                event=event.event,
                details=event.to_dict()["details"],
            )
            session.add(log)
        session.flush()

    def _summarize(self, job: IngestJob, entities: list[EntityMatch]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "artifact_kind": job.artifact_kind.value,
            "entities": len(entities),
        }
        if entities:
            summary["entity_kinds"] = sorted({entity.kind for entity in entities})
        return summary


__all__ = ["IngestService"]
