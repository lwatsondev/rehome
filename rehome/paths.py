from pathlib import Path

from dynaconf import Dynaconf

_env_paths = Dynaconf(envvar_prefix="PATHS")

BASE = Path(__file__).parent.absolute()
ASSETS = Path(_env_paths.get("ASSETS", BASE / "assets"))
TEMPLATES = Path(_env_paths.get("TEMPLATES", BASE / "templates"))
RESOURCES = Path(_env_paths.get("RESOURCES", BASE / "resources"))
STATIC = Path(_env_paths.get("STATIC", BASE.parent / "static"))
DATA = Path(_env_paths.get("DATA", BASE.parent / "data"))
NODE_MODULES = Path(_env_paths.get("NODE_MODULES", BASE.parent / "node_modules"))
