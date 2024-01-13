# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm
ARG PYTHON_VERSION=3.12
ARG NODE_VERSION=20
ARG POETRY_VERSION=""
ARG NODE_MODULES="/opt/node"
ARG POETRY_HOME="/opt/poetry"
ARG PYSETUP_PATH="/opt/pysetup"
ARG VENV_PATH="${PYSETUP_PATH}/.venv"

## Base
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} as python-base

ARG POETRY_HOME
ARG POETRY_VERSION
ARG VENV_PATH

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME=${POETRY_HOME} \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=${POETRY_VERSION} \
    PATH="${VENV_PATH}/bin:${POETRY_HOME}/bin:$PATH"


## Python builder
FROM python-base as python-builder-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    libffi-dev \
    libpq-dev \
    && apt-get autoclean && rm -rf /var/lib/apt/lists/*

ARG PYSETUP_PATH

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    curl -sSL https://install.python-poetry.org | python3 -

WORKDIR ${PYSETUP_PATH}

COPY poetry.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --no-root --only main


## JS builder
FROM node:${NODE_VERSION}-${DEBIAN_VERSION}-slim as node-builder-base

ARG NODE_MODULES
WORKDIR ${NODE_MODULES}

COPY yarn.lock package.json ./
RUN --mount=type=cache,target=/usr/local/share/.cache/yarn \
    yarn install

## Base image
FROM python-base as flask-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    libpq5 \
    curl && \
    apt-get autoclean && rm -rf /var/lib/apt/lists/*

ARG VENV_PATH
ARG NODE_MODULES

COPY --from=node-builder-base ${NODE_MODULES}/node_modules ${NODE_MODULES}/
COPY --from=python-builder-base ${VENV_PATH} ${VENV_PATH}

COPY docker/rootfs /

WORKDIR /app

COPY ./rehome ./rehome
COPY ./alembic.ini .

ENV SETTINGS_FILE_FOR_DYNACONF="/config/settings.yml" \
    GUNICORN_HOST="0.0.0.0" \
    GUNICORN_PORT=5000 \
    FLASK_APP="rehome" \
    PATHS_STATIC="/static" \
    PATHS_DATA="/data" \
    PATHS_NODE_MODULES=${NODE_MODULES} \
    NODE_MODULES=${NODE_MODULES}

VOLUME ["/static", "/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/docker-init.sh"]


## Dev image
FROM flask-base as development

ARG PYSETUP_PATH
ARG POETRY_HOME

WORKDIR ${PYSETUP_PATH}

COPY --from=python-builder-base ${POETRY_HOME} ${POETRY_HOME}
COPY --from=python-builder-base ${PYSETUP_PATH} ${PYSETUP_PATH}

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --no-root

ENV FLASK_DEBUG=1 \
    GUNICORN_OPTS="--reload --reload-extra-file /config --reload-extra-file $FLASK_APP/assets"

## Production image
FROM flask-base as production

HEALTHCHECK --interval=30s --timeout=5s CMD ["/docker-healthcheck.sh"]
