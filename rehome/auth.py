from flask import abort
from flask import current_app as app
from flask_httpauth import HTTPTokenAuth

auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def __verify_token(token: str) -> bool:
    return token == app.config.get("auth.token")


@auth.error_handler
def __auth_error_handler(status: int):
    abort(status)
