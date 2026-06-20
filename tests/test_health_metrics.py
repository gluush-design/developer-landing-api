"""Тесты системных эндпоинтов и инфраструктуры."""
from __future__ import annotations


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["ai"] == "fallback"
    assert body["dependencies"]["smtp"] == "dry-run"
    assert body["dependencies"]["storage"] == "ok"
    assert body["uptime_seconds"] >= 0


def test_metrics_empty_initially(client):
    body = client.get("/api/metrics").json()
    assert body["total_submissions"] == 0
    assert body["by_category"] == {}


def test_openapi_schema_available(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    assert "/api/contact" in paths
    assert "/api/health" in paths
    assert "/api/metrics" in paths


def test_docs_available(client):
    assert client.get("/docs").status_code == 200


def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "backend" in res.text.lower()


def test_unknown_route_404(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.json()["error"] == "http_error"


def test_cors_headers_present(client, valid_payload):
    res = client.post(
        "/api/contact",
        json=valid_payload,
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.headers.get("access-control-allow-origin") == "*"
