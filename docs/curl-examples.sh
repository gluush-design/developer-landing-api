#!/usr/bin/env bash
# Примеры запросов к API через curl.
# Использование:  BASE=http://localhost:8000 bash docs/curl-examples.sh
set -euo pipefail
BASE="${BASE:-http://localhost:8000}"

echo "== 1. Валидное обращение (заказ проекта) =="
curl -sS -X POST "$BASE/api/contact" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "email": "ivan@example.com",
    "phone": "+7 999 123-45-67",
    "comment": "Здравствуйте! Хочу заказать разработку backend API для маркетплейса, есть ТЗ и бюджет."
  }' | jq .

echo; echo "== 2. Ошибка валидации (ожидаем 422) =="
curl -sS -X POST "$BASE/api/contact" \
  -H "Content-Type: application/json" \
  -d '{"name":"Я","email":"not-an-email","phone":"123","comment":"мало"}' | jq .

echo; echo "== 3. Health =="
curl -sS "$BASE/api/health" | jq .

echo; echo "== 4. Metrics =="
curl -sS "$BASE/api/metrics" | jq .
