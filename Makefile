.PHONY: help install dev test coverage lint format check docker-up docker-down docker-logs

help:
	@echo "ChargeCheck commands:"
	@echo "  make install      Install dependencies"
	@echo "  make dev          Start development server"
	@echo "  make test         Run tests"
	@echo "  make coverage     Run tests with coverage"
	@echo "  make lint         Check code quality"
	@echo "  make format       Format Python code"
	@echo "  make check        Run all quality checks"
	@echo "  make docker-up    Start Docker services"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make docker-logs  Show Docker logs"

install:
	uv sync

dev:
	uv run uvicorn chargecheck.api.main:create_app --factory --reload

test:
	uv run pytest -v

coverage:
	uv run pytest --cov=chargecheck --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test

docker-up:
	docker compose -f compose.yaml up --build -d

docker-down:
	docker compose -f compose.yaml down

docker-logs:
	docker compose -f compose.yaml logs -f
