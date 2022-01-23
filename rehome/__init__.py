import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration
from webassets import Bundle
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import paths
from rehome.extensions import assets, db, dynaconf


def create_app():
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
    )

    load_configuration(app)
    register_extensions(app)
    register_blueprints(app)
    register_assets(app)

    if not app.debug and not app.testing:
        ProxyFix(app)

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
    bundles = {
        "css-app": Bundle(
            f"{paths.NODE_MODULES}/purecss/build/pure.css",
            "scss/main.scss",
            filters="libsass,cssmin",
            output="css/main-%(version)s.css",
        )
    }

    with app.app_context():
        assets.directory = app.static_folder
        assets.append_path(paths.ASSETS)

    for name, bundle in bundles.items():
        assets.register(name, bundle)

    app.logger.debug("Assets registered.")
