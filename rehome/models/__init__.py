import pathlib

from sqlalchemy.orm import DeclarativeBase, registry

from rehome.models._type_decorators import PathLike


class BaseModel(DeclarativeBase):
    """Base class used for declarative class definitions."""

    registry = registry(
        type_annotation_map={
            pathlib.Path: PathLike(pathlib.Path),
        }
    )
