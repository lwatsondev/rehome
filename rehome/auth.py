# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

from flask import Flask, abort
from flask_httpauth import HTTPTokenAuth
from sqlalchemy import exists, inspect, select

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
        if not inspect(db.engine).has_table(AuthToken.__tablename__):
            return

        has_tokens = db.session.scalar(select(exists(select(AuthToken.name))))

        if not has_tokens:
            token = AuthToken.generate("default")
            db.session.add(token)
            db.session.commit()
            app.logger.warning(f"No auth tokens found. Generated token: {token.token}")
