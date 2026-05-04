import click
import humanize
from flask.cli import AppGroup
from rich import box
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from sqlalchemy import select

from rehome import db
from rehome.models.upload import SORT_COLUMNS, Upload

_out = Console()

upload_cli = AppGroup("upload", help="Manage uploaded files.")


@upload_cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(list(SORT_COLUMNS)),
    default="created",
    show_default=True,
    help="Sort by field.",
)
@click.option("--desc", is_flag=True, default=False, help="Sort descending.")
def upload_list(sort: str, desc: bool):
    col = SORT_COLUMNS[sort]
    col = col.desc() if desc else col.asc()

    uploads = db.session.scalars(select(Upload).order_by(col)).all()
    if not uploads:
        _out.print("[yellow]No files.[/yellow]")
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
    table.add_column("Created", style="dim")

    for upload in uploads:
        table.add_row(
            str(upload.name),
            str(upload.slug),
            humanize.naturalsize(upload.size),
            upload.mimetype,
            upload.created_at.isoformat(),
        )
    _out.print(table)


class _UploadNotFoundError(click.ClickException):
    def __init__(self, slug: str) -> None:
        super().__init__(f"File '{slug}' not found.")

    def show(self, file=None) -> None:  # noqa: ARG002
        _out.print(f"[red]Error:[/red] {self.format_message()}")


@upload_cli.command("delete")
@click.argument("slugs", nargs=-1, required=True)
def upload_delete(slugs: tuple[str, ...]):
    if "*" in slugs:
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
        return

    uploads = []
    for slug in slugs:
        upload = db.session.get(Upload, slug)
        if not upload:
            raise _UploadNotFoundError(slug)
        uploads.append(upload)

    noun = "file" if len(uploads) == 1 else "files"
    names_str = ", ".join(f"'{upload.slug}'" for upload in uploads)

    if not Confirm.ask(f"Delete {noun} {names_str}?", default=False):
        raise click.Abort

    for upload in uploads:
        upload.delete()

    _out.print(f"[green]Deleted {len(uploads)} {noun}.[/green]")
