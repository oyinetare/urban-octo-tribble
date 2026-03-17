# Intelligent Document Analyst

[![Tests](https://github.com/oyinetare/urban-octo-tribble/actions/workflows/tests.yml/badge.svg)](https://github.com/oyinetare/urban-octo-tribble/actions/workflows/tests.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade AI backend built across three phases of increasing complexity. From a secure REST API foundation through to a full RAG system with hybrid semantic search, agentic AI workflows, and event-driven architecture.

---

## Build status

| Phase | Status | Notes |
|-------|--------|-------|
| Project 1 — RESTful API | ✅ Complete | Auth, rate limiting, Snowflake IDs, URL shortener, idempotency |
| Project 2 — RAG System | ✅ Complete | Document pipeline, hybrid search, RAG generation, caching |
| Project 3 — Agentic Platform | 🔧 In progress | Event streaming (Redpanda) done; LangGraph agent, WebSockets, observability, and production deployment in progress |

---

## System evolution

```
Phase 1: RESTful API          — Auth, rate limiting, distributed IDs, URL shortening
    ↓
Phase 2: RAG System           — Document ingestion, vector search, hybrid retrieval, LLM generation
    ↓
Phase 3: Agentic AI Platform  — LangGraph agents, event streaming, observability, horizontal scaling
```

Each phase builds on the last. The codebase is intentionally structured so that every component can be discussed in terms of the design decision it encodes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (nginx)                   │
└───────────────┬─────────────────┬─────────────────┬─────────┘
                │                 │                 │
       ┌────────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
       │  FastAPI API 1  │ │  API 2     │ │  API 3         │
       │  (Stateless)    │ │            │ │                │
       └────────┬────────┘ └─────┬──────┘ └───────┬────────┘
                └─────────────────┼─────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼─────┐    ┌─────────┐    │    ┌──────────┐   ┌────▼────┐
   │PostgreSQL│    │  Redis  │    │    │  Qdrant  │   │  MinIO  │
   │          │    │ cache + │    │    │  vector  │   │  S3     │
   │          │    │ rate lmt│    │    │  store   │   │ storage │
   └──────────┘    └─────────┘    │    └──────────┘   └─────────┘
                                  │
                         ┌────────▼────────┐
                         │    Redpanda     │
                         │ (Event stream)  │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
            ┌───────▼──────┐ ┌───▼───────┐ ┌──▼──────────┐
            │ Celery Worker│ │  Triggers │ │  Analytics  │
            │  (RAG tasks) │ │ (Agents)  │ │             │
            └──────────────┘ └───────────┘ └─────────────┘
                                  │
                         ┌────────▼────────┐
                         │  Prometheus +   │
                         │    Grafana      │
                         └─────────────────┘
```

---

## Tech stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API framework | FastAPI 0.115+ | Async routes, dependency injection, OpenAPI |
| ORM | SQLModel + Alembic | Type-safe models, schema migrations |
| Primary DB | PostgreSQL 16+ | ACID transactions, full-text search (GIN indexes) |
| Cache + rate limiting | Redis 7+ | Token bucket state, JWT blacklist, query cache |
| Object storage | MinIO (S3-compatible) | Raw document storage |
| Vector DB | Qdrant | HNSW index, approximate nearest neighbour search |
| Embeddings | Sentence Transformers | Dense vector generation |
| Task queue | Celery | Async document processing pipeline |
| LLM | Claude Sonnet 4 (Anthropic) | RAG generation, agentic reasoning |
| Agent framework | LangGraph | State machine, tool-calling, multi-step reasoning |
| Event streaming | Redpanda (Kafka-compatible) | Pub/sub, event sourcing, async triggers |
| Monitoring | Prometheus + Grafana | RED metrics, dashboards, alerting |
| Package manager | uv | Fast dependency resolution |
| Linter/formatter | Ruff | Consistent code style |
| Type checker | Ty | Static analysis |

---

## Phase 1: RESTful API

**Architecture pattern:** N-tier layered (presentation → business logic → data access → database)

```
┌─────────────────────────────────────┐
│     Presentation Layer              │
│  FastAPI routes + dependencies      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Business Logic Layer           │
│  Validation + business rules        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Data Access Layer             │
│  SQLModel ORM + repositories        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Database Layer              │
│  PostgreSQL (ACID, transactions)    │
└─────────────────────────────────────┘
```

**What's implemented:**

**Authentication and security** — JWT access tokens (15 min TTL) and refresh tokens (7 days), bcrypt password hashing, token blacklist in Redis on logout, CORS, HTTPS enforcement, and security headers middleware.

**Rate limiting** — Token Bucket algorithm implemented in middleware. State stored per-user in Redis (`rate:{user_id}`). Free tier: 10 req/min, paid tier: 100 req/min. Returns `429` with `X-RateLimit-*` headers on exhaustion.

**Distributed ID generation** — Twitter Snowflake implementation: 41-bit timestamp + 5-bit datacenter + 5-bit worker + 12-bit sequence. Thread-safe, handles clock skew, generates 4,096 unique IDs per millisecond per worker. All models use Snowflake IDs over auto-increment.

**URL shortener** — Base62 encoding of Snowflake IDs produces 11-character codes (3.5 trillion possible URLs). Redirects via `GET /{short_code}` with click analytics tracked per link.

**Idempotency, versioning, pagination** — Idempotency middleware prevents duplicate POST side effects using a Redis-backed request hash. URI versioning (`/api/v1/`). Cursor-based pagination on list endpoints.

---

## Phase 2: RAG System

**Architecture pattern:** Pipes and filters

```
Upload → Extract → Chunk → Embed → Store → Query
  │         │         │       │       │       │
MinIO    Celery    Celery  Celery  Qdrant  Claude

Each stage is a filter transforming data.
Celery task queues connect the pipes between stages.
```

**What's implemented:**

**Document ingestion** — File upload to MinIO (S3-compatible). Supports PDF, DOCX, and plain text. A Celery task chain fires on upload: extraction → chunking → embedding → vector store write. Processing status is queryable via `GET /documents/{id}/status`.

**Chunking strategy** — Fixed-size chunks with configurable overlap. Overlap preserves semantic context across chunk boundaries. Chunk position and token count stored in PostgreSQL for citation tracking.

**Embeddings and vector search** — Sentence Transformers generate dense vectors. Stored in Qdrant with HNSW index for approximate nearest neighbour search. Cosine similarity scoring.

**Hybrid search** — Combines dense vector search (Qdrant) with sparse keyword search (PostgreSQL full-text, GIN indexes). Results fused using Reciprocal Rank Fusion (RRF). A query classifier routes queries to the appropriate retrieval strategy.

**RAG generation** — Retrieved chunks passed as context to Claude Sonnet 4. Streaming responses via Server-Sent Events (`POST /query/stream`). Query history and token usage persisted to PostgreSQL.

**Caching** — Multi-layer: Redis caches frequent query results with configurable TTL. Metrics endpoint exposes cache hit rate.

---

## Phase 3: Agentic AI Platform

**Architecture pattern:** Event-driven

**What's implemented:**

**LangGraph agent framework** — State machine with four tools: `search_documents` (semantic retrieval), `query_database` (read-only SQL), `generate_report` (multi-document summary), `send_notification`. Implements the ReAct loop (reason → act → observe). Max iterations guard prevents infinite loops. Conversation history persisted and retrievable via `GET /agent/conversations`.

**Event streaming (Redpanda)** — Kafka-compatible pub/sub. Producer publishes domain events (document uploaded, query completed, agent run finished). Consumer services react asynchronously. Redpanda chosen over vanilla Kafka for operational simplicity (no JVM dependency, same wire protocol).

**Intelligent triggers** — Event consumers trigger downstream actions: document processing on upload, agent runs on query patterns, analytics aggregation.

**Observability** — Prometheus metrics exposed at `/metrics`. Grafana dashboards for API performance, RAG pipeline latency, system resources, and business metrics. Alerts configured for error rate >5%, p95 latency >1s, and CPU sustained above 80%.

**Horizontal scaling** — Stateless API instances behind nginx. All shared state (sessions, rate limit buckets, JWT blacklist) in Redis. Designed for 3+ replicas with no sticky sessions required (except WebSocket connections).

---

## Design patterns implemented

| Pattern | Where |
|---------|-------|
| Repository pattern | Data access layer across all models |
| Middleware chain | Auth → rate limit → idempotency → security headers |
| Token Bucket | `middleware/rate_limit.py` |
| Snowflake ID | `utility/snowflake.py` |
| Adapter | `services/storage/minio_adapter.py` — decouples storage interface from S3 implementation |
| Pipes and filters | `tasks/` — document_processing → document_chunking → chunks_embedding |
| Strategy | `services/ai/` — pluggable embedding models, LLM providers (Anthropic / Ollama fallback) |
| Cache-aside | Redis query cache in `services/optimization/redis_service.py` |
| State machine | `services/agent_state.py` — LangGraph agent with typed state transitions |
| Publisher / Subscriber | `services/events/producer.py` + `consumer.py` |
| Facade | `services/ai/hybrid_search.py` — unified interface over vector + keyword search |

---

## Getting started

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- Docker and Docker Compose
- Make (optional)

### Installation

```bash
git clone https://github.com/oyinetare/urban-octo-tribble
cd urban-octo-tribble

# Install dependencies
make dev-install

# Copy and configure environment
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

# Start services (PostgreSQL, Redis, Qdrant, MinIO, Redpanda)
make docker-up

# Run migrations
make migrate

# Start the API
make run
```

### LLM provider configuration

The system supports Anthropic Claude (recommended) or a local Ollama model as fallback.

```bash
# Anthropic (primary)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local fallback)
LLM_FALLBACK_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## Development commands

```bash
make help              # All available commands

make run               # Start dev server
make run-fresh         # Clean start (rebuild Docker volumes)

make format            # Format with Ruff
make lint              # Lint with Ruff
make type-check        # Type check with Ty
make ci                # Run all checks

make test              # Run tests
make test-cov          # Tests with coverage report

make migrate           # Run pending migrations
make migrate-create    # Create migration: make migrate-create msg="description"
make migrate-down      # Rollback one migration

make docker-up         # Start services
make docker-down       # Stop services
make docker-logs       # Tail logs
```

---

## API overview

Full interactive documentation available at `http://localhost:8000/docs` once running.

### Health

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "password123"}'

# Login — saves refresh token cookie, returns access token
TOKEN=$(curl -c cookies.txt -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=password123" | jq -r '.access_token')

# Refresh
TOKEN=$(curl -b cookies.txt -s -X POST http://localhost:8000/api/v1/auth/refresh | jq -r '.access_token')

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

### Documents

```bash
# Upload and begin processing
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "title=My Document")

DOC_ID=$(echo $RESPONSE | jq -r '.id')

# Poll processing status
curl http://localhost:8000/api/v1/documents/$DOC_ID/status \
  -H "Authorization: Bearer $TOKEN"

# Share (creates short URL)
curl -X POST http://localhost:8000/api/v1/documents/$DOC_ID/share \
  -H "Authorization: Bearer $TOKEN"
```

### Querying

```bash
# Standard RAG query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say about X?", "max_chunks": 5, "min_score": 0.5}'

# Streaming response (SSE)
curl -X POST http://localhost:8000/api/v1/query/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarise the key points", "max_chunks": 5}' \
  --no-buffer

# Query history
curl http://localhost:8000/api/v1/query/history \
  -H "Authorization: Bearer $TOKEN"
```

### Agent

```bash
# Multi-step agent query
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find all documents about system design and generate a summary report"}'

# Streaming agent (shows reasoning + tool calls via SSE)
curl -X POST http://localhost:8000/api/v1/agent/query/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare the documents and identify common themes"}' \
  --no-buffer

# Conversation history
curl http://localhost:8000/api/v1/agent/conversations \
  -H "Authorization: Bearer $TOKEN"
```

---

## Running tests

```bash
make test                                  # Full suite
make test-cov                              # With coverage report
uv run pytest tests/test_auth.py -v        # Single file
uv run pytest -vv                          # Verbose output
```

---

## Project structure

```
urban-octo-tribble/
├── app/
│   ├── core/              # Config, database, security, logging
│   ├── middleware/        # Rate limiting, idempotency, security headers, versioning
│   ├── models/            # SQLModel table definitions
│   ├── routes/            # FastAPI routers (auth, documents, query, agent, metrics)
│   ├── schemas/           # Pydantic request/response models
│   ├── services/
│   │   ├── ai/            # Chunking, embeddings, hybrid search, RAG, vector store, LLM
│   │   ├── events/        # Redpanda producer and consumer
│   │   ├── optimization/  # Redis service, metrics
│   │   ├── storage/       # MinIO adapter
│   │   └── validation/    # File validators
│   ├── tasks/             # Celery tasks: document processing, chunking, embedding
│   ├── utility/           # Snowflake ID, Base62 encoder, UTC helpers
│   ├── celery_app.py
│   ├── dependencies.py
│   ├── exceptions.py
│   └── main.py
├── alembic/               # Migration scripts
├── tests/
├── scripts/               # Event consumer utilities
├── notes/checklists/      # Build documentation
├── .github/workflows/     # CI (tests on PR)
├── docker-compose.yaml
├── docker-compose.override.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

---

## Code quality

All tooling configured in `pyproject.toml`.

```bash
make format      # Ruff format + fix
make lint        # Ruff lint
make type-check  # Ty static analysis
make ci          # All of the above + tests
```

Pre-commit hooks run format, lint, and type checks before every commit.

---

## References

- [Azure REST API design best practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [FastAPI documentation](https://fastapi.tiangolo.com/learn/)
- *On System Design* — Jim Waldo
