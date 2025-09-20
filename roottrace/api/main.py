from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from roottrace import __version__
from roottrace.config import settings
from roottrace.db.base import Base
from roottrace.db.session import get_sessionmaker
from roottrace.extraction.entities import EntityMatch
from roottrace.graph.service import GraphService
from roottrace.ingest.service import IngestService
from roottrace.osint.suggestions import generate_suggestions

app = FastAPI(title="RootTrace", version=__version__)


def get_ingest_service() -> IngestService:
    return IngestService()


def get_graph_service() -> GraphService:
    return GraphService()


class EntityModel(BaseModel):
    kind: str
    value: str
    normalized: str | None = None
    context: str | None = None
    score: float | None = None


class SuggestionModel(BaseModel):
    tool: str
    command: str
    description: str
    category: str


class JobModel(BaseModel):
    id: int
    artifact_kind: str
    content_type: str
    sha256: str
    size_bytes: int
    metadata: dict[str, Any]
    summary: dict[str, Any]
    text_excerpt: str | None


class IngestResponse(BaseModel):
    job: JobModel
    entities: list[EntityModel]
    suggestions: list[SuggestionModel]


class ProofRequest(BaseModel):
    job_id: int


@app.on_event("startup")
def _startup() -> None:
    session_factory = get_sessionmaker()
    with session_factory() as session:
        engine = session.get_bind()
        if engine is not None:
            Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "retention_days": settings.retention_days,
        "timezone": settings.timezone,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    source_uri: str | None = Form(default=None),
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    if file is None and url is None:
        raise HTTPException(status_code=400, detail="Provide a file or a URL")
    if file is not None and url is not None:
        raise HTTPException(status_code=400, detail="Provide either file or URL, not both")

    if file is not None:
        job = service.ingest_upload(file, source_uri=source_uri)
    else:
        job = service.ingest_url(url or "")

    stored_job = service.get_job(job.id)
    if stored_job is None:
        raise HTTPException(status_code=404, detail="Ingest job not found after processing")

    entity_matches = [
        EntityMatch(
            kind=entity.kind,
            value=entity.value,
            normalized=entity.normalized,
            context=entity.context,
            score=entity.score,
        )
        for entity in stored_job.entities
    ]
    entities = [
        EntityModel(
            kind=match.kind,
            value=match.value,
            normalized=match.normalized,
            context=match.context,
            score=match.score,
        )
        for match in entity_matches
    ]
    suggestions = [
        SuggestionModel(**asdict(suggestion))
        for suggestion in generate_suggestions(entity_matches)
    ]
    text_excerpt = (stored_job.text_content or "")[:500] or None
    job_model = JobModel(
        id=stored_job.id,
        artifact_kind=stored_job.artifact_kind.value,
        content_type=stored_job.content_type,
        sha256=stored_job.sha256,
        size_bytes=stored_job.size_bytes,
        metadata=stored_job.artifact_metadata,
        summary=stored_job.summary,
        text_excerpt=text_excerpt,
    )
    return IngestResponse(job=job_model, entities=entities, suggestions=suggestions)


@app.get("/graph")
def graph(service: GraphService = Depends(get_graph_service)) -> dict[str, Any]:
    return service.build_graph()


@app.post("/export/proof")
def export_proof(
    payload: ProofRequest,
    service: IngestService = Depends(get_ingest_service),
) -> FileResponse:
    job = service.get_job(payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    proof_path = job.summary.get("proof_archive") if job.summary else None
    if proof_path is None:
        raise HTTPException(status_code=409, detail="Proof archive unavailable")
    archive = Path(proof_path)
    if not archive.exists():
        raise HTTPException(status_code=410, detail="Proof archive missing on disk")
    return FileResponse(archive, media_type="application/zip", filename=archive.name)


__all__ = ["app"]
