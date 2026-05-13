from flask import Flask, abort
from flask_httpauth import HTTPTokenAuth
from sqlalchemy import exists, select

from rehome.extensions import db
from rehome.models.auth_token import AuthToken

auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def _verify_token(token: str) -> bool:
    return AuthToken.verify(token)


@auth.error_handler
def _auth_error_handler(status: int):
    abort(status)


def ensure_auth_token(app: Flask):
    with app.app_context():
        has_tokens = db.session.scalar(select(exists(select(AuthToken.name))))

        if not has_tokens:
            token = AuthToken.generate("default")
            db.session.add(token)
            db.session.commit()
            app.logger.warning("No auth tokens found. Generated token: %s", token.token)
