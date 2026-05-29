import hashlib
import shutil
import typing
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import magic
from flask import current_app as app
from flask import url_for
from sqlalchemy import (
    BigInteger,
    DateTime,
    Text,
    and_,
    cast,
    event,
    exists,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from rehome import paths
from rehome.extensions import db
from rehome.models import BaseModel
from rehome.util import random_string


class UploadSaveError(Exception):
    pass


class Upload(BaseModel):
    __tablename__ = "uploads"

    slug: Mapped[Path] = mapped_column(primary_key=True, nullable=False)
    name: Mapped[Path] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __init__(  # noqa: PLR0913
        self,
        slug: Path,
        name: Path,
        size: int,
        mimetype: str,
        file_hash: str,
        expires_at: datetime | None = None,
    ):
        super().__init__()
        self.slug = slug
        self.name = name
        self.size = size
        self.mimetype = mimetype
        self.file_hash = file_hash
        self.expires_at = expires_at

    @classmethod
    def from_file(cls, file: BinaryIO, name: str | Path) -> typing.Self:
        file_name = Path(name)
        file.seek(0)
        hasher = hashlib.sha256()
        file_size = 0
        header = b""

        # Single pass rather than previous behaviour of multiple seeks.
        # Collects hash, size, and mime header together.
        while chunk := file.read(1024 * 128):
            if not header:
                header = chunk[:4096]
            hasher.update(chunk)
            file_size += len(chunk)

        file_mimetype = magic.from_buffer(header, mime=True)
        if file_name.suffix.lower() in {".md", ".markdown"}:
            file_mimetype = "text/markdown"

        file_hash = hasher.hexdigest()

        existing_upload_query = select(cls).filter_by(file_hash=file_hash)
        existing_upload = db.session.scalar(existing_upload_query)
        if existing_upload:
            existing_upload.update(name=file_name, commit=False)
            return existing_upload

        return cls(
            _generate_slug(file_name),
            file_name,
            file_size,
            file_mimetype,
            file_hash,
        )

    def save(self, file: BinaryIO):
        if self.path.exists():
            return

        db.session.add(self)
        try:
            self.path.parent.mkdir(exist_ok=True, parents=True)
            file.seek(0)
            with self.path.open("wb") as dest:
                shutil.copyfileobj(
                    file,
                    dest,
                    length=app.config.get("uploads.save_chunk_size", 1024 * 128),
                )
            db.session.commit()
        except (OSError, IntegrityError) as error:
            db.session.rollback()
            self.path.unlink(missing_ok=True)
            raise UploadSaveError from error

    @hybrid_property
    def path(self) -> Path:
        return paths.UPLOADS / self.slug

    @hybrid_property
    def url(self) -> str:
        return url_for("uploads.view", slug=self.slug, _external=True)

    @property
    def expires_at_utc(self) -> datetime | None:
        if self.expires_at is None:
            return None

        if self.expires_at.tzinfo is None:
            return self.expires_at.replace(tzinfo=UTC)

        return self.expires_at

    @hybrid_property
    def is_expired(self) -> bool:
        if self.expires_at_utc is None:
            return False

        return datetime.now(UTC) > self.expires_at_utc

    @is_expired.expression
    @classmethod
    def is_expired(cls):
        now = datetime.now(UTC)
        return and_(cls.expires_at.isnot(None), cls.expires_at < now)


ORDER_ASC = "asc"
ORDER_DESC = "desc"

SORT_COLUMNS = {
    "created": Upload.created_at,
    "expires": Upload.expires_at,
    "size": Upload.size,
    "mimetype": Upload.mimetype,
}


def build_filter_clauses(
    name: str | None = None,
    slug: str | None = None,
    mimetype: str | None = None,
    expired: bool | None = None,
) -> list:
    clauses = []

    if name is not None:
        clauses.append(cast(Upload.name, Text).op("GLOB")(name))

    if slug is not None:
        clauses.append(cast(Upload.slug, Text).op("GLOB")(slug))

    if mimetype is not None:
        clauses.append(Upload.mimetype.op("GLOB")(mimetype))

    if expired is True:
        clauses.append(Upload.is_expired)

    return clauses


def _generate_slug(file_name: Path) -> Path:
    slug_length = app.config.get("uploads.slug_length", 5)
    suffix = "".join(file_name.suffixes)

    while True:
        random_part = random_string(slug_length)
        slug = Path(random_part).with_suffix(suffix)
        check_exists_query = select(exists().where(Upload.slug == slug))
        if not db.session.scalar(check_exists_query):
            return slug
        slug_length += 1


@event.listens_for(Upload, "after_delete")
def _after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)
