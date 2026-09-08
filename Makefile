.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help install lint fmt typecheck test test-cov up down logs build migrate revision shell-api shell-db clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install project + dev deps into the active environment
	pip install -e ".[dev]"

lint: ## Ruff lint
	ruff check app tests scripts

fmt: ## Ruff format
	ruff format app tests scripts

fmt-check: ## Ruff format --check
	ruff format --check app tests scripts

typecheck: ## mypy
	mypy app

ci: lint fmt-check test ## Run the CI checks locally

test: ## Run the test suite
	pytest -q

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=term-missing

build: ## Build all images
	$(COMPOSE) build

up: ## Start the full stack
	$(COMPOSE) up --build

up-obs: ## Start the stack with Prometheus + Grafana
	$(COMPOSE) --profile observability up --build

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Tail all logs
	$(COMPOSE) logs -f

migrate: ## Apply migrations inside the api container
	$(COMPOSE) run --rm api alembic upgrade head

revision: ## Autogenerate a migration: make revision m="message"
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

shell-api: ## Shell into the api container
	$(COMPOSE) run --rm api bash

shell-db: ## psql into postgres
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-newsfeed} -d $${POSTGRES_DB:-newsfeed}

clean: ## Remove containers, volumes and caches
	$(COMPOSE) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
