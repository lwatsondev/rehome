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


def generate_upload_name() -> str:
    name_length = app.config.get("uploads.name_length", 3)

    while True:
        name = __random_string(name_length, extra_chars="-_~")
        if Upload.query.filter_by(name=name).first() is None:
            return name
        name_length += 1


class Upload(db.Model):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mimetype: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    @property
    def path(self) -> Path:
        return paths.UPLOADS / self.name

    def to_dict(self) -> dict:
        return {
            "original_name": self.original_name,
            "size": self.size,
            "mimetype": self.mimetype,
            "name": self.name,
            "hash": self.file_hash,
            "created_at": self.created_at,
        }


def after_delete(mapper, connection, target: Upload):  # noqa: ARG001
    target.path.unlink(missing_ok=True)


event.listen(Upload, "after_delete", after_delete)
