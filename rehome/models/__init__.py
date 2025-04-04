import os
import pathlib
from collections.abc import Callable

from sqlalchemy import Dialect, Text
from sqlalchemy.orm import DeclarativeBase, registry
from sqlalchemy.types import TypeDecorator


class PathLike(TypeDecorator):
    """
    Allows mapping a `pathlib.Path` object to an `sqlalchemy.Text`.
    Source: https://github.com/sqlalchemy/sqlalchemy/discussions/9027#discussioncomment-4510017
    """

    impl = Text
    cache_ok = True

    def __init__(self, factory: Callable[[str], os.PathLike]):
        super().__init__()
        self.factory = factory

    def process_bind_param(
        self,
        value: os.PathLike | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> str:
        """Convert an `os.PathLike` value to a string for the database."""
        if value:
            value = os.fspath(value)
        return value

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> os.PathLike | None:
        """Restore a string from the database to an `os.Pathlike`."""
        if value is not None:
            value = self.factory(value)
        return value


class BaseModel(DeclarativeBase):
    """Base class used for declarative class definitions."""

    registry = registry(
        type_annotation_map={
            pathlib.Path: PathLike(pathlib.Path),
        }
    )
