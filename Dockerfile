FROM python:3.9-slim-bullseye AS base

WORKDIR /app

FROM base AS builder

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  PATH="$PATH:/runtime/bin" \
  PYTHONPATH=".:$PYTHONPATH:/runtime/lib/python3.9/site-packages"

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libsass-dev libpq-dev libffi-dev npm

FROM builder AS pydeps

RUN pip install poetry
COPY pyproject.toml poetry.lock /app/
RUN poetry export --dev --without-hashes --no-interaction --no-ansi -f requirements.txt -o requirements.txt
RUN pip install --prefix=/runtime --force-reinstall -r requirements.txt

FROM builder AS nodedeps

COPY package.json yarn.lock /app/
RUN npm install -g yarn && yarn install

FROM builder AS runtime

COPY --from=pydeps /runtime /usr/local
COPY --from=nodedeps /app/node_modules /app/node_modules

COPY .*env alembic.ini /app/
COPY rehome/ /app/rehome
COPY docker/ /app/docker
COPY config/ /app/config

RUN flask assets build
ENTRYPOINT ["/app/docker/entrypoint.sh"]
