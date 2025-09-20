from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from roottrace import __version__
from roottrace.config import settings
from roottrace.db.base import Base
from roottrace.db.models import IngestJob
from roottrace.db.session import get_sessionmaker
from roottrace.extraction.entities import EntityMatch
from roottrace.graph.service import GraphService
from roottrace.ingest.service import IngestService
from roottrace.osint.suggestions import generate_suggestions

app = FastAPI(title="RootTrace", version=__version__)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


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


def _entity_matches_from_job(job: IngestJob) -> list[EntityMatch]:
    return [
        EntityMatch(
            kind=entity.kind,
            value=entity.value,
            normalized=entity.normalized,
            context=entity.context,
            score=entity.score,
        )
        for entity in job.entities
    ]


def _entities_to_models(matches: list[EntityMatch]) -> list[EntityModel]:
    return [
        EntityModel(
            kind=match.kind,
            value=match.value,
            normalized=match.normalized,
            context=match.context,
            score=match.score,
        )
        for match in matches
    ]


def _job_to_model(job: IngestJob) -> JobModel:
    text_excerpt = (job.text_content or "")[:500] or None
    return JobModel(
        id=job.id,
        artifact_kind=job.artifact_kind.value,
        content_type=job.content_type,
        sha256=job.sha256,
        size_bytes=job.size_bytes,
        metadata=job.artifact_metadata,
        summary=job.summary,
        text_excerpt=text_excerpt,
    )


def _build_ingest_payload(
    job: IngestJob,
) -> tuple[JobModel, list[EntityModel], list[SuggestionModel]]:
    entity_matches = _entity_matches_from_job(job)
    entities = _entities_to_models(entity_matches)
    suggestions = [
        SuggestionModel(**asdict(suggestion))
        for suggestion in generate_suggestions(entity_matches)
    ]
    return _job_to_model(job), entities, suggestions


def _prepare_proof_response(job_id: int, service: IngestService) -> FileResponse:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    proof_path = job.summary.get("proof_archive") if job.summary else None
    if proof_path is None:
        raise HTTPException(status_code=409, detail="Proof archive unavailable")
    archive = Path(proof_path)
    if not archive.exists():
        raise HTTPException(status_code=410, detail="Proof archive missing on disk")
    return FileResponse(archive, media_type="application/zip", filename=archive.name)


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

    job_model, entities, suggestions = _build_ingest_payload(stored_job)
    return IngestResponse(job=job_model, entities=entities, suggestions=suggestions)


@app.get("/jobs", response_model=list[JobModel])
def list_jobs(
    limit: int = 10,
    service: IngestService = Depends(get_ingest_service),
) -> list[JobModel]:
    jobs = service.list_recent_jobs(limit=limit)
    return [_job_to_model(job) for job in jobs]


@app.get("/jobs/{job_id}", response_model=JobModel)
def get_job(job_id: int, service: IngestService = Depends(get_ingest_service)) -> JobModel:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_model(job)


@app.get("/jobs/{job_id}/entities", response_model=list[EntityModel])
def job_entities(
    job_id: int,
    service: IngestService = Depends(get_ingest_service),
) -> list[EntityModel]:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _entities_to_models(_entity_matches_from_job(job))


@app.get("/jobs/{job_id}/suggestions", response_model=list[SuggestionModel])
def job_suggestions(
    job_id: int,
    service: IngestService = Depends(get_ingest_service),
) -> list[SuggestionModel]:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    _, _, suggestions = _build_ingest_payload(job)
    return suggestions


@app.get("/", response_class=HTMLResponse)
def ui_home(
    request: Request,
    service: IngestService = Depends(get_ingest_service),
) -> HTMLResponse:
    jobs = service.list_recent_jobs(limit=10)
    job_models = [_job_to_model(job) for job in jobs]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "jobs": job_models,
        },
    )


@app.post("/ui/ingest")
async def ui_ingest(
    request: Request,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    source_uri: str | None = Form(default=None),
    service: IngestService = Depends(get_ingest_service),
) -> Response:
    if file is None and url is None:
        jobs = service.list_recent_jobs(limit=10)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "jobs": [_job_to_model(job) for job in jobs],
                "error": "Sélectionnez un fichier ou fournissez une URL.",
            },
            status_code=400,
        )
    if file is not None and url is not None:
        raise HTTPException(status_code=400, detail="Provide either file or URL, not both")

    try:
        if file is not None:
            job = service.ingest_upload(file, source_uri=source_uri)
        else:
            job = service.ingest_url(url or "")
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive UI feedback
        jobs = service.list_recent_jobs(limit=10)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "jobs": [_job_to_model(job) for job in jobs],
                "error": f"Erreur d'ingestion: {exc}",
            },
            status_code=500,
        )
    return RedirectResponse(
        url=request.url_for("ui_job_detail", job_id=job.id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/ui/job/{job_id}", response_class=HTMLResponse, name="ui_job_detail")
def ui_job_detail(
    request: Request,
    job_id: int,
    service: IngestService = Depends(get_ingest_service),
) -> HTMLResponse:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job_model, entities, suggestions = _build_ingest_payload(job)
    return templates.TemplateResponse(
        "job_detail.html",
        {
            "request": request,
            "job": job_model,
            "entities": entities,
            "suggestions": suggestions,
        },
    )


@app.get("/graph")
def graph(service: GraphService = Depends(get_graph_service)) -> dict[str, Any]:
    return service.build_graph()


@app.post("/export/proof")
def export_proof(
    payload: ProofRequest,
    service: IngestService = Depends(get_ingest_service),
) -> FileResponse:
    return _prepare_proof_response(payload.job_id, service)


@app.get("/export/proof/{job_id}")
def export_proof_via_get(
    job_id: int,
    service: IngestService = Depends(get_ingest_service),
) -> FileResponse:
    return _prepare_proof_response(job_id, service)


__all__ = ["app"]
