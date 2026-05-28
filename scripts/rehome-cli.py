#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "click>=8.0",
#     "dateparser>=1.0",
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
import dateparser
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
_MIN_EXPIRY_SECONDS = 10 * 60
_FILTER_OPTIONS = [
    click.option(
        "--name", "name_filter", default=None, help="Filter by name (fnmatch pattern)."
    ),
    click.option(
        "--slug", "slug_filter", default=None, help="Filter by slug (fnmatch pattern)."
    ),
    click.option(
        "--mimetype",
        "mimetype_filter",
        default=None,
        help="Filter by mimetype (fnmatch pattern).",
    ),
]

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
            _err.print("[yellow]No auth token found in config.[/yellow]")
        else:
            _err.print("[yellow]No configuration found.[/yellow]")
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


def _upload(session: Session, file: Path, expires_in: int | None = None) -> str:
    with file.open("rb") as fd:
        fields = {"file": (file.name, fd)}

        if expires_in is not None:
            fields["expires_in"] = str(expires_in)

        encoder = MultipartEncoder(fields=fields)
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


def _list_uploads(
    session: Session,
    sort: str,
    desc: bool,
    filters: dict | None = None,
) -> list[dict]:
    params = {"sort": sort, "order": _ORDER_DESC if desc else _ORDER_ASC}

    if filters:
        params.update(filters)

    response = _make_request(session, HTTPMethod.GET, "/f/", params=params)
    _check_response(response)
    return response.json()


def _delete_uploads(session: Session, filters: dict | None = None) -> int:
    response = _make_request(session, HTTPMethod.DELETE, "/f/", params=filters)
    _check_response(response)
    return response.json()["deleted"]


def _localtime(dt: datetime, format_str: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone().strftime(format_str or _DEFAULT_DATETIME_FORMAT)


def _add_filter_options(func):
    for option in reversed(_FILTER_OPTIONS):
        func = option(func)

    return func


def _build_filters(
    name_filter: str | None,
    slug_filter: str | None,
    mimetype_filter: str | None,
) -> dict | None:
    filters = {
        key: value
        for key, value in {
            "name": name_filter,
            "slug": slug_filter,
            "mimetype": mimetype_filter,
        }.items()
        if value is not None
    }
    return filters or None


def _render_uploads_table(uploads: list[dict], datetime_format: str) -> None:
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
    table.add_column("Expires", style="dim")

    now = datetime.now(UTC)

    for upload in uploads:
        if upload.get("expires_at"):
            expires_dt = datetime.fromisoformat(upload["expires_at"])

            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=UTC)

            expires_str = _localtime(expires_dt, datetime_format)
            expires_cell = (
                f"[red not dim]{expires_str}[/red not dim]"
                if expires_dt <= now
                else expires_str
            )
        else:
            expires_cell = ""

        table.add_row(
            upload["name"],
            upload["slug"],
            humanize.naturalsize(upload["size"]),
            upload["mimetype"],
            f"[link={upload['url']}]{upload['url']}[/link]",
            _localtime(datetime.fromisoformat(upload["created_at"]), datetime_format),
            expires_cell,
        )

    _err.print(table)


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
@click.option(
    "--expires",
    default=None,
    help=f"Expiry time relative to now (e.g. 'in 1 hour', '2 days', '30 minutes'). Minimum is {humanize.naturaldelta(_MIN_EXPIRY_SECONDS)}.",
)
@click.pass_obj
def upload_cmd(obj: dict, file: Path, expires: str | None) -> None:
    expires_in = None

    if expires is not None:
        parsed = dateparser.parse(
            expires,
            settings={"RETURN_AS_TIMEZONE_AWARE": True, "PREFER_DATES_FROM": "future"},
        )

        if parsed is None:
            _err.print(f"[red]Could not parse expiry: {expires!r}[/red]")
            sys.exit(1)

        expires_in = int((parsed - datetime.now(UTC)).total_seconds())
        if expires_in < _MIN_EXPIRY_SECONDS:
            _err.print(
                f"[yellow]Expiry is less than the minimum of {humanize.naturaldelta(_MIN_EXPIRY_SECONDS)}, rounding up.[/yellow]"
            )
            expires_in = _MIN_EXPIRY_SECONDS

    try:
        url = _upload(obj["session"], file, expires_in=expires_in)
    except RehomeError as exc:
        _err.print(str(exc))
        sys.exit(1)

    _out.print(url)


@cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(["created", "expires", "size", "mimetype"]),
    default="created",
    show_default=True,
    help="Sort by field.",
)
@click.option("--desc", is_flag=True, default=False, help="Sort descending.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@_add_filter_options
@click.pass_obj
def list_cmd(obj: dict, sort: str, desc: bool, as_json: bool, **filter_kwargs) -> None:
    filters = _build_filters(
        filter_kwargs.get("name_filter"),
        filter_kwargs.get("slug_filter"),
        filter_kwargs.get("mimetype_filter"),
    )

    try:
        uploads = _list_uploads(obj["session"], sort, desc, filters=filters)
    except RehomeError as exc:
        _err.print(str(exc))
        sys.exit(1)

    if as_json:
        _out.print(json.dumps(uploads, indent=2), markup=False, highlight=False)
        return

    if not uploads:
        _err.print("No files.")
        return

    _render_uploads_table(uploads, obj["datetime_format"])


class _NoTargetError(click.UsageError):
    def __init__(self):
        super().__init__("Provide --all or filter options.")


def _delete_by_filter(
    session: Session, filters: dict, datetime_format: str
) -> int | None:
    try:
        uploads = _list_uploads(session, "created", False, filters=filters)
    except RehomeError as exc:
        _err.print(str(exc))
        sys.exit(1)

    if not uploads:
        _err.print("No files.")
        return None

    _render_uploads_table(uploads, datetime_format)

    noun = "file" if len(uploads) == 1 else "files"
    if not Confirm.ask(f"Delete {len(uploads)} {noun}?", console=_err, default=False):
        raise click.Abort

    try:
        return _delete_uploads(session, filters=filters)
    except RehomeError as exc:
        _err.print(str(exc))
        sys.exit(1)


@cli.command("delete")
@click.option(
    "--all", "delete_all", is_flag=True, default=False, help="Delete all files."
)
@_add_filter_options
@click.pass_obj
def delete_cmd(obj: dict, delete_all: bool, **filter_kwargs) -> None:
    filters = _build_filters(
        filter_kwargs.get("name_filter"),
        filter_kwargs.get("slug_filter"),
        filter_kwargs.get("mimetype_filter"),
    )

    if not delete_all and not filters:
        raise _NoTargetError

    if delete_all:
        if not Confirm.ask("Delete all files?", console=_err, default=False):
            raise click.Abort

        try:
            count = _delete_uploads(obj["session"], filters={"name": "*"})
        except RehomeError as exc:
            _err.print(str(exc))
            sys.exit(1)
    else:
        count = _delete_by_filter(obj["session"], filters, obj["datetime_format"])
        if count is None:
            return

    noun = "file" if count == 1 else "files"
    _err.print(f"Deleted {count} {noun}.")


if __name__ == "__main__":
    cli()
