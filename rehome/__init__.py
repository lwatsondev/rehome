from logging.config import dictConfig

from flask import Flask

from rehome.extensions import assets, db
from rehome.config import Config, ConfigFile
from rehome.paths import (
    ASSETS_DIR,
    STATIC_DIR,
    TEMPLATE_DIR,
)


def create_app():
    setup_logging()
    app = Flask(
        "rehome", static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR)
    )
    app.config.from_object(Config())

    register_extensions(app)
    register_blueprints(app)
    register_assets(app)
    return app


def register_blueprints(app):
    from rehome import views

    views.register_blueprints(app)
    app.logger.debug("Blueprints registered.")


def register_extensions(app):
    assets.init_app(app)
    db.init_app(app)
    app.logger.debug("Extensions registered.")


def setup_logging():
    dictConfig(ConfigFile("logging.yml").load().to_dict())


def register_assets(app):
    with app.app_context():
        assets.directory = STATIC_DIR
        assets.append_path(ASSETS_DIR)
        assets.auto_build = app.debug or app.testing

    assets.from_yaml(str(ASSETS_DIR / "assets.yml"))
    app.logger.debug("Assets registered.")
