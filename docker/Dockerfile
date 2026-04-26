# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=trixie

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
    PYTHONPATH="/app"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY .python-version .

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv python install


## Builder - Gathers version information and installs dependencies.
FROM python-base AS builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && apt-get install --no-install-recommends -y \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN --mount=type=bind,from=dotgit,target=.git \
    --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --no-dev


## App base
FROM python-base AS app-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && apt-get install --no-install-recommends -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

ENV FLASK_APP="rehome" \
    GUNICORN_HOST="0.0.0.0" \
    GUNICORN_PORT=5000 \
    ROOT_PATH_FOR_DYNACONF="/config" \
    CFG_PATHS__INSTANCE="/data"

COPY --from=builder ${UV_PROJECT_ENVIRONMENT} ${UV_PROJECT_ENVIRONMENT}
COPY --from=builder /app /app

RUN ln -s /app/docker/rootfs/* /

VOLUME ["/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base AS development

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && apt-get install --no-install-recommends -y \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV FLASK_ENV=development \
    FLASK_DEBUG=1 \
    ENV_FOR_DYNACONF=development

RUN --mount=type=bind,from=dotgit,target=.git \
    --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --group dev


## Production image
FROM app-base AS production

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && apt-get install --no-install-recommends -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV FLASK_ENV=production \
    ENV_FOR_DYNACONF=production

HEALTHCHECK --start-interval=1s --start-period=10s --interval=10s --timeout=5s CMD ["/docker-healthcheck.sh"]
