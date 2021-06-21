from flask import render_template

from rehome.views.pages import blueprint as pages_blueprint


def register_blueprints(app):
    app.register_error_handler(404, page_not_found)
    app.register_blueprint(pages_blueprint)


def page_not_found(error):
    return (
        render_template(
            "errors/404.html",
            error=error,
            title="ERROR",
            content_title="The page you are trying to reach does not exist.",
            description="My personal 404 page. No guarantee of page.",
            tab_title="404",
        ),
        404,
    )
