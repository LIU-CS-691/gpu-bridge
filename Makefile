SHELL := /bin/bash

.PHONY: setup up down logs lint test itest fmt

setup:
	python -m venv .venv || true
	source .venv/bin/activate && pip install -U pip
	source .venv/bin/activate && pip install -r requirements-dev.txt
	source .venv/bin/activate && pip install -r controller/requirements.txt
	source .venv/bin/activate && pip install -e ./cli -e ./worker

up:
	docker-compose up -d --build

down:
	docker-compose down -v

logs:
	docker-compose logs -f --tail=200

fmt:
	. .venv/bin/activate && ruff format .

lint:
	. .venv/bin/activate && ruff check .

test:
	. .venv/bin/activate && PYTHONPATH=. pytest -q

itest:
	. .venv/bin/activate && PYTHONPATH=. pytest -q tests/integration
