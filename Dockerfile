# Stage 1: Build the virtual environment
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Stage 2: Runtime image
# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app data ./data
COPY --chown=app:app prompts ./prompts

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENV APP_ENV=production

USER app

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn chargecheck.api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
