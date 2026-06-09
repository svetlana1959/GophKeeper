SHELL := /bin/bash
.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

## --- Local (uv) ---

install: ## Install dependencies into the uv-managed venv
	uv sync

run: ## Run the API locally with auto-reload
	uv run uvicorn gophkeeper.main:app --reload

test: ## Run all tests
	uv run pytest

test-unit: ## Run unit tests only (no database needed)
	uv run pytest tests/unit

test-integration: ## Run integration tests (needs TEST_DATABASE_URL, e.g. via `make up`)
	uv run pytest tests/integration

lint: ## Check formatting and lint rules
	uv run ruff format --check .
	uv run ruff check .

format: ## Auto-format and apply lint fixes
	uv run ruff format .
	uv run ruff check --fix .

## --- Docker ---

up: ## Build and start postgres + backend
	docker compose up -d --build

down: ## Stop and remove containers
	docker compose down

logs: ## Tail backend logs
	docker compose logs -f backend

## --- Database (dbmate) ---

migrate: ## Apply pending migrations
	docker compose run --rm migrations

rollback: ## Roll back the most recent migration
	docker compose run --rm migrations down

dbshell: ## Open a psql shell
	docker compose exec postgres psql -U postgres -d gophkeeper
