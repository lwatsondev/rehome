import pathlib
import typing

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, registry
from werkzeug.exceptions import NotFound

from rehome.extensions import db
from rehome.models._type_decorators import PathLike


class BaseModel(DeclarativeBase):
    """Base class used for declarative class definitions."""

    registry = registry(
        type_annotation_map={
            pathlib.Path: PathLike(pathlib.Path),
        }
    )

    def update(self, commit=True, **kwargs):
        for field, value in kwargs.items():
            setattr(self, field, value)

        if commit:
            db.session.commit()

    def delete(self, commit=True):
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def one_or_404(cls, **kwargs) -> typing.Self:
        try:
            return db.session.scalars(select(cls).filter_by(**kwargs)).one()
        except NoResultFound as error:
            raise NotFound from error
