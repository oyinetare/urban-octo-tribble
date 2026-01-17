# urban-octo-tribble

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [Features](#features)
<!-- - [Quick Start] -->
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Development Commands](#development-commands)
- [API Usage](#api-usage)
- [Interactive Documentation](#interactive-documentation)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Code Quality](#code-quality)
- [References/Acknowledgments](#referencesacknowledgments)

---
## Features

1. **Basic CRUD API built with FASTAPI**
    1. RESTful with 15+ endpoints
    2. JWT authentication with refresh tokens for secure password handling
    3. Rate Limiting using Token Bucket algorithm to prevent API abuse
    4. Twitter Snowflake algorithm for distributed IDs
    5. Base62 URL shortening for document sharing
    6. Multi-channel event-driven notifications (in-app, reliable webhooks, email)
    7. Comprehensive tests and production configuration
2. **RAG System, AI-powered document analysis with semantic search and RAG**
    1. File upload with MinIO (S3-compatible storage)
    2. Text Extraction Pipeline implemented with Background workers to extract text from documents, Document Chunking
    3. Document Chunking where documents are split into 500-token chunks with 50-token overlap
    4. Vector Embeddings & Search: Generating embeddings and implemented semantic search with Qdrant
    5. Combine search with Claude + Ollama for document Q&A (RAG Implementation)
    6. Hybrid Search: Combining vector + keyword search with RRF re-ranking
    7. Production Optimization: Caching, cost reduction, and performance tuning
3. **Agentic AI Platform, Autonomous AI agents with event-driven architecture and production deployment**
    1. AI agents with tools for autonomous multi-step reasoning built with LangGraph Agent Framework
    2. Event Streaming implemeted with Redpanda, event-driven architecture with pub/sub messaging
    3. Intelligent Triggers, pattern detection (trends, anomalies) with automated actions
    4. Real-Time Chat, WebSocket chat with streaming agent responses
    5. Distributed load using consistent hash ring with virtual nodes
    6. Multiple API instances with nginx load balancer for Horizontal Scaling
    7. 011y (Observability): Metrics, dashboards, and alerting using Prometheus and Grafana
    8. Production deployment with CI/CD

___

## Tech Stack

___

## Architecture

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
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Doc", "description": "Test"}' | jq

# 2. Get document ID
curl -X GET http://localhost:8000/api/v1/documents/{docuemnt_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq

# 3. Get all documents
curl -X GET http://localhost:8000/api/v1/documents/ \
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
curl -X POST http://localhost:8000/api/v1/documents/share/{docuemnt_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq
```

```bash
# Test Security headers present in responses
curl -X GET -I http://localhost:8000/
curl -v http://localhost:8000/
```
___

## Interactive Documentation

Once the server is running, explore the full API:

___

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
### Articles/Websites
  - [Azure application architecture fundamentals](https://learn.microsoft.com/en-us/azure/architecture/guide/)
      - [API design](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design)
      - [Best practices for RESTful web API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
  - [FastAPI Documentation](https://fastapi.tiangolo.com/learn/)
  - [The System Design Primer by Donne Martin](https://github.com/donnemartin/system-design-primer)

### Books
  - Xu, A. (2020). System design interview – An insider's guide (2nd ed.). Byte Code LLC / Independently published.
  - Kleppmann, Martin. Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems. O'Reilly Media, 2017
