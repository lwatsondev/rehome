import secrets
import string
from datetime import datetime
from pathlib import Path

from flask import current_app as app
from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from rehome import db, paths


def __random_string(length: int, extra_chars: str = "") -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits + extra_chars)
        for _ in range(length)
    )


def generate_upload_url() -> str:
    url_length = app.config.get("uploads.min_url_length", 3)

    while True:
        url = __random_string(url_length, extra_chars="-_~")
        if Upload.query.filter_by(url=url).first() is None:
            return url
        url_length += 1


class Upload(db.Model):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    @property
    def path(self) -> Path:
        return paths.UPLOADS / self.url

    @property
    def response_mimetype(self) -> str:
        ext = self.path.suffix
        if (
            ext and ext.lstrip(".") in app.config.get("uploads.display_inline")
        ) or self.mimetype.startswith("text/"):
            return "text/plain"

        return self.mimetype

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size": self.size,
            "mimetype": self.mimetype,
            "url": self.url,
            "hash": self.file_hash,
            "created_at": self.created_at,
        }


def after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", after_delete)
