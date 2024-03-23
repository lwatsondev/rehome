import shutil
from urllib.parse import urlparse

import sentry_sdk
from flask import Flask, request, url_for
from libgravatar import Gravatar
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from webassets import Bundle
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import debug, meta, paths
from rehome.extensions import assets, db, debugbar, dynaconf


def create_app() -> Flask:
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
    )

    app.logger.info(f"Starting {app.name} {meta.VERSION}")

    for path in [paths.STATIC, paths.DATA]:
        path.mkdir(exist_ok=True, parents=True)

    init_extensions(app)
    register_blueprints(app)
    register_context_processors(app)

    with app.app_context():
        register_assets(app)

    if not app.debug and not app.testing:
        app.wsgi_app = ProxyFix(app.wsgi_app)

    return app


@debug.log_func
def register_blueprints(app: Flask):
    from rehome import views

    views.register_blueprints(app)


@debug.log_func
def init_sentry(app: Flask):
    if (dsn := app.config.get("sentry.dsn")) and not (app.debug or app.testing):
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
            release=meta.VERSION,
        )
        app.logger.info("Sentry is enabled")


@debug.log_func
def init_extensions(app: Flask):
    dynaconf.init_app(app)
    init_sentry(app)
    assets.init_app(app)

    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_RECORD_QUERIES=app.debug,  # for debugbar
    )
    db.init_app(app)

    if app.debug and debugbar is not None:
        debugbar.init_app(app)

    app.config.update(SESSION_USE_SIGNER=True)  # for later


@debug.log_func
def register_assets(app: Flask):
    bundles = {
        "css-app": Bundle(
            f"{paths.NODE_MODULES}/purecss/build/pure.css",
            "scss/main.scss",
            filters="libsass,cssmin",
            output="css/main-%(version)s.css",
        )
    }

    assets.directory = app.static_folder
    assets.auto_build = app.debug or app.testing
    assets.append_path(paths.ASSETS)
    assets.config["LIBSASS_INCLUDES"] = [str(paths.NODE_MODULES)]

    for name, bundle in bundles.items():
        assets.register(name, bundle)

    precompiled_assets = ["img", "fonts"]
    for asset_type in precompiled_assets:
        shutil.copytree(
            paths.ASSETS / asset_type, paths.STATIC / asset_type, dirs_exist_ok=True
        )


@debug.log_func
def register_context_processors(app: Flask):
    @app.context_processor
    def inject_menu():
        http_host = urlparse(request.base_url).hostname.replace(".", "_")
        menu = app.config.get(
            f"home.links.{http_host}",
            app.config.get("home.links.default"),
        )
        return {"menu": menu}

    @app.context_processor
    def inject_avatar_url():
        avatar_url = url_for("static", filename="img/avatar.webp")
        if email := app.config.get("gravatar.email"):
            avatar_url = Gravatar(email).get_image(size=512)
        return {"avatar_url": avatar_url}
