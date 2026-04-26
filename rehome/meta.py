from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as pkg_metadata

try:
    _meta = pkg_metadata("rehome")
    FULL_VERSION: str = _meta["Version"]
    SOURCE: str = dict(
        u.split(", ", 1) for u in (_meta.get_all("Project-URL") or [])
    ).get("source", "")
except PackageNotFoundError:
    FULL_VERSION = "[version unknown]"
    SOURCE = ""
