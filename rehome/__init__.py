from logging.config import dictConfig
from pathlib import Path

import sentry_sdk
from flask import Flask
from ruamel import yaml
from sentry_sdk.integrations.flask import FlaskIntegration

from rehome.extensions import assets, db, dynaconf
from rehome.paths import ASSETS_DIR, RESOURCE_DIR, STATIC_DIR, TEMPLATE_DIR


def create_app():
    setup_logging()
    app = Flask(
        "rehome", static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR)
    )

    register_extensions(app)
    register_blueprints(app)
    register_assets(app)

    return app


def register_blueprints(app):
    from rehome import views

    views.register_blueprints(app)
    app.logger.debug("Blueprints registered.")


def init_sentry(app):
    if (dsn := app.config.get("sentry_dsn")) and not (app.debug or app.testing):
        app.logger.info("Sentry enabled.")
        sentry_sdk.init(
            dsn=dsn,
            environment=app.env,
            integrations=[FlaskIntegration()],
        )
    else:
        app.logger.debug("Sentry disabled.")


def register_extensions(app):
    dynaconf.init_app(app)
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_SECURE=not app.debug,
        SESSION_USE_SIGNER=True,
    )

    init_sentry(app)

    assets.init_app(app)
    db.init_app(app)
    app.logger.debug("Extensions registered.")


def setup_logging():
    dictConfig(
        yaml.safe_load(Path(RESOURCE_DIR / "config" / "logging.yml").read_text())
    )


def register_assets(app):
    with app.app_context():
        assets.directory = STATIC_DIR
        assets.append_path(ASSETS_DIR)
        assets.auto_build = app.debug or app.testing

    assets.from_yaml(str(ASSETS_DIR / "assets.yml"))
    app.logger.debug("Assets registered.")
