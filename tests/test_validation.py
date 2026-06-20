"""Тесты валидации и санитизации входных данных."""
from __future__ import annotations

import pytest


def test_missing_fields_returns_422(client):
    res = client.post("/api/contact", json={"name": "Ян"})
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"] == "validation_error"
    assert body["details"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "Я"),                       # слишком коротко
        ("email", "not-an-email"),           # битый email
        ("phone", "123"),                    # мало цифр
        ("phone", "abcdefgh"),               # не телефон
        ("comment", "коротко"),              # < 10 символов
    ],
)
def test_invalid_field_rejected(client, valid_payload, field, value):
    payload = {**valid_payload, field: value}
    res = client.post("/api/contact", json=payload)
    assert res.status_code == 422
    fields = {d["field"] for d in res.json()["details"]}
    assert field in fields


def test_honeypot_blocks_bot(client, valid_payload):
    payload = {**valid_payload, "website": "http://spam.example"}
    res = client.post("/api/contact", json=payload)
    # honeypot должен иметь max_length=0 -> ошибка валидации
    assert res.status_code == 422


def test_name_and_comment_are_trimmed(client, valid_payload):
    payload = {**valid_payload, "name": "   Иван    Петров   "}
    res = client.post("/api/contact", json=payload)
    assert res.status_code == 201
    # имя нормализовано (схлопнуты пробелы) -> в ответе видно по reply
    assert "Иван" in res.json()["analysis"]["suggested_reply"]
