import logging
import os

import sentry_sdk
from flask import Flask, url_for
from libgravatar import Gravatar
from werkzeug.middleware.proxy_fix import ProxyFix

from rehome import meta, paths
from rehome.extensions import db, debugbar, dynaconf


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        "rehome",
        static_folder=paths.STATIC,
        template_folder=paths.TEMPLATES,
        instance_path=paths.INSTANCE,
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
        _ensure_auth_token(app)

    return app


def register_commands(app: Flask):
    from rehome.cli.token import token_cli  # noqa: PLC0415

    app.cli.add_command(token_cli)


def register_blueprints(app: Flask):
    from rehome import views  # noqa: PLC0415

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


def _ensure_auth_token(app: Flask):
    from sqlalchemy import func, select  # noqa: PLC0415
    from sqlalchemy.exc import OperationalError  # noqa: PLC0415

    from rehome.models.auth_token import AuthToken  # noqa: PLC0415

    with app.app_context():
        try:
            count = db.session.scalar(select(func.count()).select_from(AuthToken))
        except OperationalError:
            db.session.rollback()
            return
        if count == 0:
            plaintext, token = AuthToken.generate("default")
            db.session.add(token)
            db.session.commit()
            app.logger.warning("No auth tokens found. Generated token: %s", plaintext)


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
