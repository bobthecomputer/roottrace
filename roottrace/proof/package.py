from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from roottrace.config import Settings, settings
from roottrace.db.models import IngestJob
from roottrace.utils.audit import AuditTrail


class ProofBuilder:
    """Build structured proof packages for completed ingestion jobs."""

    def __init__(self, config: Settings = settings) -> None:
        self.config = config
        self.config.proof_dir.mkdir(parents=True, exist_ok=True)

    def index_job(self, job: IngestJob, audit: AuditTrail, session: Session) -> Path:
        """Create or refresh the proof bundle for the provided job."""

        full_job = session.get(
            IngestJob,
            job.id,
            options=[
                selectinload(IngestJob.entities),
                selectinload(IngestJob.derived_artifacts),
                selectinload(IngestJob.logs),
            ],
        )
        if full_job is None:
            msg = f"Ingest job {job.id} not found"
            raise ValueError(msg)

        job_dir = self.config.proof_dir / f"job-{job.id}"
        job_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(job_dir / "ingest.json", self._serialize_job(full_job))
        self._write_json(job_dir / "entities.json", self._serialize_entities(full_job))
        self._write_json(job_dir / "hashes.json", self._serialize_hashes(full_job))
        self._write_json(job_dir / "logs.json", self._serialize_logs(full_job))

        if audit.path.exists():
            shutil.copy2(audit.path, job_dir / "audit.jsonl")

        self._copy_artifacts(job_dir, full_job)

        archive_path = self._zip_directory(job_dir)
        return archive_path

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _serialize_job(self, job: IngestJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "source_uri": job.source_uri,
            "artifact_kind": job.artifact_kind.value,
            "content_type": job.content_type,
            "sha256": job.sha256,
            "size_bytes": job.size_bytes,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "metadata": job.artifact_metadata,
            "summary": job.summary,
        }

    def _serialize_entities(self, job: IngestJob) -> list[dict[str, Any]]:
        return [
            {
                "kind": entity.kind,
                "value": entity.value,
                "normalized": entity.normalized,
                "context": entity.context,
                "score": entity.score,
            }
            for entity in job.entities
        ]

    def _serialize_hashes(self, job: IngestJob) -> dict[str, Any]:
        hashes: dict[str, Any] = {
            "artifact": {
                "path": job.artifact_path,
                "sha256": job.sha256,
            }
        }
        if job.derived_artifacts:
            hashes["derived"] = [
                {
                    "label": derived.label,
                    "path": derived.path,
                    "sha256": derived.sha256,
                }
                for derived in job.derived_artifacts
            ]
        return hashes

    def _serialize_logs(self, job: IngestJob) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": log.created_at.isoformat(),
                "level": log.level,
                "event": log.event,
                "details": log.details,
            }
            for log in job.logs
        ]

    def _copy_artifacts(self, job_dir: Path, job: IngestJob) -> None:
        original = Path(job.artifact_path)
        if original.exists():
            artifacts_dir = job_dir / "artifact"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, artifacts_dir / original.name)
        if job.derived_artifacts:
            derived_dir = job_dir / "derived"
            derived_dir.mkdir(parents=True, exist_ok=True)
            for derived in job.derived_artifacts:
                derived_path = Path(derived.path)
                if derived_path.exists():
                    shutil.copy2(derived_path, derived_dir / derived_path.name)

    def _zip_directory(self, directory: Path) -> Path:
        archive_path = directory.with_suffix(".zip")
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in directory.rglob("*"):
                archive.write(path, arcname=path.relative_to(directory))
        return archive_path


__all__ = ["ProofBuilder"]
