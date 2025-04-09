import os
from datetime import datetime
from pathlib import Path

from flask import current_app as app
from flask import url_for
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    event,
    func,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.datastructures import FileStorage

from rehome import db, paths
from rehome.util import random_string


class UploadSaveError(Exception):
    pass


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
            name = Path(random_string(name_length)).with_suffix(
                self.original_name.suffix
            )
            upload_query = db.select(Upload).filter_by(name=name)
            if db.session.execute(upload_query).scalar() is None:
                return name
            name_length += 1

    def save(self, file: FileStorage):
        db.session.add(self)
        try:
            self.path.parent.mkdir(exist_ok=True, parents=True)
            file.seek(0, os.SEEK_SET)
            file.save(
                self.path,
                buffer_size=app.config.get("uploads.save_chunk_size", 1024 * 128),
            )  # Using 128KB chunks to match ZFS' default recordsize.
            db.session.commit()
        except (OSError, IntegrityError) as error:
            db.session.rollback()
            self.path.unlink(missing_ok=True)
            app.logger.exception(error)
            raise UploadSaveError from error

    def update(self, original_name: Path, mimetype: str | None):
        self.original_name = original_name
        if mimetype:
            self.mimetype = mimetype
        db.session.commit()

    @hybrid_property
    def path(self) -> Path:
        return paths.UPLOADS / self.name

    @hybrid_property
    def url(self) -> str:
        return url_for("uploads.view", name=self.name, _external=True)


def __after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", __after_delete)
