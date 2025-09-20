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
    assert graph.get("nodes")

    jobs_response = client.get("/jobs")
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert jobs and jobs[0]["id"] == job_id

    job_response = client.get(f"/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["sha256"]

    entities_response = client.get(f"/jobs/{job_id}/entities")
    assert entities_response.status_code == 200
    assert entities_response.json()

    suggestions_response = client.get(f"/jobs/{job_id}/suggestions")
    assert suggestions_response.status_code == 200

    proof_get = client.get(f"/export/proof/{job_id}")
    assert proof_get.status_code == 200
    assert proof_get.headers["content-type"] == "application/zip"

    ui_home = client.get("/")
    assert ui_home.status_code == 200
    assert "Ingestion rapide" in ui_home.text

    ui_job = client.get(f"/ui/job/{job_id}")
    assert ui_job.status_code == 200
    assert "Actions OSINT" in ui_job.text


def test_ui_ingest_requires_input(client: TestClient) -> None:
    response = client.post("/ui/ingest", data={}, allow_redirects=False)
    assert response.status_code == 400
    assert "Sélectionnez" in response.text


def test_ui_ingest_redirects_to_detail(client: TestClient) -> None:
    response = client.post(
        "/ui/ingest",
        files={"file": ("ui.txt", b"domain roottrace.ai", "text/plain")},
        data={"source_uri": "ui"},
        allow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    detail = client.get(location)
    assert detail.status_code == 200
    assert "RootTrace" in detail.text
