from datetime import datetime
from pathlib import Path

from flask import current_app as app
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    event,
    func,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from rehome import db, paths
from rehome.util import random_string


def generate_upload_name(suffix: str | None) -> Path:
    name_length = app.config.get("uploads.name_length", 3)

    while True:
        name = Path(random_string(name_length, extra_chars="-_~")).with_suffix(suffix)
        if Upload.query.filter_by(name=name).first() is None:
            return name
        name_length += 1


class Upload(db.Model):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Path] = mapped_column(nullable=False, unique=True, index=True)
    original_name: Mapped[Path] = mapped_column(nullable=False, index=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str | None] = mapped_column(String(128))
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __init__(
        self,
        name: Path,
        original_name: Path,
        size: int,
        mimetype: str,
        file_hash: str,
    ):
        self.name = name
        self.original_name = original_name
        self.size = size
        self.mimetype = mimetype
        self.file_hash = file_hash

    @hybrid_property
    def path(self) -> Path:
        return paths.UPLOADS / self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "original_name": self.original_name,
            "size": self.size,
            "mimetype": self.mimetype,
            "hash": self.file_hash,
            "created_at": self.created_at,
        }


def after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", after_delete)
