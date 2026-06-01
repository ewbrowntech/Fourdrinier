# syntax=docker/dockerfile:1

########################################################
# Arguments
########################################################

ARG PYTHON_VERSION=3.12

########################################################
# Base — Python runtime with uv
########################################################

FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

########################################################
# Builder — production dependencies
########################################################

FROM base AS builder-prod

COPY backend/pyproject.toml backend/uv.lock backend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --directory backend

COPY backend/fourdrinier/ backend/fourdrinier/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --directory backend

########################################################
# Builder — debug/test dependencies
########################################################

FROM base AS builder-debug

COPY backend/pyproject.toml backend/uv.lock backend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --directory backend

COPY backend/fourdrinier/ backend/fourdrinier/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --directory backend

########################################################
# Production runtime
########################################################

FROM base AS prod

ENV PATH="/app/backend/.venv/bin:$PATH"

COPY --from=builder-prod /app/backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "-m", "fourdrinier.main"]

########################################################
# Debug/test runtime
########################################################

FROM base AS debug

ENV PATH="/app/backend/.venv/bin:$PATH"

COPY --from=builder-debug /app/backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "uv sync && exec python -m fourdrinier.main"]
