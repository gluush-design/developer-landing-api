.PHONY: install run dev test lint docker-build docker-up clean

install:        ## Установить зависимости
	pip install -r requirements.txt

run:            ## Запустить продакшн-сервер
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:            ## Запустить dev-сервер с автоперезагрузкой
	uvicorn app.main:app --reload --port 8000

test:           ## Прогнать тесты
	pytest

lint:           ## Проверить код ruff'ом
	ruff check app tests

docker-build:   ## Собрать образ
	docker build -t developer-landing-api .

docker-up:      ## Поднять через docker-compose
	docker compose up --build

clean:          ## Очистить кеши и временные файлы
	rm -rf .pytest_cache __pycache__ **/__pycache__ .ruff_cache
