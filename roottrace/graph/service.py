from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from roottrace.config import Settings, settings
from roottrace.db.models import IngestJob
from roottrace.db.session import get_sessionmaker


class GraphService:
    """Generate a lightweight graph representation of ingested entities."""

    def __init__(self, config: Settings = settings) -> None:
        self.session_factory: sessionmaker[Session] = get_sessionmaker(config)

    def build_graph(self, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        with self.session_factory() as session:
            stmt = (
                select(IngestJob)
                .options(selectinload(IngestJob.entities))
                .order_by(IngestJob.created_at.desc())
                .limit(limit)
            )
            for job in session.scalars(stmt):
                job_node_id = f"job:{job.id}"
                nodes[job_node_id] = {
                    "id": job_node_id,
                    "type": "ingest",
                    "label": job.original_filename or job.source_uri,
                    "artifact_kind": job.artifact_kind.value,
                }
                for entity in job.entities:
                    entity_node_id = f"entity:{entity.kind}:{entity.normalized or entity.value}"
                    if entity_node_id not in nodes:
                        nodes[entity_node_id] = {
                            "id": entity_node_id,
                            "type": entity.kind,
                            "label": entity.value,
                        }
                    edges.append(
                        {
                            "source": job_node_id,
                            "target": entity_node_id,
                            "type": "mentions",
                        }
                    )
        return {"nodes": list(nodes.values()), "edges": edges}


__all__ = ["GraphService"]
