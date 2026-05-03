import click
import humanize
from flask.cli import AppGroup
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from rehome import db
from rehome.models.upload import Upload
from rehome.util import localtime

upload_cli = AppGroup("upload", help="Manage uploaded files.")

_SORT_COLUMNS = {
    "created": Upload.created_at,
    "size": Upload.size,
    "mimetype": Upload.mimetype,
}


@upload_cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(list(_SORT_COLUMNS)),
    default="created",
    show_default=True,
    help="Sort by field.",
)
def upload_list(sort: str):
    uploads = db.session.scalars(select(Upload).order_by(_SORT_COLUMNS[sort])).all()
    if not uploads:
        click.echo(click.style("No files.", fg="yellow"))
        return
    table = Table(show_edge=False, pad_edge=False)
    table.add_column("Name", style="bold")
    table.add_column("Slug")
    table.add_column("Size")
    table.add_column("Type")
    table.add_column("Created")
    for upload in uploads:
        table.add_row(
            str(upload.name),
            str(upload.slug),
            humanize.naturalsize(upload.size),
            upload.mimetype,
            localtime(upload.created_at),
        )
    Console().print(table)


class _UploadNotFoundError(click.ClickException):
    def __init__(self, slug: str) -> None:
        super().__init__(f"File '{slug}' not found.")


@upload_cli.command("delete")
@click.argument("slugs", nargs=-1, required=True)
def upload_delete(slugs: tuple[str, ...]):
    uploads = []
    for slug in slugs:
        upload = db.session.get(Upload, slug)
        if not upload:
            raise _UploadNotFoundError(slug)
        uploads.append(upload)
    noun = "file" if len(uploads) == 1 else "files"
    names_str = ", ".join(f"'{u.slug}'" for u in uploads)
    click.confirm(f"Delete {noun} {names_str}?", abort=True)
    for upload in uploads:
        upload.delete()
    click.echo(click.style(f"Deleted {len(uploads)} {noun}.", fg="green"))
