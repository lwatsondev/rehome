ARG ARG_PYTHON_VERSION=3.11
ARG ARG_NODE_VERSION=18
ARG ARG_POETRY_VERSION=1.3.2
ARG ARG_NODE_MODULES="/opt/node"
ARG ARG_POETRY_HOME="/opt/poetry"
ARG ARG_PYSETUP_PATH="/opt/pysetup"
ARG ARG_VENV_PATH="${ARG_PYSETUP_PATH}/.venv"

## Base
FROM python:${ARG_PYTHON_VERSION}-slim as python-base

ARG ARG_POETRY_HOME
ARG ARG_POETRY_VERSION
ARG ARG_VENV_PATH

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME=${ARG_POETRY_HOME} \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=${ARG_POETRY_VERSION} \
    PATH="${ARG_VENV_PATH}/bin:${ARG_POETRY_HOME}/bin:$PATH"


## Python builder
FROM python-base as python-builder-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        libffi-dev \
        libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG ARG_PYSETUP_PATH

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org | python -

WORKDIR ${ARG_PYSETUP_PATH}

COPY poetry.lock pyproject.toml ./
RUN poetry install --only main


## JS builder
FROM node:${ARG_NODE_VERSION}-bullseye-slim as node-builder-base

ARG ARG_NODE_MODULES
WORKDIR ${ARG_NODE_MODULES}

COPY yarn.lock package.json ./
RUN yarn install

## Base image
FROM python-base as flask-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        libpq5 \
        curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG ARG_VENV_PATH
ARG ARG_NODE_MODULES

COPY --from=node-builder-base ${ARG_NODE_MODULES}/node_modules ${ARG_NODE_MODULES}/
COPY --from=python-builder-base ${ARG_VENV_PATH} ${ARG_VENV_PATH}

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
    PATHS_NODE_MODULES=${ARG_NODE_MODULES} \
    NODE_MODULES=${ARG_NODE_MODULES}

VOLUME ["/static", "/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/docker-init.sh"]


## Dev image
FROM flask-base as development

ARG ARG_PYSETUP_PATH
ARG ARG_POETRY_HOME

WORKDIR ${ARG_PYSETUP_PATH}

COPY --from=python-builder-base ${ARG_POETRY_HOME} ${ARG_POETRY_HOME}
COPY --from=python-builder-base ${ARG_PYSETUP_PATH} ${ARG_PYSETUP_PATH}

RUN poetry install

ENV FLASK_DEBUG=1 \
    GUNICORN_OPTS="--reload --reload-extra-file /config --reload-extra-file $FLASK_APP/assets"

## Production image
FROM flask-base as production

HEALTHCHECK --interval=30s --timeout=5s CMD ["/docker-healthcheck.sh"]
