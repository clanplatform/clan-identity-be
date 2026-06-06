.PHONY: help build up down restart logs clean test migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs for all services
	docker-compose logs -f

logs-auth: ## Show logs for auth service
	docker-compose logs -f auth-service

logs-user: ## Show logs for user service
	docker-compose logs -f user-service

logs-session: ## Show logs for session service
	docker-compose logs -f session-service

logs-rbac: ## Show logs for rbac service
	docker-compose logs -f rbac-service

logs-oauth: ## Show logs for oauth service
	docker-compose logs -f oauth-service

logs-db: ## Show logs for database
	docker-compose logs -f postgres

logs-redis: ## Show logs for redis
	docker-compose logs -f redis

ps: ## List running containers
	docker-compose ps

clean: ## Remove containers and volumes
	docker-compose down -v

clean-all: ## Remove containers, volumes, and images
	docker-compose down -v --rmi all

shell-auth: ## Open shell in auth service
	docker-compose exec auth-service /bin/bash

shell-user: ## Open shell in user service
	docker-compose exec user-service /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U clan_user -d clan_identity_db

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli -a redis_password

test: ## Run tests
	docker-compose exec auth-service pytest
	docker-compose exec user-service pytest

migrate: ## Run database migrations
	@echo "Running migrations for all services..."
	docker-compose exec auth-service alembic upgrade head
	docker-compose exec user-service alembic upgrade head
	docker-compose exec session-service alembic upgrade head
	docker-compose exec rbac-service alembic upgrade head
	docker-compose exec oauth-service alembic upgrade head

install: ## Install dependencies locally
	pip install -r services/requirements.txt

format: ## Format code with black
	black services/

lint: ## Lint code with flake8
	flake8 services/

dev-setup: build up ## Initial development setup
	@echo "Waiting for services to be ready..."
	sleep 10
	$(MAKE) migrate
	@echo "Development environment is ready!"
