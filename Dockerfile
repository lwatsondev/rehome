ARG ARG_PYTHON_VERSION=3.9
ARG ARG_NODE_VERSION=17
ARG ARG_POETRY_VERSION=1.1.14
ARG ARG_S6_OVERLAY_VERSION=3.1.1.2
ARG ARG_S6_DOWNLOAD_PATH="/opt/s6"
ARG ARG_NODE_MODULES="/opt/node"
ARG ARG_POETRY_HOME="/opt/poetry"
ARG ARG_PYSETUP_PATH="/opt/pysetup"
ARG ARG_VENV_PATH="/opt/pysetup/.venv"

## Base
FROM python:${ARG_PYTHON_VERSION}-slim as python-base

ARG ARG_POETRY_HOME
ARG ARG_VENV_PATH

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME=${ARG_POETRY_HOME} \
    PATH="${ARG_VENV_PATH}/bin:${ARG_POETRY_HOME}/bin:$PATH"


FROM python-base as s6-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    xz-utils \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG ARG_S6_OVERLAY_VERSION
ARG ARG_S6_DOWNLOAD_PATH

#https://github.com/just-containers/s6-overlay/releases/download/v3.1.1.2/s6-overlay-x86_64.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${ARG_S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
ADD https://github.com/just-containers/s6-overlay/releases/download/v${ARG_S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN mkdir -p "${ARG_S6_DOWNLOAD_PATH}" && \
    tar -C "${ARG_S6_DOWNLOAD_PATH}" -Jxpf /tmp/s6-overlay-x86_64.tar.xz && \
    tar -C "${ARG_S6_DOWNLOAD_PATH}" -Jxpf /tmp/s6-overlay-noarch.tar.xz


## Python builder
FROM python-base as python-builder-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        libffi-dev \
        libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG ARG_POETRY_VERSION
ARG ARG_PYSETUP_PATH

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=${ARG_POETRY_VERSION}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org | python -

WORKDIR ${ARG_PYSETUP_PATH}

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev


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

ARG ARG_S6_DOWNLOAD_PATH
ARG ARG_VENV_PATH
ARG ARG_NODE_MODULES

COPY --from=s6-base ${ARG_S6_DOWNLOAD_PATH} /
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
    NODE_MODULES=${ARG_NODE_MODULES} \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    S6_READ_ONLY_ROOT=1

VOLUME ["/static", "/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/init"]


## Dev image
FROM flask-base as development

ARG ARG_PYSETUP_PATH
ARG ARG_POETRY_HOME

WORKDIR ${ARG_PYSETUP_PATH}

COPY --from=python-builder-base ${ARG_POETRY_HOME} ${ARG_POETRY_HOME}
COPY --from=python-builder-base ${ARG_PYSETUP_PATH} ${ARG_PYSETUP_PATH}

RUN poetry install

ENV FLASK_ENV="development" \
    GUNICORN_OPTS="--reload --reload-extra-file /config --reload-extra-file rehome/assets"

## Production image
FROM flask-base as production

ENV FLASK_ENV="production"

HEALTHCHECK --interval=10s --timeout=5s CMD ["/bin/healthcheck"]
