import secrets
import typing
from datetime import UTC, datetime

from sqlalchemy import DateTime, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from rehome.extensions import db
from rehome.models import BaseModel


class AuthToken(BaseModel):
    __tablename__ = "auth_tokens"

    name: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @classmethod
    def generate(cls, name: str) -> typing.Self:
        return cls(name=name, token=secrets.token_urlsafe(32))

    @classmethod
    def verify(cls, token: str) -> bool:
        if not token:
            return False

        auth_token = db.session.scalar(select(cls).where(cls.token == token))
        if auth_token is None:
            return False

        auth_token.last_used_at = datetime.now(UTC)
        db.session.commit()
        return True
