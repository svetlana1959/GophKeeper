# --- Build stage: resolve and install dependencies into a venv ---
FROM python:3.12-slim AS builder

# uv is the package manager (https://docs.astral.sh/uv/)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached layer), without the project itself.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project --no-dev

# Then install the project.
COPY src ./src
COPY README.md ./
RUN uv sync --no-dev

# --- dbmate source for database migrations ---
FROM amacneil/dbmate:2.33.0 AS dbmate

# --- Runtime stage: slim image with just the venv and source ---
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1001 app
WORKDIR /app

COPY --from=dbmate /usr/local/bin/dbmate /usr/local/bin/dbmate
RUN echo '#!/bin/sh\n\
echo "Running migrations..." && \n\
dbmate -d /db/migrations up \n\
echo "Starting application..." && \n\
exec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && \
    chown app:app /app/entrypoint.sh

COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8080
ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD ["uvicorn", "gophkeeper.main:app", "--host", "0.0.0.0", "--port", "8080"]
