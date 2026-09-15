.PHONY: help up up-build down down-v restart migrate migrate-down migration seed logs logs-app logs-db ps shell db-shell redis-shell test network wait-db

DOCKER_COMPOSE ?= docker compose

# Default target
.DEFAULT_GOAL := help

## ----------------------------------------------------------------------
## Household Backend Management
## ----------------------------------------------------------------------

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

network: ## Create external docker network if it doesn't exist
	@docker network inspect shared_network >/dev/null 2>&1 || (echo "Creating docker network: shared_network" && docker network create shared_network)

wait-db: ## Wait until PostgreSQL database is ready to accept connections
	@echo "Waiting for PostgreSQL to be ready..."
	@until $(DOCKER_COMPOSE) exec -T postgres_db pg_isready -U postgres -d postgres >/dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "PostgreSQL is ready!"

up: network ## Start all containers, wait for DB, and apply migrations
	@echo "Starting containers..."
	@$(DOCKER_COMPOSE) up -d
	@$(MAKE) wait-db
	@$(MAKE) migrate
	@echo ""
	@echo "✓ All services are running!"
	@echo "✓ API Docs available at: http://localhost:8000/docs"

up-build: network ## Rebuild and start all containers, wait for DB, and apply migrations
	@echo "Building and starting containers..."
	@$(DOCKER_COMPOSE) up -d --build
	@$(MAKE) wait-db
	@$(MAKE) migrate
	@echo ""
	@echo "✓ All services are rebuilt and running!"
	@echo "✓ API Docs available at: http://localhost:8000/docs"

down: ## Stop all running containers
	@echo "Stopping containers..."
	@$(DOCKER_COMPOSE) down

down-v: ## Stop all containers and remove persistent volumes (WARNING: wipes database)
	@echo "Stopping containers and deleting volumes..."
	@$(DOCKER_COMPOSE) down -v

restart: ## Restart containers and apply migrations
	@$(MAKE) down
	@$(MAKE) up

migrate: wait-db ## Apply pending database migrations (alembic upgrade head)
	@echo "Applying database migrations..."
	@$(DOCKER_COMPOSE) exec -T fastapi alembic upgrade head
	@echo "✓ Migrations applied successfully!"

migrate-down: wait-db ## Rollback the last applied migration (alembic downgrade -1)
	@echo "Rolling back last migration..."
	@$(DOCKER_COMPOSE) exec -T fastapi alembic downgrade -1
	@echo "✓ Rollback completed!"

migration: ## Create a new Alembic migration (usage: make migration msg="migration name")
	@if [ -z "$(msg)" ]; then \
		echo "Error: please specify migration message. Example: make migration msg=\"add users index\""; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE) exec -T fastapi alembic revision --autogenerate -m "$(msg)"

seed: wait-db ## Seed initial default chores and translations into database
	@echo "Seeding default chores..."
	@$(DOCKER_COMPOSE) exec -T fastapi python scripts/seed_default_chores.py
	@echo "✓ Seeding completed!"

logs: ## View and follow logs of all services
	@$(DOCKER_COMPOSE) logs -f

logs-app: ## View and follow FastAPI application logs
	@$(DOCKER_COMPOSE) logs -f fastapi

logs-worker: ## View and follow ARQ background worker logs
	@$(DOCKER_COMPOSE) logs -f worker

logs-db: ## View and follow PostgreSQL database logs
	@$(DOCKER_COMPOSE) logs -f postgres_db

ps: ## List status of all project containers
	@$(DOCKER_COMPOSE) ps

shell: ## Open interactive bash shell in the FastAPI container
	@$(DOCKER_COMPOSE) exec fastapi bash

db-shell: ## Open PostgreSQL interactive CLI (psql)
	@$(DOCKER_COMPOSE) exec postgres_db psql -U postgres -d postgres

redis-shell: ## Open Redis interactive CLI (redis-cli)
	@$(DOCKER_COMPOSE) exec redis redis-cli

test: ## Run tests with pytest
	@./venv/bin/pytest

pwa-build: ## Build PWA from frontend repo and copy to static/
	@if [ -d "../HOUSEHOLD-APP/frontend" ]; then \
		echo "Building PWA in ../HOUSEHOLD-APP/frontend..."; \
		(cd ../HOUSEHOLD-APP/frontend && npm run build:pwa) && \
		rm -rf static/* && \
		touch static/.gitkeep && \
		cp -r ../HOUSEHOLD-APP/frontend/dist/* static/ && \
		echo "✓ PWA built and copied to static/!"; \
	else \
		echo "Directory ../HOUSEHOLD-APP/frontend not found."; \
		exit 1; \
	fi

