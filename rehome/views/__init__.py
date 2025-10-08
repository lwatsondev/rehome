from typing import TYPE_CHECKING

from rehome.views import pages, uploads

if TYPE_CHECKING:
    from flask import Flask


def register_blueprints(app: Flask):
    app.register_blueprint(pages.blueprint)
    app.register_blueprint(uploads.blueprint)
