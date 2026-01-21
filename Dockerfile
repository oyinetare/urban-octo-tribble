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

# --- Stage 2: Final Runtime ---
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Add a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set production environment variables to optimize Python performance in Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy ONLY the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy your application code
COPY . .

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Expose the port (FastAPI standard is 8000)
EXPOSE 8000

# Use uvicorn or the standard FastAPI runner
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
