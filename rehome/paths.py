from distutils.dir_util import copy_tree
from pathlib import Path

from dynaconf import Dynaconf

BASE = Path(__file__).parent.absolute()
ASSETS = BASE / "assets"
TEMPLATES = BASE / "templates"
RESOURCES = BASE / "resources"

_paths_from_env = Dynaconf(envvar_prefix="PATHS")
NODE_MODULES = Path(_paths_from_env.get("NODE_MODULES", BASE.parent / "node_modules"))
STATIC = Path(_paths_from_env.get("STATIC", BASE.parent / "static"))
DATA = Path(_paths_from_env.get("DATA", BASE.parent / "data"))

for path in [STATIC, DATA]:
    path.mkdir(exist_ok=True)

copy_tree(str(ASSETS / "img"), str(STATIC / "img"), update=1)
