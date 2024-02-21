from dynaconf import Dynaconf, FlaskDynaconf
from flask_assets import Environment
from flask_sqlalchemy import SQLAlchemy

from rehome import paths

dynaconf = FlaskDynaconf(
    dynaconf_instance=Dynaconf(
        environments=False,
        envvar_prefix="CFG",
        root_path=paths.CONFIG_ROOT,
        settings_files=[
            "*.toml",
            "*.yml",
            "*.yaml",
        ],
    ),
)
assets = Environment()
db = SQLAlchemy()
debugbar = None

try:
    import flask_debugtoolbar  # noqa: F401
except ImportError:
    pass
else:
    from flask_debugtoolbar import DebugToolbarExtension

    debugbar = DebugToolbarExtension()
