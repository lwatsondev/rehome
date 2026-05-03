#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.0",
#     "dynaconf>=3.0",
#     "niquests[speedups]",
# ]
# ///

import os
import sys
from pathlib import Path

import click
import niquests
from dynaconf import Dynaconf
from dynaconf.loaders import write as dynaconf_write

_XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_CONFIG_DIR = _XDG_CONFIG_HOME / "rehome"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"
_DEFAULT_BASE_URL = "https://lwatson.dev"


class UploadError(Exception):
    pass


class _ConnectionError(UploadError):
    def __init__(self, base_url: str) -> None:
        super().__init__(f"Could not connect to {base_url}.")


class _TimeoutError(UploadError):
    def __init__(self, base_url: str) -> None:
        super().__init__(f"Request to {base_url} timed out.")


class _RequestError(UploadError):
    def __init__(self, exc: Exception) -> None:
        super().__init__(f"Request failed: {exc}.")


class _ServerError(UploadError):
    def __init__(self, error: str) -> None:
        super().__init__(f"Upload failed: {error}")


def _load_config() -> Dynaconf:
    return Dynaconf(
        settings_files=[str(_CONFIG_FILE)],
        environments=False,
        envvar_prefix="REHOME",
        load_dotenv=False,
    )


def _save_config(token: str, base_url: str) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    dynaconf_write(str(_CONFIG_FILE), {"base_url": base_url, "auth": {"token": token}})


def _ensure_config() -> Dynaconf:
    config = _load_config() if _CONFIG_FILE.exists() else None

    base_url = config.get("base_url") if config else None
    token = config.get("auth.token") if config else None

    needs_save = False

    if not base_url:
        base_url = click.prompt("Base URL", default=_DEFAULT_BASE_URL)
        needs_save = True

    if not token:
        if config:
            click.echo("No auth token found in config.")
        else:
            click.echo("No configuration found.")
        token = click.prompt("Auth token", hide_input=True)
        needs_save = True

    if needs_save:
        _save_config(token, base_url)
        return _load_config()

    return config


def _upload(file: Path, base_url: str, token: str) -> str:
    try:
        with file.open("rb") as f:
            response = niquests.post(
                f"{base_url}/f/",
                files={"file": (file.name, f)},
                headers={"Authorization": f"Bearer {token}"},
            )
    except niquests.exceptions.ConnectionError:
        raise _ConnectionError(base_url) from None
    except niquests.exceptions.Timeout:
        raise _TimeoutError(base_url) from None
    except niquests.exceptions.RequestException as exc:
        raise _RequestError(exc) from exc

    if not response.ok:
        try:
            error = response.json().get("error", response.reason)
            if isinstance(error, dict):
                error = "\n".join(
                    f"{field}: {', '.join(msgs)}" for field, msgs in error.items()
                )
        except ValueError, TypeError:
            error = response.reason or f"HTTP {response.status_code}"
        raise _ServerError(error)

    return response.json()["url"]


@click.command()
@click.argument("file", type=click.Path(exists=True, readable=True, path_type=Path))
def main(file: Path) -> None:
    config = _ensure_config()

    base_url = config.get("base_url", _DEFAULT_BASE_URL).rstrip("/")
    token = config.get("auth.token")

    try:
        url = _upload(file, base_url, token)
    except UploadError as exc:
        click.echo(str(exc))
        sys.exit(1)

    click.echo(url)


if __name__ == "__main__":
    main()
