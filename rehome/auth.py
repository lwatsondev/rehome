from flask import current_app as app
from flask_httpauth import HTTPTokenAuth

auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def verify_token(token):
    return token == app.config.get("uploads.upload_token")
