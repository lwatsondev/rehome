#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.0",
#     "dynaconf>=3.0",
#     "humanize>=4.0",
#     "niquests[speedups]",
#     "rich>=13.0",
# ]
# ///

import os
import sys
from pathlib import Path

import click
import humanize
import niquests
from dynaconf import Dynaconf
from dynaconf.loaders import write as dynaconf_write
from niquests import Response
from rich.console import Console
from rich.table import Table

_XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_CONFIG_DIR = _XDG_CONFIG_HOME / "rehome"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"
_DEFAULT_BASE_URL = "https://lwatson.dev"


class RehomeError(Exception):
    pass


class _ConnectionError(RehomeError):
    def __init__(self, base_url: str) -> None:
        super().__init__(f"Could not connect to {base_url}.")


class _TimeoutError(RehomeError):
    def __init__(self, base_url: str) -> None:
        super().__init__(f"Request to {base_url} timed out.")


class _RequestError(RehomeError):
    def __init__(self, exc: Exception) -> None:
        super().__init__(f"Request failed: {exc}.")


class _ServerError(RehomeError):
    def __init__(self, error: str) -> None:
        super().__init__(f"Server error: {error}")


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


def _make_request(method: str, url: str, token: str, **kwargs) -> Response:
    base_url = url.split("/f", 1)[0]
    try:
        return niquests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )
    except niquests.exceptions.ConnectionError:
        raise _ConnectionError(base_url) from None
    except niquests.exceptions.Timeout:
        raise _TimeoutError(base_url) from None
    except niquests.exceptions.RequestException as exc:
        raise _RequestError(exc) from exc


def _check_response(response: Response) -> None:
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


def _upload(file: Path, base_url: str, token: str) -> str:
    with file.open("rb") as fd:
        response = _make_request(
            "POST",
            f"{base_url}/f/",
            token,
            files={"file": (file.name, fd)},
        )
    _check_response(response)
    return response.json()["url"]


def _list_uploads(base_url: str, token: str) -> list[dict]:
    response = _make_request("GET", f"{base_url}/f/", token)
    _check_response(response)
    return response.json()


def _delete_uploads(slugs: list[str], base_url: str, token: str) -> int:
    response = _make_request("DELETE", f"{base_url}/f/", token, json={"slugs": slugs})
    _check_response(response)
    return response.json()["deleted"]


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    config = _ensure_config()
    ctx.ensure_object(dict)
    ctx.obj["base_url"] = config.get("base_url", _DEFAULT_BASE_URL).rstrip("/")
    ctx.obj["token"] = config.get("auth.token")


@cli.command("upload")
@click.argument("file", type=click.Path(exists=True, readable=True, path_type=Path))
@click.pass_obj
def upload_cmd(obj: dict, file: Path) -> None:
    try:
        url = _upload(file, obj["base_url"], obj["token"])
    except RehomeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    click.echo(url)


@cli.command("list")
@click.pass_obj
def list_cmd(obj: dict) -> None:
    try:
        uploads = _list_uploads(obj["base_url"], obj["token"])
    except RehomeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    if not uploads:
        click.echo("No files.")
        return

    table = Table(show_edge=False, pad_edge=False)
    table.add_column("Name", style="bold")
    table.add_column("Slug")
    table.add_column("Size")
    table.add_column("Type")
    table.add_column("Created")
    for upload in uploads:
        table.add_row(
            upload["name"],
            upload["slug"],
            humanize.naturalsize(upload["size"]),
            upload["mimetype"],
            upload["created_at"],
        )
    Console().print(table)


@cli.command("delete")
@click.argument("slugs", nargs=-1, required=True)
@click.pass_obj
def delete_cmd(obj: dict, slugs: tuple[str, ...]) -> None:
    try:
        count = _delete_uploads(list(slugs), obj["base_url"], obj["token"])
    except RehomeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    noun = "file" if count == 1 else "files"
    click.echo(f"Deleted {count} {noun}.")


if __name__ == "__main__":
    cli()
