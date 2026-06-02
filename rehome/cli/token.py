# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

import click
from flask.cli import AppGroup
from rich import box
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from rehome.extensions import db
from rehome.models.auth_token import AuthToken

_out = Console()


class _TokenExistsError(click.ClickException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Token '{name}' already exists.")

    def show(self, file=None) -> None:  # noqa: ARG002
        _out.print(f"[red]Error:[/red] {self.format_message()}")


class _TokenNotFoundError(click.ClickException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Token '{name}' not found.")

    def show(self, file=None) -> None:  # noqa: ARG002
        _out.print(f"[red]Error:[/red] {self.format_message()}")


token_cli = AppGroup("token", help="Manage auth tokens.")


@token_cli.command("create")
@click.argument("name")
def token_create(name: str):
    if db.session.get(AuthToken, name):
        raise _TokenExistsError(name)

    token = AuthToken.generate(name)
    db.session.add(token)
    db.session.commit()

    _out.print(token.token)


@token_cli.command("list")
def token_list():
    tokens = db.session.scalars(select(AuthToken).order_by(AuthToken.created_at)).all()

    if not tokens:
        _out.print("[yellow]No tokens.[/yellow]")
        return

    table = Table(
        box=box.ASCII_DOUBLE_HEAD,
        header_style="bold green",
    )
    table.add_column("Name", style="cyan")
    table.add_column("Created", style="dim")
    table.add_column("Last Used", style="dim")
    for token in tokens:
        last_used = (
            token.last_used_at.isoformat()
            if token.last_used_at
            else "[yellow]never[/yellow]"
        )
        table.add_row(token.name, token.created_at.isoformat(), last_used)

    _out.print(table)


@token_cli.command("delete")
@click.argument("name")
def token_delete(name: str):
    token = db.session.get(AuthToken, name)
    if not token:
        raise _TokenNotFoundError(name)

    token.delete()
    _out.print(f"[green]Deleted token '{name}'.[/green]")
