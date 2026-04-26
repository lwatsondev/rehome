import os

FULL_VERSION: str = "[version unknown]"
VERSION: str | None = os.getenv("META_VERSION")
COMMIT: str | None = os.getenv("META_COMMIT")
SOURCE: str = os.getenv("META_SOURCE") or "https://github.com/lwatsondev/rehome"

if VERSION:
    FULL_VERSION = f"{VERSION}"

if COMMIT:
    FULL_VERSION += f"-{COMMIT[:8]}"
