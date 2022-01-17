import os

import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration
from webassets import Bundle

from rehome.extensions import assets, db, dynaconf
from rehome.paths import ASSETS_DIR, TEMPLATE_DIR


def create_app():
    app = Flask(
        "rehome",
        static_folder=os.getenv("FLASK_STATIC_DIR", "static"),
        template_folder=str(TEMPLATE_DIR),
    )

    load_configuration(app)

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


def load_configuration(app):
    dynaconf.init_app(app)
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_USE_SIGNER=True,
    )


def register_extensions(app):
    init_sentry(app)
    assets.init_app(app)
    db.init_app(app)
    app.logger.debug("Extensions registered.")


def register_assets(app):
    with app.app_context():
        assets.directory = app.static_folder
        assets.append_path(ASSETS_DIR)

    node_modules = os.getenv("NODE_MODULES", "../../node_modules")
    bundles = {
        "css-app": Bundle(
            f"{node_modules}/purecss/build/pure.css",
            "scss/main.scss",
            filters="libsass,cssmin",
            output="css/main-%(version)s.css",
        )
    }

    for name, bundle in bundles.items():
        assets.register(name, bundle)

    app.logger.debug("Assets registered.")
