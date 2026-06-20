# --- Базовый образ ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости отдельным слоем — кешируются, пока requirements не меняется.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения.
COPY app ./app

# Каталог под файловое хранилище (логи, заявки, метрики, rate limit).
RUN mkdir -p data/logs

EXPOSE 8000

# Healthcheck по эндпоинту /api/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else sys.exit(1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
