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


class Upload(db.Model):
    __tablename__ = "uploads"

    name: Mapped[Path] = mapped_column(primary_key=True)
    original_name: Mapped[Path] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str] = mapped_column(String(128), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __init__(
        self,
        original_name: Path,
        size: int,
        mimetype: str,
        file_hash: str,
    ):
        self.original_name = original_name
        self.name = self.__generate_name()
        self.size = size
        self.mimetype = mimetype
        self.file_hash = file_hash

    def __generate_name(self) -> Path:
        name_length = app.config.get("uploads.name_length", 5)

        while True:
            name = Path(random_string(name_length, extra_chars="-_~")).with_suffix(
                self.original_name.suffix
            )
            if Upload.query.filter_by(name=name).first() is None:
                return name
            name_length += 1

    @hybrid_property
    def path(self) -> Path:
        return paths.UPLOADS / self.name


def __after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", __after_delete)
