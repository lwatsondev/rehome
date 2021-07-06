from flask import Blueprint
from flask import current_app as app
from flask import render_template

blueprint = Blueprint("pages", __name__)


@blueprint.get("/")
def index():
    return render_template(
        "pages/index.html", profile_links=app.config.get("rehome.profile.external")
    )
