from dynaconf import Dynaconf, FlaskDynaconf
from flask_assets import Environment
from flask_sqlalchemy import SQLAlchemy

from rehome.paths import CONFIG_DIR

dynaconf = FlaskDynaconf(
    dynaconf_instance=Dynaconf(
        settings_file=CONFIG_DIR / "config.yml",
        environments=False,
        envvar_prefix="FLASK",
    ),
)
assets = Environment()
db = SQLAlchemy()
