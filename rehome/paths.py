import os
from pathlib import Path

from dynaconf import Dynaconf

BASE = Path(__file__).parent.absolute()
CONFIG_ROOT = os.getenv("ROOT_PATH_FOR_DYNACONF", BASE.parent / "config")

# Needs to be loaded outside the flask extension as these are needed before we have an app context.
__config = Dynaconf(
    envvar_prefix="CFG",
)

ASSETS = Path(__config.get("paths.assets", BASE / "assets"))
TEMPLATES = Path(__config.get("paths.templates", BASE / "templates"))
RESOURCES = Path(__config.get("paths.resources", BASE / "resources"))
STATIC = Path(__config.get("paths.static", BASE.parent / "static"))
DATA = Path(__config.get("paths.data", BASE.parent / "data"))
NODE_MODULES = Path(__config.get("paths.node_modules", BASE.parent / "node_modules"))
