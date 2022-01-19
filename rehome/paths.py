from pathlib import Path

from dynaconf import Dynaconf

BASE = Path(__file__).parent.absolute()
ASSETS = BASE / "assets"
TEMPLATES = BASE / "templates"
RESOURCES = BASE / "resources"

_paths = Dynaconf(
    environments=False,
    envvar_prefix="PATHS",
)

NODE_MODULES = _paths.get("NODE_MODULES")
STATIC = _paths.get("STATIC")
DATA = _paths.get("DATA")
