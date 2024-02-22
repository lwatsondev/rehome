from dynaconf import FlaskDynaconf
from flask_assets import Environment
from flask_sqlalchemy import SQLAlchemy

from rehome import config

dynaconf = FlaskDynaconf(dynaconf_instance=config.dynaconf)
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
