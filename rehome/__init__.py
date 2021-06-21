from logging.config import dictConfig

from flask import Flask

from rehome.config import Config, ConfigFile
from rehome.paths import (
    STATIC_DIR,
    TEMPLATE_DIR,
)


def create_app():
    setup_logging()
    app = Flask(
        "rehome", static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR)
    )
    app.config.from_object(Config())

    register_blueprints(app)
    return app


def register_blueprints(app):
    from rehome import views

    views.register_blueprints(app)
    app.logger.debug("Blueprints registered.")


def setup_logging():
    dictConfig(ConfigFile("logging.yml").load().to_dict())
