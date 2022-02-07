from dynaconf import Dynaconf, FlaskDynaconf
from flask_assets import Environment
from flask_sqlalchemy import SQLAlchemy

dynaconf = FlaskDynaconf(
    dynaconf_instance=Dynaconf(
        environments=False,
        envvar_prefix="FLASK",
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
