import click
from flask.cli import AppGroup
from sqlalchemy import select

from rehome import db
from rehome.models.auth_token import AuthToken
from rehome.util import localtime


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
    for index, token in enumerate(tokens):
        if index:
            click.echo()
        last_used = (
            localtime(token.last_used_at)
            if token.last_used_at
            else click.style("never", fg="yellow")
        )
        click.echo(click.style(token.name, bold=True))
        click.echo(
            f"  {click.style('created', dim=True)}   {localtime(token.created_at)}"
        )
        click.echo(f"  {click.style('last used', dim=True)} {last_used}")


@token_cli.command("delete")
@click.argument("name")
def token_delete(name: str):
    token = db.session.get(AuthToken, name)
    if not token:
        raise _TokenNotFoundError(name)
    token.delete()
    db.session.commit()
    click.echo(click.style(f"Deleted token '{name}'.", fg="green"))
