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
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Install uv in the final stage too (standard practice in 2026)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy venv and code
COPY --from=builder /app/.venv /app/.venv
COPY . .

# Environment setup
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Use uv run to ensure the environment is activated correctly
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
