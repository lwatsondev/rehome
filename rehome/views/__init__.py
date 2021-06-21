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
            title=f"{error.code} {error.name}",
            content_title=error.description,
            description=f"My personal {error.code} page. No guarantee of page.",
            tab_title=f"error/{error.code}",
        ),
        error.code,
    )
