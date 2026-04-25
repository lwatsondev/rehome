from http import HTTPStatus

from flask import Blueprint, render_template
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException

blueprint = Blueprint("pages", __name__)


@blueprint.app_errorhandler(HTTPException)
def _base_error_handler(error: HTTPException):
    try:
        template = render_template(f"errors/{error.code}.html", error=error)
    except TemplateNotFound:
        template = render_template("layouts/error.html", error=error)

    return template, error.code


@blueprint.get("/")
def index():
    return render_template("pages/index.html")


@blueprint.get("/_/health")
def health():
    return "", HTTPStatus.NO_CONTENT
