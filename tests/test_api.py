from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"


def test_ingest_endpoint_returns_entities_and_proof(client: TestClient) -> None:
    response = client.post(
        "/ingest",
        files={"file": ("sample.txt", b"mail agent@example.org", "text/plain")},
        data={"source_uri": "local"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["artifact_kind"] == "text"
    assert payload["entities"]
    job_id = payload["job"]["id"]

    proof_response = client.post("/export/proof", json={"job_id": job_id})
    assert proof_response.status_code == 200
    assert proof_response.headers["content-type"] == "application/zip"

    graph = client.get("/graph").json()
    assert "nodes" in graph and graph["nodes"]
