"""Тесты rate limiting (защита от спама)."""
from __future__ import annotations


def test_rate_limit_triggers_after_threshold(client, valid_payload):
    # Лимит в фикстуре — 5 запросов. 6-й должен отлететь 429.
    last_status = None
    for _ in range(5):
        last_status = client.post("/api/contact", json=valid_payload).status_code
        assert last_status == 201

    res = client.post("/api/contact", json=valid_payload)
    assert res.status_code == 429
    body = res.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "Retry-After" in res.headers


def test_rate_limited_counts_in_metrics(client, valid_payload):
    for _ in range(6):
        client.post("/api/contact", json=valid_payload)
    metrics = client.get("/api/metrics").json()
    assert metrics["rate_limited"] >= 1
