from importlib.util import find_spec

from dynaconf import FlaskDynaconf
from flask_assets import Environment
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from rehome import config

dynaconf = FlaskDynaconf(dynaconf_instance=config.dynaconf)
assets = Environment()
db = SQLAlchemy()
migrate = Migrate()
debugbar = None

if find_spec("flask_debugtoolbar"):
    from flask_debugtoolbar import DebugToolbarExtension

    debugbar = DebugToolbarExtension()
