from pathlib import Path

# Needs to be loaded outside the flask extension as these are needed before we have an app context.
from rehome.config import dynaconf as _config

BASE = Path(__file__).parent.absolute()
TEMPLATES = Path(_config.get("paths.templates", BASE / "templates"))
RESOURCES = Path(_config.get("paths.resources", BASE / "resources"))
STATIC = Path(_config.get("paths.static", BASE / "static"))
INSTANCE = Path(_config.get("paths.instance", BASE.parent / "instance"))
DATA = Path(_config.get("paths.data", INSTANCE))
UPLOADS = Path(_config.get("paths.uploads", DATA / "uploads"))


def ensure_dirs():
    for path in [INSTANCE, DATA, UPLOADS]:
        path.mkdir(parents=True, exist_ok=True)
