import logging
import os
import sqlite3

import sentry_sdk
from flask import Flask, url_for
from jinja2 import select_autoescape
from libgravatar import Gravatar
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import auth, meta, paths, scheduler, views
from rehome.cli.token import token_cli
from rehome.cli.upload import upload_cli
from rehome.extensions import db, debugbar, dynaconf


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
        instance_path=paths.INSTANCE,
    )
    app.jinja_env.autoescape = select_autoescape(
        ["html", "htm", "xml", "xhtml", "html.j2"]
    )
    dynaconf.init_app(app)

    if test_config is not None:
        app.config.update(test_config)

    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
        init_sentry(app)

    if not app.testing:
        paths.ensure_dirs()

    init_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_context_processors(app)

    if not app.debug and not app.testing:
        app.wsgi_app = ProxyFix(app.wsgi_app)

    if not app.testing:
        auth.ensure_auth_token(app)
        scheduler.start(app)

    return app


def register_commands(app: Flask):
    app.cli.add_command(token_cli)
    app.cli.add_command(upload_cli)


def register_blueprints(app: Flask):
    views.register_blueprints(app)


def init_sentry(app: Flask):
    if (dsn := app.config.get("sentry.dsn")) and not (app.debug or app.testing):
        sentry_sdk.init(
            dsn=dsn,
            release=meta.FULL_VERSION,
        )
        app.logger.info("Sentry is enabled")


def init_extensions(app: Flask):
    app.config.update(
        SQLALCHEMY_RECORD_QUERIES=app.debug,  # for debugbar
        SESSION_USE_SIGNER=True,
        SQLALCHEMY_ENGINES={
            "default": {
                "url": app.config.get(
                    "SQLALCHEMY_DATABASE_URI",
                    f"sqlite:////{paths.DATA}/app.db",
                )
            }
        },
    )

    db.init_app(app)

    if app.debug and debugbar is not None:
        debugbar.init_app(app)


def register_context_processors(app: Flask):
    @app.context_processor
    def inject_nav_links():
        nav_links = app.config.get("nav_links")
        return {"nav_links": nav_links}

    @app.context_processor
    def inject_avatar():
        avatar_url = url_for("static", filename="img/avatar.webp")
        if email := app.config.get("gravatar.email"):
            avatar_url = Gravatar(email).get_image(size=256)

        return {"avatar_url": avatar_url}

    @app.context_processor
    def inject_meta_info():
        return {"meta": meta}


@event.listens_for(Engine, "connect")
def _set_sqlite_wal_mode(dbapi_connection, _connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
