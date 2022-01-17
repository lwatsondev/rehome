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
