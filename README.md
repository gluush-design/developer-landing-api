# Developer Landing API

Бэкенд-сервис для лендинг-презентации разработчика: полноценный REST API формы
обратной связи с **AI-анализом обращений**, файловым хранилищем, rate limiting,
структурным логированием и автодокументацией OpenAPI. В комплекте — современный
одностраничный фронтенд-лендинг с рабочей формой.

> Полный цикл обращения: **запрос → валидация → бизнес-логика → AI → отправка писем → ответ.**

---

## Содержание
1. [Быстрый старт](#1-быстрый-старт)
2. [Стек технологий](#2-стек-технологий)
3. [Архитектура](#3-архитектура)
4. [Реализация API](#4-реализация-api)
5. [AI-интеграция](#5-ai-интеграция)
6. [Что сделано с помощью AI](#6-что-сделано-с-помощью-ai)
7. [Хранение данных](#7-хранение-данных)
8. [Тесты](#8-тесты)
9. [Деплой](#9-деплой)

---

## 1. Быстрый старт

### Требования
- Python 3.9+ (разрабатывалось и тестировалось на 3.11)
- `pip`

### Установка и запуск
```bash
# 1. Клонировать и перейти в каталог
git clone <repo-url> && cd developer-landing-api

# 2. Виртуальное окружение
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Зависимости
pip install -r requirements.txt

# 4. Переменные окружения
cp .env.example .env             # Windows: copy .env.example .env
#   отредактируйте .env при необходимости (ключ OpenAI, SMTP)

# 5. Запуск
uvicorn app.main:app --reload --port 8000
```

Откройте:
- **Лендинг** → http://localhost:8000/
- **Swagger UI** → http://localhost:8000/docs
- **ReDoc** → http://localhost:8000/redoc
- **OpenAPI JSON** → http://localhost:8000/openapi.json

> Сервис **полностью работоспособен без единого ключа**: без `OPENAI_API_KEY`
> включается rule-based AI-fallback, без SMTP — письма пишутся в лог (dry-run).

### Настройка переменных окружения
Все переменные описаны в [`.env.example`](.env.example). Ключевые:

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `AI_PROVIDER` | `openai` \| `anthropic` \| `none` | `openai` |
| `OPENAI_API_KEY` | ключ OpenAI (иначе fallback) | — |
| `OPENAI_MODEL` | модель | `gpt-4o-mini` |
| `SMTP_HOST` / `SMTP_*` | SMTP (иначе dry-run) | — |
| `OWNER_EMAIL` | куда падают заявки | — |
| `RATE_LIMIT_MAX_REQUESTS` | лимит запросов | `5` |
| `RATE_LIMIT_WINDOW_SECONDS` | окно лимита, сек | `600` |
| `CORS_ALLOW_ORIGINS` | разрешённые origin'ы | `*` |

### Docker
```bash
docker compose up --build      # → http://localhost:8000
```

---

## 2. Стек технологий

**Backend**
- **Python 3.11** + **FastAPI** — async, типобезопасность, автогенерация OpenAPI.
- **Pydantic v2** / **pydantic-settings** — валидация запросов и конфигурации.
- **Uvicorn** — ASGI-сервер.
- **aiosmtplib** — асинхронная отправка почты.
- **pytest** — 27 тестов.

**AI**
- **OpenAI** (`gpt-4o-mini`, JSON mode) — основной провайдер.
- **Anthropic Claude** — альтернативный провайдер (через тот же интерфейс).
- **Rule-based fallback** — собственный детерминированный анализатор без сети.

**Хранилище** — файловое (JSON / JSONL), без обязательной БД (по ТЗ).

### Почему так
- **FastAPI** — единственный мейнстрим-фреймворк, дающий **Swagger/OpenAPI из
  коробки** (прямое требование ТЗ), плюс валидация через Pydantic и нативный async,
  что идеально для I/O-bound операций (вызовы LLM, SMTP).
- **Слоистая архитектура** вместо «всё в роуте» — чтобы бизнес-логику можно было
  тестировать без HTTP и менять провайдеров AI/почты без правок контроллеров.
- **Файловое хранилище** — достаточно для задачи и не тянет инфраструктуру; код
  изолирован в репозиториях, так что переход на БД — это замена одного слоя.

---

## 3. Архитектура

Слоистая структура (**Controllers → Services → Repositories / Adapters**) с
Dependency Injection. Зависимости собираются один раз в *composition root*
([`app/dependencies.py`](app/dependencies.py)) и живут в `app.state`.

```
app/
├── main.py                 # Application factory: middleware, CORS, роуты, OpenAPI, статика
├── config.py               # Настройки (pydantic-settings, .env)
├── dependencies.py         # Composition root + DI-провайдеры
├── logging_config.py       # JSON-логи в файл + консоль, request_id
│
├── api/                    # СЛОЙ КОНТРОЛЛЕРОВ
│   ├── errors.py           #   глобальные обработчики ошибок (единый ErrorResponse)
│   └── routes/
│       ├── contact.py      #   POST /api/contact
│       ├── health.py       #   GET  /api/health
│       └── metrics.py      #   GET  /api/metrics
│
├── core/                   # ЯДРО
│   ├── exceptions.py       #   доменные исключения (HTTP-статус + код)
│   ├── rate_limiter.py     #   файловый sliding-window rate limiter
│   └── middleware.py       #   request_id, тайминг, логирование запросов
│
├── schemas/                # КОНТРАКТЫ (Pydantic)
│   ├── contact.py          #   ContactRequest/Response, AIAnalysis, enum'ы
│   └── common.py           #   ErrorResponse, Health, Metrics
│
├── services/               # БИЗНЕС-ЛОГИКА
│   ├── contact_service.py  #   оркестратор полного цикла
│   ├── ai/                 #   AIProvider (Strategy): openai | anthropic | fallback
│   │   ├── base.py         #     интерфейс + промпт + парсер JSON
│   │   ├── analyzer.py     #     фасад с graceful fallback
│   │   └── *_provider.py
│   └── email/              #   sender (SMTP/dry-run) + HTML-шаблоны писем
│
├── repositories/           # ДОСТУП К ДАННЫМ
│   ├── submission_repo.py  #   обращения (JSONL, append-only)
│   └── metrics_repo.py     #   агрегированные метрики (JSON)
│
└── static/index.html       # фронтенд-лендинг
```

### Паттерны проектирования
- **Layered architecture** — чёткое разделение ответственности по слоям.
- **Dependency Injection** — через FastAPI `Depends` + контейнер в `app.state`.
- **Strategy** — `AIProvider` с взаимозаменяемыми реализациями.
- **Repository** — изоляция доступа к данным от бизнес-логики.
- **Adapter** — `EmailSender` оборачивает SMTP/dry-run за единым интерфейсом.
- **Application Factory** — `create_app()` для конфигурируемой сборки (важно для тестов).
- **Graceful degradation** — fallback для AI и почты: сбой внешней зависимости
  не роняет основной сценарий.

---

## 4. Реализация API

| Метод | Путь | Назначение | Коды |
|---|---|---|---|
| `POST` | `/api/contact` | приём обращения (полный цикл) | `201` / `422` / `429` / `500` |
| `GET` | `/api/health` | статус сервиса и зависимостей | `200` |
| `GET` | `/api/metrics` | статистика обращений | `200` |

### `POST /api/contact`

**Запрос**
```json
{
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "comment": "Хочу заказать разработку backend API для маркетплейса."
}
```

**Ответ `201 Created`**
```json
{
  "success": true,
  "request_id": "5fde2cf2950c49c1",
  "message": "Обращение принято. Мы свяжемся с вами в ближайшее время.",
  "submission_id": "83a8c5b83255437e88ba6cc5199b3c24",
  "analysis": {
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "category": "project_inquiry",
    "priority": "high",
    "summary": "Обращение от Иван Петров: Хочу заказать разработку backend API…",
    "suggested_reply": "Здравствуйте, Иван! Спасибо за обращение. Я изучу детали проекта…",
    "provider": "openai"
  },
  "email_owner_sent": true,
  "email_user_sent": true,
  "processing_ms": 128
}
```

### Валидация и обработка ошибок
Валидация — на уровне Pydantic-схемы:
- `name` — 2–100 символов, тримминг и схлопывание пробелов;
- `email` — формат через `email-validator`;
- `phone` — регэксп + минимум 7 цифр;
- `comment` — 10–2000 символов, санитизация;
- `website` — **honeypot** (видим только ботам; заполнен → отклонение).

Все ошибки приходят в **едином формате** с `request_id` для трассировки:
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Некорректные входные данные.",
  "request_id": "96a4c06defa74450",
  "details": [
    { "field": "email", "message": "value is not a valid email address: ..." },
    { "field": "phone", "message": "String should have at least 7 characters" }
  ]
}
```

Статус-коды: `201` создано · `422` валидация/спам · `429` rate limit
(с заголовком `Retry-After`) · `500` внутренняя ошибка (стектрейс только в логах).

> Примеры запросов: [Postman-коллекция](docs/postman_collection.json) ·
> [curl-скрипт](docs/curl-examples.sh).

---

## 5. AI-интеграция

На каждое обращение AI выполняет **три функции сразу**:
1. **Анализ тональности** — `positive` / `neutral` / `negative` + score (−1…+1).
2. **Классификация типа обращения** — `collaboration` / `hiring` /
   `project_inquiry` / `support` / `spam` / `other`.
3. **Генерация черновика ответа** пользователю.

Результат используется в бизнес-логике: спам отсекается (`422`), приоритет
влияет на письмо владельцу, черновик уходит в копию пользователю.

### Как реализован fallback
[`AIAnalyzer`](app/services/ai/analyzer.py) пытается вызвать основной провайдер
(OpenAI/Anthropic) с таймаутом. При **любой** проблеме — нет ключа, сеть,
таймаут, невалидный JSON — мягко переключается на детерминированный
[`FallbackProvider`](app/services/ai/fallback_provider.py) (лексиконы тональности
+ ключевые слова категорий). **Обработка обращения никогда не падает из-за AI.**
В ответе всегда видно, кто отработал: поле `analysis.provider` (`openai` |
`anthropic` | `fallback`).

### Промпт
Единый системный промпт ([`app/services/ai/base.py`](app/services/ai/base.py))
заставляет модель вернуть строго JSON:
```
Ты — ассистент входящих обращений с лендинга backend-разработчика.
Проанализируй обращение и верни СТРОГО валидный JSON без пояснений и markdown.
Поля:
  "sentiment": один из ["positive","neutral","negative"];
  "sentiment_score": число от -1.0 до 1.0;
  "category": один из ["collaboration","hiring","project_inquiry","support","spam","other"];
  "priority": один из ["low","normal","high"];
  "summary": краткое резюме обращения на русском (1-2 предложения);
  "suggested_reply": вежливый черновик ответа пользователю на русском, 2-4 предложения.
Отвечай только JSON-объектом.
```
У OpenAI дополнительно включён `response_format={"type": "json_object"}` —
гарантия валидного JSON.

---

## 6. Что сделано с помощью AI

Проект разрабатывался в связке с AI-ассистентом (Claude Code).

**Что генерировалось ассистентом**
- Каркас слоистой структуры и бойлерплейт (схемы, репозитории, роуты).
- HTML/CSS/JS фронтенд-лендинга.
- Rule-based лексиконы тональности и ключевые слова категорий.
- Тестовые сценарии (pytest).

**Примеры использованных промптов**
- *«Спроектируй слоистую архитектуру FastAPI-сервиса формы обратной связи с
  AI-анализом, файловым хранилищем и graceful fallback»*.
- *«Напиши файловый sliding-window rate limiter с атомарной записью»*.
- *«Сгенерируй premium-лендинг разработчика с анимированным терминалом и формой,
  дёргающей API»*.

**Что правилось вручную**
- Коллизия `name`/`window.name` в JS формы (значения брались неверно) — найдено
  и исправлено при end-to-end проверке в браузере.
- Порядок ключевых слов в классификаторе (вакансия vs заказ проекта пересекались).
- Отсечение спама перенесено **после** AI-анализа, чтобы решение принималось по
  результату классификации, а не до него.
- Логика метрик: скользящее среднее времени обработки вместо простого счётчика.

---

## 7. Хранение данных

Всё хранилище — файловое, каталог [`data/`](data/) (создаётся автоматически,
содержимое в `.gitignore`).

| Что | Где | Формат |
|---|---|---|
| **Логи запросов** | `data/logs/app.log` | JSON-строки, ротация 5×5 МБ, `request_id` |
| **Обращения** | `data/submissions.jsonl` | JSON Lines (append-only) |
| **Статистика** | `data/metrics.json` | агрегированный JSON |
| **Rate limit** | `data/ratelimit.json` | таймстемпы по IP |

- **Логи** — `RotatingFileHandler`, каждая строка содержит `request_id`, метод,
  путь, статус, длительность и IP клиента → события одного запроса легко связать.
- **Rate limiting** — алгоритм скользящего окна по IP; запись атомарна (через
  временный файл + `replace`), устаревшие записи вычищаются на каждом обращении.
- **Статистика** (`GET /api/metrics`) — счётчики по тональности, категориям,
  приоритетам, доля AI vs fallback, отправленные письма, заблокированный спам,
  сработавший rate limit и среднее время обработки.

---

## 8. Тесты

```bash
pytest                 # 27 тестов: ~1.3 c
```
Покрытие: успешный полный цикл, валидация всех полей, honeypot, rate limit (429),
rule-based анализ (тональность/категории/спам), health, metrics, наличие
OpenAPI-схемы, CORS, единый формат ошибок. Тесты используют изолированное
файловое хранилище (`tmp_path`) и работают без сети (fallback + dry-run).

---

## 9. Деплой

**Локально** — см. [Быстрый старт](#1-быстрый-старт).

**Docker** — `docker compose up --build`.

**Render** — в репозитории есть [`render.yaml`](render.yaml): подключите репозиторий,
задайте секреты (`OPENAI_API_KEY`, SMTP) в дашборде — деплой по
`startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
healthcheck по `/api/health`. Аналогично разворачивается на Railway/любом хостинге.

---

### Чек-лист требований ТЗ
- [x] `POST /api/contact` с валидацией (имя, телефон, email, комментарий)
- [x] Email владельцу + копия пользователю
- [x] Обработка ошибок с HTTP-статусами + глобальный error handler
- [x] Rate limiting (файловый)
- [x] Логирование всех запросов в файл
- [x] AI-функция (тональность + классификация + генерация ответа) с graceful fallback
- [x] `GET /api/health`, `GET /api/metrics`
- [x] `.env`, CORS, Swagger/OpenAPI
- [x] Слоистая архитектура (Controllers → Services → Repositories)
- [x] README, Postman-коллекция, curl-примеры
- [x] Фронтенд-лендинг с рабочей формой
- [x] 27 тестов
