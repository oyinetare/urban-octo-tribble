.PHONY: install dev-install format lint type-check test test-cov clean run migrate pre-commit help check-docker-up run-fresh gaf clean-install

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

gaf: # git add . and run format code with ruff
	git add .
	uv run ruff format .
	uv run ruff check --fix .
	uv run pre-commit run --all-files
# 	git add .

install:  ## Install production dependencies
	uv sync

dev-install:  ## Install all dependencies including dev tools
	uv sync --all-extras
	uv run pre-commit install

clean-install: ## Force a Reinstallation - re-download and re-install all packages
	uv sync --reinstall

format:  ## Format code with ruff
	uv run ruff format .
	uv run ruff check --fix .

lint:  ## Lint code with ruff
	uv run ruff check .

type-check:  ## Type check with ty
	uv run ty check app/

test:  ## Run tests
	uv run pytest -v

test-cov:  ## Run tests with coverage report
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing

test-file: # Run specific test file
	pytest tests/$(FILE) -v


test-parallel: # Run tests in parallel
	pytest -n auto

test-failed: # Run only failed tests
	pytest --lf

load-test: # Load testing
	locust -f tests/locustfile.py --host=http://localhost:8000

clean:  ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .coverage*
# 	find . -type d -name ".mypy_cache" -exec rm -rf {} +

check-docker-up:
	@docker info >/dev/null 2>&1 || (echo "Error: Docker daemon is not running." && exit 1)

run-fresh: check-docker-up  ## Run the development server with docker
# 	uv run uvicorn app.main:app --reload
	docker compose down -v
	docker compose up -d
# 	uv run fastapi dev

run: check-docker-up  ## Run the development server
# 	uv run uvicorn app.main:app --reload
	uv run fastapi dev

migrate:  ## Run database migrations
	uv run alembic upgrade head

.PHONY: migration
migration:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-create:  ## Create a new migration (use: make migrate-create msg="description")
	uv run alembic revision --autogenerate -m "$(msg)"

migrate-down:  ## Rollback one migration
	uv run alembic downgrade -1

# migrate:
# 	alembic upgrade head

.PHONY: rollback
rollback:
	uv run alembic downgrade -1

.PHONY: db-reset
db-reset:
	uv run alembic downgrade base
	uv run alembic upgrade head

docker-hot-reload: check-docker-up ## Start Docker services
	docker compose up --build -d

docker-up: check-docker-up ## Start Docker services
	docker compose up -d

docker-down:  ## Stop Docker services
	docker compose down

docker-logs:  ## View Docker logs
	docker compose logs -f

pre-commit:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks
	uv run pre-commit autoupdate

ci:  ## Run all CI checks (format, lint, type-check, test)
	@echo "Running formatter..."
	@$(MAKE) format
	@echo "\nRunning linter..."
	@$(MAKE) lint
	@echo "\nRunning type checker..."
	@$(MAKE) type-check
	@echo "\nRunning tests..."
	@$(MAKE) test-cov
	@echo "\n✅ All checks passed!"
