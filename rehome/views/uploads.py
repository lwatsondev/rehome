import hashlib
import os
from pathlib import Path

import magic
from flask import Blueprint, make_response, redirect, request, send_file, url_for
from flask import current_app as app
from sqlalchemy.exc import IntegrityError

from rehome import paths
from rehome.auth import auth
from rehome.extensions import db
from rehome.forms.upload import UploadForm
from rehome.models.upload import Upload, generate_upload_name

blueprint = Blueprint("uploads", __name__, url_prefix="/f")


@blueprint.route("/", methods=["GET"])
def index():
    return redirect(url_for("pages.index"))


@blueprint.route("/", methods=["POST"])
@auth.login_required
def upload():
    form = UploadForm(request.files)
    if not form.validate_on_submit():
        return {"errors": form.errors}

    fd = form.file.data

    fd.seek(0, os.SEEK_END)
    file_size = fd.tell()
    fd.seek(0)

    file_contents = fd.read()
    fd.seek(0)

    file_hash = hashlib.sha256(file_contents).hexdigest()
    file_mimetype = magic.from_buffer(file_contents, mime=True)

    view_route = "uploads.view"
    extension = Path(fd.filename).suffix
    name = generate_upload_name()
    if extension:
        name = name + extension

    existing_file = Upload.query.filter_by(file_hash=file_hash).first()
    if existing_file:
        existing_file.original_name = fd.filename
        db.session.commit()

        return {"url": url_for(view_route, name=existing_file.name, _external=True)}

    file = Upload()
    file.original_name = fd.filename
    file.size = file_size
    file.file_hash = file_hash
    file.mimetype = file_mimetype
    file.name = name

    db.session.add(file)

    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        app.logger.error(exc)
        return {
            "errors": [
                "An error occured while processing your file. Try uploading again."
            ]
        }
    else:
        file.path.parent.mkdir(exist_ok=True)
        fd.save(file.path)

    return {"url": url_for(view_route, name=file.name, _external=True)}


@blueprint.route("<string:name>", methods=["GET"])
def view(name: str):
    file_instance = Upload.query.filter_by(name=name).first_or_404()
    relative_path = file_instance.path.relative_to(paths.UPLOADS)

    if app.config.get("uploads.use_x_accel_redirect"):
        response = make_response()
        response.headers["Content-Type"] = file_instance.response_mimetype
        response.headers["Content-Disposition"] = (
            f'inline; filename="{file_instance.original_name}"'
        )
        response.headers["X-Accel-Redirect"] = f"/{relative_path}"
        return response

    return send_file(
        file_instance.path,
        mimetype=file_instance.response_mimetype,
        download_name=file_instance.original_name,
    )
