from flask import Flask

from rehome.views import pages, uploads


def register_blueprints(app: Flask):
    app.register_blueprint(pages.blueprint)
    app.register_blueprint(uploads.blueprint)
