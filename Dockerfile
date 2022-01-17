## Base
FROM python:3.9-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.12 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    NODE_MODULES="/opt/node"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


## Python builder
FROM python-base as python-builder-base

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        libffi-dev \
        libpq-dev

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python -

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev


## JS builder
FROM node:17-buster-slim as node-builder-base

ENV NODE_MODULES="/opt/node"
WORKDIR $NODE_MODULES

COPY yarn.lock package.json ./
RUN yarn install


## Production image
FROM python-base as production

COPY --from=sudobmitch/base:scratch / /
COPY docker/entrypoint.d/ /etc/entrypoint.d/

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        util-linux \
        libpq5 \
        rsync

RUN rm -rf /var/lib/apt/lists/*

COPY --from=python-builder-base $PYSETUP_PATH $PYSETUP_PATH
COPY --from=node-builder-base $NODE_MODULES/node_modules $NODE_MODULES/

RUN addgroup --gid 1000 --system rehome && \
    adduser --uid 1000 --system --gid 1000 --no-create-home rehome

WORKDIR /app

COPY --chown=rehome:rehome ./rehome ./rehome
COPY --chown=rehome:rehome ./alembic.ini .

ENV GUNICORN_WORKERS=1
ENV SETTINGS_FILE_FOR_DYNACONF="/config/settings.yml"
ENV FLASK_APP="rehome"
ENV FLASK_ENV="production"
ENV FLASK_STATIC_DIR="/static"
ENV FLASK_DATA_DIR="/data"
ENV PYTHONPATH="/app:$VENV_PATH/lib/python3.9/site-packages"

VOLUME ["/static", "/config", "/data"]
EXPOSE 5000

ENTRYPOINT ["/usr/bin/entrypointd.sh"]
CMD ["sh", "-c", "gunicorn 'rehome:create_app()' --workers $GUNICORN_WORKERS --worker-class gevent --bind 0.0.0.0:5000"]
