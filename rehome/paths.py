from pathlib import Path

from rehome import config

BASE = Path(__file__).parent.absolute()

# Needs to be loaded outside the flask extension as these are needed before we have an app context.
__config = config.dynaconf

TEMPLATES = Path(__config.get("paths.templates", BASE / "templates"))
RESOURCES = Path(__config.get("paths.resources", BASE / "resources"))
DATA = Path(__config.get("paths.data", BASE.parent / "data"))
STATIC = Path(__config.get("paths.static", BASE / "static"))
UPLOADS = Path(__config.get("paths.uploads", DATA / "uploads"))
MIGRATIONS = Path(__config.get("paths.migrations", BASE / "db/migrations"))
NODE_MODULES = Path(__config.get("paths.node_modules", BASE.parent / "node_modules"))
