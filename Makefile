.PHONY: dev up down build test lint migrate logs clean deploy

# === LOCAL DEVELOPMENT ===

dev: ## Start all services in development mode
	docker compose up --build

up: ## Start all services in background
	docker compose up -d --build

down: ## Stop all services
	docker compose down

logs: ## View logs from all services
	docker compose logs -f

logs-api: ## View API logs
	docker compose logs -f api

logs-worker: ## View worker logs
	docker compose logs -f worker

build: ## Build all Docker images
	docker compose build

restart: ## Restart all services
	docker compose restart

# === DATABASE ===

migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="description")
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	docker compose exec api alembic downgrade -1

# === TESTING ===

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	docker compose exec api pytest tests/ -v --tb=short

test-unit: ## Run backend unit tests only
	docker compose exec api pytest tests/unit/ -v

test-integration: ## Run backend integration tests only
	docker compose exec api pytest tests/integration/ -v

test-frontend: ## Run frontend tests
	cd frontend && npm test

# === CODE QUALITY ===

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend code
	docker compose exec api ruff check app/ --fix
	docker compose exec api ruff format app/

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

# === GCP DEPLOYMENT ===

deploy: ## Deploy to GCP (usage: make deploy PROJECT_ID=xxx REGION=us-central1)
	./deploy/deploy.sh $(PROJECT_ID) $(REGION)

deploy-build: ## Build and push images to Artifact Registry
	gcloud builds submit --config=deploy/cloudbuild.yaml --substitutions=_REGION=$(REGION)

terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Plan Terraform changes
	cd terraform && terraform plan -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)"

terraform-apply: ## Apply Terraform changes
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)"

# === UTILITIES ===

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi all --remove-orphans

shell-api: ## Open shell in API container
	docker compose exec api bash

shell-db: ## Open psql shell
	docker compose exec db psql -U postgres -d photoai

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
