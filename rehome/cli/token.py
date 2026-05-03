import click
from flask.cli import AppGroup
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from rehome import db
from rehome.models.auth_token import AuthToken


class _TokenExistsError(click.ClickException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Token '{name}' already exists.")


class _TokenNotFoundError(click.ClickException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Token '{name}' not found.")


token_cli = AppGroup("token", help="Manage auth tokens.")


@token_cli.command("create")
@click.argument("name")
def token_create(name: str):
    if db.session.get(AuthToken, name):
        raise _TokenExistsError(name)

    plaintext, token = AuthToken.generate(name)
    db.session.add(token)
    db.session.commit()

    click.echo(plaintext)


@token_cli.command("list")
def token_list():
    tokens = db.session.scalars(select(AuthToken).order_by(AuthToken.created_at)).all()
    if not tokens:
        click.echo(click.style("No tokens.", fg="yellow"))
        return

    table = Table(show_edge=False, pad_edge=False)
    table.add_column("Name", style="bold")
    table.add_column("Created")
    table.add_column("Last Used")
    for token in tokens:
        last_used = (
            token.last_used_at.isoformat()
            if token.last_used_at
            else "[yellow]never[/yellow]"
        )
        table.add_row(token.name, token.created_at, last_used)

    Console().print(table)


@token_cli.command("delete")
@click.argument("name")
def token_delete(name: str):
    token = db.session.get(AuthToken, name)
    if not token:
        raise _TokenNotFoundError(name)

    token.delete()
    click.echo(click.style(f"Deleted token '{name}'.", fg="green"))
