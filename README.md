# rehome

## Setting up the dev environment

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone git@github.com:TheReverend403/rehome
cd rehome

uv sync --group dev
uv run pre-commit install

yarn install
```

## Running in dev mode

### Docker

```sh
cp docker/.env.example docker/.env # Open and set any empty variables
docker compose -f docker/docker-compose.dev.yml up --build --pull always
```

### Manual

```sh
mkdir config
cp rehome/resources/config/settings.toml config/settings.toml # Edit settings.toml

uv run flask assets build
uv run flask db upgrade
uv run flask user create # Or use /auth/register

# Do not use this in production, use a WSGI server such as gunicorn with rehome:create_app() as your entrypoint.
uv run flask run
```
