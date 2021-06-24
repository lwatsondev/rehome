from flask import render_template
from jinja2 import TemplateNotFound
from werkzeug.exceptions import default_exceptions

from rehome.views.pages import blueprint as pages_blueprint


def register_blueprints(app):
    for http_exception in default_exceptions:
        app.register_error_handler(http_exception, error_handler)

    app.register_blueprint(pages_blueprint)


def error_handler(error):
    try:
        template = render_template(f"errors/{error.code}.html", error=error)
    except TemplateNotFound:
        template = render_template("layouts/error.html", error=error)

    return template, error.code
