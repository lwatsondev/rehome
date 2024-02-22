import os

from dynaconf import Dynaconf

dynaconf = Dynaconf(
    environments=False,
    envvar_prefix="CFG",
    root_path=os.getenv("ROOT_PATH_FOR_DYNACONF", None),
    settings_files=[
        "*.toml",
        "*.yml",
        "*.yaml",
    ],
)
