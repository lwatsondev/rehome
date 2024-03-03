import os

VERSION: str = "[version unknown]"
_META_VERSION: str | None = os.getenv("META_VERSION")
_META_HASH: str | None = os.getenv("META_VERSION_HASH")

if _META_VERSION and _META_HASH:
    VERSION = f"{_META_VERSION}-{_META_HASH[:8]}"

SOURCE: str = os.getenv("META_SOURCE") or "https://github.com/TheReverend403/rehome"
