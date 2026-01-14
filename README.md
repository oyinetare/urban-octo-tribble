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
export API_URL="http://localhost:8000"

# 1. Register a new user
export API_URL="http://localhost:8000"
curl -X POST $API_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }' | jq

# 2. Login and save the access token
TOKEN=$(curl -X POST $API_URL/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123" | jq -r '.access_token')

# 3. Access protected endpoints
curl -X GET $API_URL/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

```bash
# Logout
curl -X POST 'http://localhost:8000/api/v1/auth/logout' \
  -H "Authorization: Bearer $TOKEN" | jq
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
- Azure Architecture
    - [Best practices for RESTful web API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
    - [API design](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design)
- [FastAPI Docs (Learn)](https://fastapi.tiangolo.com/learn/)
