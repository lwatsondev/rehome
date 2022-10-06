from distutils.dir_util import copy_tree
from urllib.parse import urlparse

import sentry_sdk
from flask import Flask, request
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from webassets import Bundle
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import paths
from rehome.extensions import assets, db, debugbar, dynaconf


def create_app() -> Flask:
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
    )

    for path in [paths.STATIC, paths.DATA]:
        path.mkdir(exist_ok=True)

    load_configuration(app)
    register_extensions(app)
    register_blueprints(app)
    register_assets(app)
    register_context_processors(app)

    if not app.debug and not app.testing:
        ProxyFix(app)

    return app


def register_blueprints(app: Flask):
    app.logger.debug("register_blueprints")

    from rehome import views

    views.register_blueprints(app)


def init_sentry(app: Flask):
    app.logger.debug("init_sentry")

    if (dsn := app.config.get("sentry_dsn")) and not (app.debug or app.testing):
        sentry_sdk.init(
            dsn=dsn,
            environment="production",
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
        )
        app.logger.info("Sentry is enabled")


def load_configuration(app: Flask):
    app.logger.debug("load_configuration")

    dynaconf.init_app(app)
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_USE_SIGNER=True,
    )


def register_extensions(app: Flask):
    app.logger.debug("register_extensions")

    init_sentry(app)
    assets.init_app(app)
    db.init_app(app)

    if app.debug and debugbar is not None:
        debugbar.init_app(app)


def register_assets(app: Flask):
    app.logger.debug("register_assets")

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
        assets.auto_build = app.debug or app.testing
        assets.append_path(paths.ASSETS)

    for name, bundle in bundles.items():
        assets.register(name, bundle)

    precompiled_assets = ["img", "fonts"]
    for asset_type in precompiled_assets:
        copy_tree(
            str(paths.ASSETS / asset_type), str(paths.STATIC / asset_type), update=1
        )


def register_context_processors(app: Flask):
    app.logger.debug("register_context_processors")

    @app.context_processor
    def inject_menu():
        http_host = urlparse(request.base_url).hostname.replace(".", "_")
        menu = app.config.get(
            f"rehome.profile.external.{http_host}",
            app.config.get("rehome.profile.external.default"),
        )
        return {"menu": menu}
