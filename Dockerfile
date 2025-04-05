# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm
ARG PYTHON_VERSION=3.13

## Base
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${DEBIAN_VERSION}-slim AS python-base

ARG META_VERSION
ARG META_COMMIT
ARG META_SOURCE

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT="/venv" \
    META_VERSION="${META_VERSION}" \
    META_COMMIT="${META_COMMIT}" \
    META_SOURCE="${META_SOURCE}"

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app


## Python builder
FROM python-base AS python-builder-base

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-install-project --no-dev


## Base image
FROM python-base AS flask-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    libmagic1 \
    && apt-get autoclean && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder-base ${UV_PROJECT_ENVIRONMENT} ${UV_PROJECT_ENVIRONMENT}
COPY docker/rootfs /
COPY rehome ./rehome

ENV ROOT_PATH_FOR_DYNACONF="/config" \
    SETTINGS_FILES_FOR_DYNACONF='["/app/rehome/resources/config/default.toml", "*.toml"]' \
    GUNICORN_HOST="0.0.0.0" \
    GUNICORN_PORT=5000 \
    FLASK_APP="rehome" \
    CFG_SQLALCHEMY_DATABASE_URI="sqlite:////data/app.db" \
    CFG_PATHS__DATA="/data" \
    CFG_PATHS__MIGRATIONS="/app/rehome/db/migrations"

VOLUME ["/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM flask-base AS development

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-install-project --group dev

ENV ENV_FOR_DYNACONF=development \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    CFG_SECRET_KEY=dev \
    CFG_AUTH__TOKEN=dev


## Production image
FROM flask-base AS production

ENV ENV_FOR_DYNACONF=production \
    FLASK_ENV=production

HEALTHCHECK --start-interval=1s --start-period=10s --interval=10s --timeout=5s CMD ["/docker-healthcheck.sh"]
