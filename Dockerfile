# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm

## Base
FROM debian:${DEBIAN_VERSION}-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=1 \
    UV_PROJECT_ENVIRONMENT="/opt/uv/venv" \
    UV_PYTHON_INSTALL_DIR="/opt/uv/python" \
    UV_CACHE_DIR="/opt/uv/cache"

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY .python-version ./

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv python install


## Base image
FROM python-base AS app-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    libmagic1 \
    && apt-get autoclean && rm -rf /var/lib/apt/lists/*

ARG META_VERSION
ARG META_COMMIT
ARG META_SOURCE

ENV META_VERSION="${META_VERSION}" \
    META_COMMIT="${META_COMMIT}" \
    META_SOURCE="${META_SOURCE}" \
    FLASK_APP="rehome" \
    GUNICORN_HOST="0.0.0.0" \
    GUNICORN_PORT=5000 \
    ROOT_PATH_FOR_DYNACONF="/config" \
    SETTINGS_FILES_FOR_DYNACONF='["/app/rehome/resources/config/default.toml", "*.toml"]' \
    CFG_SQLALCHEMY_DATABASE_URI="sqlite:////data/app.db" \
    CFG_PATHS__DATA="/data"

COPY docker/rootfs /
COPY pyproject.toml uv.lock README.md ./
COPY rehome ./rehome
COPY alembic.ini .

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --no-install-project --no-dev

VOLUME ["/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base AS development

ENV FLASK_ENV=development \
    FLASK_DEBUG=1 \
    ENV_FOR_DYNACONF=development \
    CFG_SECRET_KEY=dev \
    CFG_AUTH__TOKEN=dev

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --no-install-project --group dev


## Production image
FROM app-base AS production

ENV FLASK_ENV=production \
    ENV_FOR_DYNACONF=production

HEALTHCHECK --start-interval=1s --start-period=10s --interval=10s --timeout=5s CMD ["/docker-healthcheck.sh"]
