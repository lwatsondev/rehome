import secrets
import string
from datetime import UTC, datetime


def localtime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def random_string(length: int, extra_chars: str = "") -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits + extra_chars)
        for _ in range(length)
    )
