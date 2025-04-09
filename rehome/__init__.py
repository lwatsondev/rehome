import logging
import os

import sentry_sdk
from flask import Flask, url_for
from libgravatar import Gravatar
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import debug, meta, paths
from rehome.extensions import db, debugbar, dynaconf


def create_app() -> Flask:
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
    )

    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    app.logger.info(f"Starting {app.name} {meta.FULL_VERSION}")

    for path in [paths.STATIC, paths.DATA]:
        path.mkdir(exist_ok=True, parents=True)

    init_extensions(app)
    register_blueprints(app)
    register_context_processors(app)

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
            release=meta.FULL_VERSION,
        )
        app.logger.info("Sentry is enabled")


@debug.log_func
def init_extensions(app: Flask):
    dynaconf.init_app(app)
    init_sentry(app)

    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_RECORD_QUERIES=app.debug,  # for debugbar
    )

    db.init_app(app)

    app.config.update(SESSION_USE_SIGNER=True)

    if app.debug and debugbar is not None:
        debugbar.init_app(app)


@debug.log_func
def register_context_processors(app: Flask):
    @app.context_processor
    def inject_nav_links():
        nav_links = app.config.get("nav_links")
        return {"nav_links": nav_links}

    @app.context_processor
    def inject_avatar_url():
        avatar_url = url_for("static", filename="img/avatar.webp")
        if email := app.config.get("gravatar.email"):
            avatar_url = Gravatar(email).get_image(size=512)
        return {"avatar_url": avatar_url}

    @app.context_processor
    def inject_meta_info():
        return {"meta": meta}
