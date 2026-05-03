import click
import humanize
from flask.cli import AppGroup
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
    for index, upload in enumerate(uploads):
        if index:
            click.echo()
        click.echo(click.style(str(upload.name), bold=True))
        click.echo(
            f"  {click.style('created', dim=True)}  {localtime(upload.created_at)}"
        )
        click.echo(
            f"  {click.style('size', dim=True)}     {humanize.naturalsize(upload.size)}"
        )
        click.echo(f"  {click.style('type', dim=True)}     {upload.mimetype}")


class _UploadNotFoundError(click.ClickException):
    def __init__(self, name: str) -> None:
        super().__init__(f"File '{name}' not found.")


@upload_cli.command("delete")
@click.argument("names", nargs=-1, required=True)
def upload_delete(names: tuple[str, ...]):
    uploads = []
    for name in names:
        upload = db.session.get(Upload, name)
        if not upload:
            raise _UploadNotFoundError(name)
        uploads.append(upload)
    noun = "file" if len(uploads) == 1 else "files"
    names_str = ", ".join(f"'{u.name}'" for u in uploads)
    click.confirm(f"Delete {noun} {names_str}?", abort=True)
    for upload in uploads:
        upload.delete()
    click.echo(click.style(f"Deleted {len(uploads)} {noun}.", fg="green"))
