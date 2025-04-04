import hashlib
import shutil
import tempfile
from pathlib import Path

import magic
from flask import Blueprint, make_response, redirect, request, send_file, url_for
from flask import current_app as app
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from rehome import paths
from rehome.auth import auth
from rehome.extensions import db
from rehome.forms.upload import UploadForm
from rehome.models.upload import Upload, generate_upload_name
from rehome.util import random_string

blueprint = Blueprint("uploads", __name__, url_prefix="/f")


@blueprint.route("/", methods=["GET"])
def index():
    return redirect(url_for("pages.index"))


@blueprint.route("/", methods=["POST"])
@auth.login_required
def upload_file():
    form = UploadForm(request.files)
    if not form.validate_on_submit():
        return {"errors": form.errors}

    fd = form.file.data
    file_original_name = Path(fd.filename)
    tmp_dir = Path(tempfile.gettempdir()) / "rehome"
    tmp_file = tmp_dir / Path(
        random_string(32) + secure_filename(str(file_original_name))
    )
    tmp_file.parent.mkdir(exist_ok=True)
    fd.save(tmp_file)

    file_name = generate_upload_name(tmp_file.suffix)
    file_size = tmp_file.stat().st_size
    file_contents = tmp_file.read_bytes()
    file_mimetype = magic.from_buffer(file_contents, mime=True)
    file_hash = hashlib.sha256(file_contents).hexdigest()

    view_route = "uploads.view"
    existing_upload = Upload.query.filter_by(file_hash=file_hash).first()
    if existing_upload:
        existing_upload.original_name = file_original_name
        existing_upload.mimetype = file_mimetype
        db.session.commit()

        return {"url": url_for(view_route, name=existing_upload.name, _external=True)}

    upload = Upload(
        name=file_name,
        original_name=file_original_name,
        size=file_size,
        mimetype=file_mimetype,
        file_hash=file_hash,
    )
    db.session.add(upload)

    try:
        db.session.commit()
        upload.path.parent.mkdir(exist_ok=True)
        shutil.move(tmp_file, upload.path)
    except (FileNotFoundError, OSError, IntegrityError) as exc:
        db.session.rollback()
        tmp_file.unlink()
        app.logger.error(exc)
        return {
            "errors": [
                "An error occured while processing your file. Try uploading again."
            ]
        }

    return {"url": url_for(view_route, name=upload.name, _external=True)}


@blueprint.route("<string:name>", methods=["GET"])
def view(name: str):
    file_instance = Upload.query.filter_by(name=name).first_or_404()
    relative_path = file_instance.path.relative_to(paths.UPLOADS)

    if app.config.get("uploads.use_x_accel_redirect"):
        response = make_response()
        response.headers["Content-Type"] = file_instance.mimetype
        response.headers["Content-Disposition"] = (
            f'inline; filename="{file_instance.original_name}"'
        )
        response.headers["X-Accel-Redirect"] = f"/{relative_path}"
        return response

    return send_file(
        file_instance.path,
        mimetype=file_instance.mimetype,
        download_name=str(file_instance.original_name),
    )
