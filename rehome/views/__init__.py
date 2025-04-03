from flask import Flask, render_template
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException, default_exceptions

from rehome.views import pages, uploads


def register_blueprints(app: Flask):
    for http_exception in default_exceptions:
        app.register_error_handler(http_exception, error_handler)

    app.register_blueprint(pages.blueprint)
    app.register_blueprint(uploads.blueprint)


def error_handler(error: HTTPException):
    try:
        template = render_template(f"errors/{error.code}.html", error=error)
    except TemplateNotFound:
        template = render_template("layouts/error.html", error=error)

    return template, error.code
