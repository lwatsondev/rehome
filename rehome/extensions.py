from importlib.util import find_spec

from dynaconf import FlaskDynaconf
from flask_sqlalchemy import SQLAlchemy

from rehome.config import dynaconf
from rehome.models import BaseModel

dynaconf = FlaskDynaconf(dynaconf_instance=dynaconf)
db = SQLAlchemy(model_class=BaseModel)
debugbar = None

if find_spec("flask_debugtoolbar"):
    from flask_debugtoolbar import DebugToolbarExtension

    debugbar = DebugToolbarExtension()
