# --- Stage 1: Builder ---
FROM python:3.13-slim AS builder

# Install uv directly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Prevent uv from looking for a project root outside /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Install dependencies only (Layer Caching)
# sync --no-dev ensures only production dependencies are installed
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --no-dev --no-install-project

# This creates the uvicorn link in .venv/bin
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# --- Stage 2: Final Runtime ---
FROM python:3.13-slim AS final

# Set the working directory inside the container
WORKDIR /app

# Non-root user for security (Production Best Practice)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 🔧 FIX: Create cache directories BEFORE switching to appuser
RUN mkdir -p /app/.cache/huggingface \
             /app/.cache/transformers \
             /app/.cache/sentence-transformers && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser . .

ENV PATH="/app/.venv/bin:$PATH"
# Ensures app module is found regardless of where you call it
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# 🔧 FIX: Set cache environment variables for HuggingFace/Sentence-Transformers
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers
ENV XDG_CACHE_HOME=/app/.cache

# Use the list form for better signal handling (SIGTERM)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
