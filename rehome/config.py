import os
from pathlib import Path

from dynaconf import Dynaconf

_base_dir = Path(__file__).parent
_config_dir = os.getenv("ROOT_PATH_FOR_DYNACONF", _base_dir / "resources" / "config")

dynaconf = Dynaconf(
    environments=False,
    envvar_prefix="CFG",
    root_path=_config_dir,
    settings_files=[str(_base_dir / "resources" / "config" / "default.toml"), "*.toml"],
)
