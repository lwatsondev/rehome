import hashlib
import os
import typing
from datetime import datetime  # noqa: TC003
from pathlib import Path

import magic
from flask import current_app as app
from flask import url_for
from sqlalchemy import (
    BigInteger,
    DateTime,
    Text,
    event,
    exists,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from rehome import db, paths
from rehome.models import BaseModel
from rehome.util import random_string

if typing.TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage


class UploadSaveError(Exception):
    pass


class Upload(BaseModel):
    __tablename__ = "uploads"

    name: Mapped[Path] = mapped_column(primary_key=True, nullable=False)
    original_name: Mapped[Path] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __init__(
        self,
        original_name: Path,
        size: int,
        mimetype: str,
        file_hash: str,
    ):
        super().__init__()
        self.name = _generate_name(_get_file_extension(original_name))
        self.original_name = original_name
        self.size = size
        self.mimetype = mimetype
        self.file_hash = file_hash

    @classmethod
    def from_file(cls, file: FileStorage) -> typing.Self:
        file_original_name = Path(file.filename)
        file.seek(0, os.SEEK_SET)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0, os.SEEK_SET)
        file_mimetype = magic.from_buffer(file.read(4096), mime=True)
        file.seek(0, os.SEEK_SET)
        file_hash = hashlib.file_digest(file.stream, hashlib.sha256).hexdigest()
        file.seek(0, os.SEEK_SET)

        existing_upload_query = select(cls).filter_by(file_hash=file_hash)
        existing_upload = db.session.scalar(existing_upload_query)
        if existing_upload:
            return existing_upload

        return cls(
            file_original_name,
            file_size,
            file_mimetype,
            file_hash,
        )

    def save(self, file: FileStorage):
        if self.path.exists():
            self.update(original_name=file.filename)
            return

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
            raise UploadSaveError from error

    @hybrid_property
    def path(self) -> Path:
        return paths.UPLOADS / self.name

    @hybrid_property
    def url(self) -> str:
        return url_for("uploads.view", name=self.name, _external=True)


def _get_file_extension(path: Path) -> str:
    """Extract file extension, preserving multipart extensions like .tar.gz."""
    return "".join(path.suffixes)


def _generate_name(suffix: str) -> Path:
    name_length = app.config.get("uploads.name_length", 5)

    while True:
        # Construct manually to preserve multipart extensions like .tar.gz.
        random_part = random_string(name_length)
        name = Path(f"{random_part}{suffix}")
        check_exists_query = select(exists().where(Upload.name == name))
        if not db.session.scalar(check_exists_query):
            return name
        name_length += 1


def __after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", __after_delete)
