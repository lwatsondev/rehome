from flask import abort
from flask_httpauth import HTTPTokenAuth

from rehome.models.auth_token import AuthToken

auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def _verify_token(token: str) -> bool:
    return AuthToken.verify(token)


@auth.error_handler
def _auth_error_handler(status: int):
    abort(status)
