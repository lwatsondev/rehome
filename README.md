# rehome

## Setting up the development environment

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone git@github.com:TheReverend403/rehome
cd rehome

uv sync --all-groups
uv run pre-commit install

yarn install
```

## Running

```sh
mkdir config
cp rehome/resources/config/settings.toml config/settings.toml # Edit settings.toml

echo FLASK_APP=rehome\nFLASK_ENV=development > .flaskenv

uv run flask assets build
uv run flask db upgrade
uv run flask user create # Or use /auth/register

# Do not use this in production, use a WSGI server such as gunicorn with rehome:create_app() as your entrypoint.
uv run flask run
```
