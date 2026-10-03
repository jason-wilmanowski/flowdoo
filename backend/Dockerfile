# syntax=docker/dockerfile:1
# Build context: backend/. Migrations ship inside the package and run automatically on
# container start (docker-entrypoint.sh, disable with RUN_MIGRATIONS=false).

FROM python:3.12.15-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first for layer caching.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini docker-entrypoint.sh ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 app
USER app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "flow_tracer_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
