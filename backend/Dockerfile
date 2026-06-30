# --- uv source for builder stage ---
FROM ghcr.io/astral-sh/uv:0.11.25@sha256:1e3808aa9023d0980e7c15b1fa7c1ac16ff35925780cf5c459858b2d693f01a9  AS uv-source

# --- dbmate source for database migrations ---
FROM amacneil/dbmate:2.33.0@sha256:cbdf9e3631ff1c70a8a7a0091437bdd63c8525407009c2541273ee19e6eebc9e AS dbmate

# --- Build stage: resolve and install dependencies into a venv ---
FROM python:3.12-slim@sha256:6c4dd321d176d61ea848dc8c73a4f7dbae8f70e0ee48bb411ea2f045b599fa8e AS builder

# uv is the package manager (https://docs.astral.sh/uv/)
COPY --from=uv-source /uv /usr/local/bin/uv

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

# --- Runtime stage: slim image with just the venv and source ---
FROM python:3.12-slim@sha256:6c4dd321d176d61ea848dc8c73a4f7dbae8f70e0ee48bb411ea2f045b599fa8e AS runtime

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
