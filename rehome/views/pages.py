from urllib.parse import urlparse

from flask import Blueprint
from flask import current_app as app
from flask import render_template, request

blueprint = Blueprint("pages", __name__)


@blueprint.get("/")
def index():
    http_host_key = urlparse(request.base_url).hostname.replace(".", "_")

    return render_template(
        "pages/index.html",
        profile_links=app.config.get(
            f"rehome.profile.external.{http_host_key}",
            app.config.get("rehome.profile.external.default"),
        ),
    )
