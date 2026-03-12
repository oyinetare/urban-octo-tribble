# urban-octo-tribble

[![Tests](https://github.com/oyinetare/urban-octo-tribble/actions/workflows/tests.yml/badge.svg)](https://github.com/oyinetare/urban-octo-tribble/actions/workflows/tests.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
<!-- [![codecov](https://codecov.io)](https://codecov.io) -->

## 📋 Table of Contents

API backend built w FASTAPI with Auth, Rate Limiting demonstrating system design concepts with progressive complexity.

<!-- - [Features](#features) -->
<!-- - [Quick Start] -->
- [Tech Stack](#tech-stack)
- [System Evolution + Architecture](#architecture)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Development Commands](#development-commands)
- [API Usage](#api-usage)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Code Quality](#code-quality)
- [References/Acknowledgments](#referencesacknowledgments)


___

## Tech Stack

### Core Technologies
```
FastAPI 0.115+         - Async API framework
PostgreSQL 16+         - Primary database
SQLModel              - ORM (SQLAlchemy + Pydantic)
Pydantic              - Data validation
Alembic               - Database migrations
Redis 7+              - Caching + Rate limiting
Python-JOSE           - JWT handling
Passlib               - Password hashing (bcrypt)
```
___


## System Evolution & Architecture

```
Phase 1: RESTful API
    ↓ (adds document processing)
Phase 2: RAG System
    ↓ (adds autonomous intelligence)
Phase 3: Agentic AI Platform
```


### Layered (N-Tier)

#### V1
```
┌─────────────────────────────────────┐
│     Presentation Layer              │
│  FastAPI Routes + Dependencies      │
│  /auth, /users, /documents          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Business Logic Layer           │
│  Route Handlers (inline for now)   │
│  Validation + Business Rules        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Data Access Layer             │
│  SQLModel ORM + Repositories        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Database Layer              │
│  PostgreSQL (ACID, Transactions)    │
└─────────────────────────────────────┘
```

#### V2
```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (nginx)                   │
└───────────────┬─────────────────┬─────────────────┬─────────┘
                │                 │                 │
       ┌────────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
       │  FastAPI API 1  │ │  API 2     │ │  API 3         │
       │  (Stateless)    │ │            │ │                │
       └────────┬────────┘ └─────┬──────┘ └───────┬────────┘
                │                 │                 │
                └─────────────────┼─────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼─────┐    ┌─────────┐   │    ┌──────────┐   ┌────▼────┐
   │PostgreSQL│    │  Redis  │   │    │  Qdrant  │   │  MinIO  │
   │          │    │ (cache) │   │    │ (vector) │   │(storage)│
   └──────────┘    └─────────┘   │    └──────────┘   └─────────┘
                                  │
                         ┌────────▼────────┐
                         │    Redpanda     │
                         │ (Event Stream)  │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
            ┌───────▼──────┐ ┌───▼───────┐ ┌──▼──────────┐
            │ Celery Worker│ │  Triggers │ │  Analytics  │
            │  (RAG Tasks) │ │ (Agents)  │ │             │
            └──────────────┘ └───────────┘ └─────────────┘
                                  │
                         ┌────────▼────────┐
                         │  Prometheus +   │
                         │    Grafana      │
                         │ (Observability) │
                         └─────────────────┘
```

### RAG: Pipes & Filters + Background Processing

```
Upload → Extract → Chunk → Embed → Store → Query
  │        │         │       │       │       │
MinIO   Celery    Celery  Celery  Qdrant  Claude

Each stage is a "filter" that transforms data
Celery queues connect the "pipes" between filters
```

___

## Getting Started

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose
- Make (optional, for convenient commands)

### Installation

#### Quick Start with Make (Recommended)

___

## Development Commands

The project includes a comprehensive Makefile for common tasks:

```bash
make help              # Show all available commands

# Development
make install           # Install production dependencies
make dev-install       # Install all dependencies + dev tools
make run               # Start development server
make run-fresh         # Clean start (rebuild Docker volumes)

# Code Quality
make format            # Format code with Ruff
make lint              # Lint code with Ruff
make type-check        # Type check with Ty
make ci                # Run all checks (format, lint, type-check, test)
make pre-commit        # Run pre-commit on all files

# Testing
make test              # Run tests
make test-cov          # Run tests with coverage report

# Database
make migrate           # Run migrations
make migrate-create    # Create new migration (use: make migrate-create msg="description")
make migrate-down      # Rollback one migration

# Docker
make docker-up         # Start Docker services
make docker-down       # Stop Docker services
make docker-logs       # View Docker logs

# Cleanup
make clean             # Remove cache and build files
```

___

## API Usage

### Health
```bash
curl -X GET http://localhost:8000/health/live | jq

curl -X GET http://localhost:8000/health/ready | jq
```

### Authentication Flow

```bash
# export API_URL="http://localhost:8000"

# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "username": "testuser",
    "password": "password123"
  }' | jq

# 2. Login and save the access token and cookies
TOKEN=$(curl -c cookies.txt -s -X POST http://localhost:8000/api/v1/auth/login \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=testuser&password=password123" | jq -r '.access_token')

# curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
#   -H "Content-Type: application/x-www-form-urlencoded" \
#   -d "username=testuser&password=password123"

####
# 2.1 Refresh token
TOKEN=$(curl -b cookies.txt -s -X POST http://localhost:8000/api/v1/auth/refresh | jq -r '.access_token')

# curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh | jq

# See what is actually happening
# curl -v -b cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh

####
# 3. Access protected endpoints
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

```bash
# Logout
curl -X POST 'http://localhost:8000/api/v1/auth/logout' \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Docments
```bash
# 1. Create a document
# curl -X POST http://localhost:8000/api/v1/documents \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"title": "Test Doc", "description": "Test"}' | jq

# Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
   -H "Authorization: Bearer $TOKEN" \
   -F "file=On System Design by Jim Waldo.pdf" \
   -F "title=Test" \
   -F "description=Test description" | jq

# procewsing status
# curl -X GET http://localhost:8000/api/v1/documents/{docuemnt_id}/status\
#   -H "Authorization: Bearer $TOKEN" | jq

RESPONSE=$(curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@On System Design by Jim Waldo.pdf" \
  -F "title=On System Design by Jim Waldo" \
  -F "description=")

# Print the response pretty-printed
echo $RESPONSE | jq

# Extract the document_id for the next command
DOC_ID=$(echo $RESPONSE | jq -r '.id')


curl -X GET http://localhost:8000/api/v1/documents/$DOC_ID/status \
  -H "Authorization: Bearer $TOKEN" | jq

# loop to watch the percentage go up in real-time
while true; do
  STATUS_RESP=$(curl -s -X GET http://localhost:8000/api/v1/documents/$DOC_ID/status -H "Authorization: Bearer $TOKEN")
  echo $STATUS_RESP | jq -c '.'

  # Exit loop if completed or failed
  CURRENT_STATUS=$(echo $STATUS_RESP | jq -r '.status')
  if [[ "$CURRENT_STATUS" == "completed" || "$CURRENT_STATUS" == "failed" ]]; then
    break
  fi
  sleep 1
done


# 2. Get document ID
curl -X GET http://localhost:8000/api/v1/documents/{docuemnt_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

# 3. Get all documents
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

# 4. Delete document
curl -X DELETE http://localhost:8000/api/v1/documents/{docuemnt_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

# 5. Update a document
curl -X PUT http://localhost:8000/api/v1/documents/{docuemnt_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Test update description"}' | jq

# 6. share document link
curl -X POST http://localhost:8000/api/v1/documents/$DOC_ID/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

```bash
# Test Security headers present in responses
curl -X GET -I http://localhost:8000/d/2oLIZi1bnwI
curl -v http://localhost:8000/
```
---

## Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
uv run pytest tests/test_auth.py -v

# Run with verbose output
uv run pytest -vv
```

___

## Project Structure

```
└── urban-octo-tribble
    └── .github
        └── workflows
            ├── tests.yml
        ├── PULL_REQUEST_TEMPLATE.md
    └── alembic
        ├── env.py
        ├── README
        ├── script.py.mako
    └── app
        └── core
            ├── __init__.py
            ├── config.py
            ├── constants.py
            ├── database.py
            ├── extractors.py
            ├── logging.py
            ├── security.py
            ├── services.py
        └── middleware
            ├── __init__.py
            ├── https_redirect.py
            ├── idempotency.py
            ├── logging.py
            ├── rate_limit.py
            ├── security_headers.py
            ├── versioning.py
        └── models
            ├── __init__.py
            ├── base.py
            ├── chunk.py
            ├── document.py
            ├── query.py
            ├── shorturl.py
            ├── user.py
        └── routes
            ├── __init__.py
            ├── auth.py
            ├── documents.py
            ├── metrics.py
            ├── query.py
            ├── users.py
        └── schemas
            ├── __init__.py
            ├── document.py
            ├── events.py
            ├── metrics.py
            ├── pagination.py
            ├── query.py
            ├── search.py
            ├── shorturl.py
            ├── user.py
        └── services
            └── ai
                ├── __init__.py
                ├── chunking.py
                ├── embeddings.py
                ├── hybrid_search.py
                ├── llm.py
                ├── query_classifier.py
                ├── rag.py
                ├── vector_store.py
            └── events
                ├── __init__.py
                ├── consumer.py
                ├── producer.py
            └── optimization
                ├── __init__.py
                ├── metrics_service.py
                ├── redis_service.py
            └── storage
                ├── __init__.py
                ├── minio_adapter.py
            └── validation
                ├── __init__.py
                ├── validators.py
            ├── __init__.py
        └── tasks
            ├── __init__.py
            ├── base.py
            ├── chunks_embedding.py
            ├── document_chunking.py
            ├── document_processing.py
        └── utility
            ├── __init__.py
            ├── base62_encoder.py
            ├── snowflake.py
            ├── utc_now.py
        ├── __init__.py
        ├── celery_app.py
        ├── dependencies.py
        ├── exceptions.py
        ├── main.py
    └── scripts
        ├── analytics_consumer.py
        ├── event_consumer.py
    └── tests
    ├── .dockerignore
    ├── .env.example
    ├── .env.test
    ├── .gitignore
    ├── .pre-commit-config.yaml
    ├── .python-version
    ├── alembic.ini
    ├── docker-compose.override.yml
    ├── docker-compose.yaml
    ├── Dockerfile
    ├── Makefile
    ├── pyproject.toml
    ├── pytest.ini
    ├── README.md
    └── uv.lock
```
___

## Code Quality

This project uses Astral's modern Python tooling:

- **uv**: Fast Python package installer and resolver
- **Ruff**: Extremely fast Python linter and formatter
- **Ty**: Ultra-fast type checker
- **pre-commit**: Git hooks for automated checks

### Configuration

All tools are configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ty]
[tool.ty.environment]
python-version = "3.13"
```

### Running Checks

```bash
# Format and fix code
make format

# Check linting
make lint

# Type checking
make type-check

# Run all CI checks
make ci
```

___

## References/Acknowledgments
- Azure Architecture
    - [Best practices for RESTful web API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
    - [API design](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design)
- [FastAPI Docs (Learn)](https://fastapi.tiangolo.com/learn/)
