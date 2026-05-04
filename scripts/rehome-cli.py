#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.0",
#     "dynaconf>=3.0",
#     "humanize>=4.0",
#     "niquests[speedups]",
#     "requests-toolbelt>=1.0",
#     "rich>=13.0",
# ]
# ///

import json
import os
import sys
from datetime import UTC, datetime
from http import HTTPMethod
from pathlib import Path

import click
import humanize
from dynaconf import Dynaconf
from dynaconf.loaders import write as dynaconf_write
from niquests import Response, Session
from niquests import exceptions as niquests_exceptions
from requests_toolbelt import MultipartEncoder
from rich import box
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

_XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_CONFIG_DIR = _XDG_CONFIG_HOME / "rehome"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"
_DEFAULT_BASE_URL = "https://lwatson.dev"
_DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
_ORDER_ASC = "asc"
_ORDER_DESC = "desc"

_out = Console()
_err = Console(stderr=True)


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
        base_url = Prompt.ask("Base URL", default=_DEFAULT_BASE_URL, console=_err)
        needs_save = True

    if not token:
        if config:
            _out.print("[yellow]No auth token found in config.[/yellow]")
        else:
            _out.print("[yellow]No configuration found.[/yellow]")
        token = Prompt.ask("Auth token", password=True, console=_err)
        needs_save = True

    if needs_save:
        _save_config(token, base_url)
        return _load_config()

    return config


def _make_session(base_url: str, token: str) -> Session:
    session = Session()
    session.base_url = base_url
    session.headers["Authorization"] = f"Bearer {token}"
    return session


def _make_request(session: Session, method: str, path: str, **kwargs) -> Response:
    try:
        return session.request(method, path, **kwargs)
    except niquests_exceptions.ConnectionError:
        raise _ConnectionError(session.base_url) from None
    except niquests_exceptions.Timeout:
        raise _TimeoutError(session.base_url) from None
    except niquests_exceptions.RequestException as exc:
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


def _upload(session: Session, file: Path) -> str:
    with file.open("rb") as fd:
        encoder = MultipartEncoder(fields={"file": (file.name, fd)})

        with Progress(
            TextColumn("[cyan]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=_err,
        ) as progress:
            task_id = progress.add_task(file.name, total=encoder.len)

            def body():
                while chunk := encoder.read(1 << 17):
                    progress.update(task_id, advance=len(chunk))
                    yield chunk

            response = _make_request(
                session,
                HTTPMethod.POST,
                "/f/",
                data=body(),
                headers={"Content-Type": encoder.content_type},
            )

    _check_response(response)
    return response.json()["url"]


def _list_uploads(session: Session, sort: str, desc: bool) -> list[dict]:
    response = _make_request(
        session,
        HTTPMethod.GET,
        "/f/",
        params={"sort": sort, "order": _ORDER_DESC if desc else _ORDER_ASC},
    )
    _check_response(response)
    return response.json()


def _delete_uploads(session: Session, slugs: list[str]) -> int:
    response = _make_request(session, HTTPMethod.DELETE, "/f/", json={"slugs": slugs})
    _check_response(response)
    return response.json()["deleted"]


def _localtime(dt: datetime, format_str: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone().strftime(format_str or _DEFAULT_DATETIME_FORMAT)


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    config = _ensure_config()

    ctx.ensure_object(dict)
    base_url = config.get("base_url", _DEFAULT_BASE_URL).rstrip("/")
    ctx.obj["session"] = _make_session(base_url, config.get("auth.token"))
    ctx.obj["datetime_format"] = config.get("datetime_format", _DEFAULT_DATETIME_FORMAT)


@cli.command("upload")
@click.argument("file", type=click.Path(exists=True, readable=True, path_type=Path))
@click.pass_obj
def upload_cmd(obj: dict, file: Path) -> None:
    try:
        url = _upload(obj["session"], file)
    except RehomeError as exc:
        _out.print(str(exc))
        sys.exit(1)

    _out.print(url)


@cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(["created", "size", "mimetype"]),
    default="created",
    show_default=True,
    help="Sort by field.",
)
@click.option("--desc", is_flag=True, default=False, help="Sort descending.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@click.pass_obj
def list_cmd(obj: dict, sort: str, desc: bool, as_json: bool) -> None:
    try:
        uploads = _list_uploads(obj["session"], sort, desc)
    except RehomeError as exc:
        _out.print(str(exc))
        sys.exit(1)

    if as_json:
        _out.print(json.dumps(uploads, indent=2), markup=False, highlight=False)
        return

    if not uploads:
        _err.print("No files.")
        return

    table = Table(
        show_edge=False,
        pad_edge=False,
        box=box.ASCII_DOUBLE_HEAD,
        header_style="bold green",
    )
    table.add_column("Name", style="cyan")
    table.add_column("Slug", style="bright_white")
    table.add_column("Size", style="bright_white")
    table.add_column("Type", style="bright_white")
    table.add_column("URL", style="blue")
    table.add_column("Created", style="dim")

    for upload in uploads:
        table.add_row(
            upload["name"],
            upload["slug"],
            humanize.naturalsize(upload["size"]),
            upload["mimetype"],
            f"[link={upload['url']}]{upload['url']}[/link]",
            _localtime(
                datetime.fromisoformat(upload["created_at"]), obj["datetime_format"]
            ),
        )

    _err.print(table)


@cli.command("delete")
@click.argument("slugs", nargs=-1, required=True)
@click.pass_obj
def delete_cmd(obj: dict, slugs: tuple[str, ...]) -> None:
    if "*" in slugs and not Confirm.ask(
        "Delete all files?", console=_err, default=False
    ):
        raise click.Abort

    try:
        count = _delete_uploads(obj["session"], list(slugs))
    except RehomeError as exc:
        _out.print(str(exc))
        sys.exit(1)

    noun = "file" if count == 1 else "files"
    _err.print(f"Deleted {count} {noun}.")


if __name__ == "__main__":
    cli()
