"""Тесты основного эндпоинта POST /api/contact."""
from __future__ import annotations


def test_contact_success(client, valid_payload):
    res = client.post("/api/contact", json=valid_payload)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["submission_id"]
    assert body["request_id"]
    assert body["analysis"]["provider"] == "fallback"  # без ключа — fallback
    assert body["analysis"]["category"] == "project_inquiry"
    assert body["email_owner_sent"] is True
    assert body["email_user_sent"] is True
    assert "X-Request-ID" in res.headers


def test_contact_persists_and_counts_in_metrics(client, valid_payload):
    client.post("/api/contact", json=valid_payload)
    client.post("/api/contact", json=valid_payload)
    metrics = client.get("/api/metrics").json()
    assert metrics["total_submissions"] == 2
    assert metrics["by_category"].get("project_inquiry") == 2
    assert metrics["fallback_used"] == 2
    assert metrics["emails_sent"] == 4
    assert metrics["last_submission_at"] is not None


def test_contact_response_includes_suggested_reply(client, valid_payload):
    res = client.post("/api/contact", json=valid_payload)
    reply = res.json()["analysis"]["suggested_reply"]
    assert "Иван" in reply  # обращение по имени
