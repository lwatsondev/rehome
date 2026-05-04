import click
import humanize
from flask.cli import AppGroup
from rich import box
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from rehome import db
from rehome.models.upload import SORT_COLUMNS, Upload

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
        click.echo(click.style("No files.", fg="yellow"))
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
    table.add_column("URL")
    table.add_column("Created", style="dim")

    for upload in uploads:
        table.add_row(
            str(upload.name),
            str(upload.slug),
            humanize.naturalsize(upload.size),
            upload.mimetype,
            f"[blue link={upload.url}]{upload.url}[/blue link]",
            upload.created_at.isoformat(),
        )
    Console().print(table)


class _UploadNotFoundError(click.ClickException):
    def __init__(self, slug: str) -> None:
        super().__init__(f"File '{slug}' not found.")


@upload_cli.command("delete")
@click.argument("slugs", nargs=-1, required=True)
def upload_delete(slugs: tuple[str, ...]):
    if "*" in slugs:
        uploads = db.session.scalars(select(Upload)).all()

        if not uploads:
            click.echo(click.style("No files.", fg="yellow"))
            return

        noun = "file" if len(uploads) == 1 else "files"
        click.confirm(f"Delete all {len(uploads)} {noun}?", abort=True)
        for upload in uploads:
            upload.delete()

        click.echo(click.style(f"Deleted {len(uploads)} {noun}.", fg="green"))
        return

    uploads = []
    for slug in slugs:
        upload = db.session.get(Upload, slug)
        if not upload:
            raise _UploadNotFoundError(slug)
        uploads.append(upload)

    noun = "file" if len(uploads) == 1 else "files"
    names_str = ", ".join(f"'{upload.slug}'" for upload in uploads)

    click.confirm(f"Delete {noun} {names_str}?", abort=True)

    for upload in uploads:
        upload.delete()

    click.echo(click.style(f"Deleted {len(uploads)} {noun}.", fg="green"))
