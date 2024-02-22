from dynaconf import Dynaconf

dynaconf = Dynaconf(
    environments=False,
    envvar_prefix="CFG",
    settings_files=[
        "*.toml",
        "*.yml",
        "*.yaml",
    ],
)
