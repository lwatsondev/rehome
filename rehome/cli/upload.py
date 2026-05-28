import click
import humanize
from flask.cli import AppGroup
from rich import box
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from sqlalchemy import select

from rehome.extensions import db
from rehome.models.upload import SORT_COLUMNS, Upload, build_filter_clauses

_out = Console()

upload_cli = AppGroup("upload", help="Manage uploaded files.")

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


def _add_filter_options(func):
    for option in reversed(_FILTER_OPTIONS):
        func = option(func)
    return func


def _print_uploads_table(uploads):
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
    table.add_column("Created", style="dim")
    table.add_column("Expires", style="dim")

    for upload in uploads:
        if upload.expires_at:
            expires_str = upload.expires_at.isoformat()
            expires_cell = (
                f"[red not dim]{expires_str}[/red not dim]"
                if upload.is_expired
                else expires_str
            )
        else:
            expires_cell = ""

        table.add_row(
            str(upload.name),
            str(upload.slug),
            humanize.naturalsize(upload.size),
            upload.mimetype,
            upload.created_at.isoformat(),
            expires_cell,
        )
    _out.print(table)


@upload_cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(list(SORT_COLUMNS)),
    default="created",
    show_default=True,
    help="Sort by field.",
)
@click.option("--desc", is_flag=True, default=False, help="Sort descending.")
@_add_filter_options
def upload_list(
    sort: str,
    desc: bool,
    name_filter: str | None,
    slug_filter: str | None,
    mimetype_filter: str | None,
):
    col = SORT_COLUMNS[sort]
    col = col.desc() if desc else col.asc()

    filter_clauses = build_filter_clauses(
        name=name_filter, slug=slug_filter, mimetype=mimetype_filter
    )

    uploads = db.session.scalars(
        select(Upload).where(*filter_clauses).order_by(col)
    ).all()

    if not uploads:
        _out.print("[yellow]No files.[/yellow]")
        return

    _print_uploads_table(uploads)


class _NoTargetError(click.UsageError):
    def __init__(self):
        super().__init__("Provide --all or filter options.")


def _wildcard_delete():
    uploads = db.session.scalars(select(Upload)).all()

    if not uploads:
        _out.print("[yellow]No files.[/yellow]")
        return

    noun = "file" if len(uploads) == 1 else "files"
    if not Confirm.ask(f"Delete all {len(uploads)} {noun}?", default=False):
        raise click.Abort

    for upload in uploads:
        upload.delete()

    _out.print(f"[green]Deleted {len(uploads)} {noun}.[/green]")


def _filter_delete(
    name_filter: str | None, slug_filter: str | None, mimetype_filter: str | None
):
    filter_clauses = build_filter_clauses(
        name=name_filter, slug=slug_filter, mimetype=mimetype_filter
    )

    uploads = db.session.scalars(select(Upload).where(*filter_clauses)).all()
    if not uploads:
        _out.print("[yellow]No files.[/yellow]")
        return

    _print_uploads_table(uploads)

    noun = "file" if len(uploads) == 1 else "files"
    if not Confirm.ask(f"Delete {len(uploads)} {noun}?", default=False):
        raise click.Abort

    for upload in uploads:
        upload.delete()

    _out.print(f"[green]Deleted {len(uploads)} {noun}.[/green]")


@upload_cli.command("delete")
@click.option(
    "--all", "delete_all", is_flag=True, default=False, help="Delete all files."
)
@_add_filter_options
def upload_delete(
    delete_all: bool,
    name_filter: str | None,
    slug_filter: str | None,
    mimetype_filter: str | None,
):
    has_filters = any([name_filter, slug_filter, mimetype_filter])

    if not delete_all and not has_filters:
        raise _NoTargetError

    if delete_all:
        _wildcard_delete()
    else:
        _filter_delete(name_filter, slug_filter, mimetype_filter)
