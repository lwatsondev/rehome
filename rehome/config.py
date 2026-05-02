import os
from pathlib import Path

from dynaconf import Dynaconf

_BASE_DIR = Path(__file__).parent
_CONFIG_DIR = os.getenv("ROOT_PATH_FOR_DYNACONF", _BASE_DIR / "resources" / "config")

dynaconf = Dynaconf(
    environments=False,
    envvar_prefix="CFG",
    root_path=_CONFIG_DIR,
    settings_files=[str(_BASE_DIR / "resources" / "config" / "default.toml"), "*.toml"],
)
