# rehome

## Setting up the dev environment

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone git@github.com:lwatsondev/rehome
cd rehome

uv sync --group dev
uv run pre-commit install

yarn install
```

## Running in dev mode

```sh
## Env var usage for configuration is documented here: https://www.dynaconf.com/envvars/
## Env var prefix is set to 'CFG_', not 'DYNACONF_'.
## Add env vars to 'docker/.env'.
## You can also copy rehome/resources/config/default.toml to instance/config
## Config shouldn't be necessary for dev as everything that needs to be is already configured in the Dockerfile.
docker compose -f docker/compose.yaml up --build --pull always
```
