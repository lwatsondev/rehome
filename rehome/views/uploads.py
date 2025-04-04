import hashlib
from http import HTTPMethod, HTTPStatus
from pathlib import Path

import magic
from flask import Blueprint, make_response, redirect, request, send_file, url_for
from flask import current_app as app
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
)

from rehome import paths
from rehome.auth import auth
from rehome.extensions import db
from rehome.forms.upload import UploadForm
from rehome.models.upload import Upload
from rehome.views.pages import _base_error_handler

blueprint = Blueprint("uploads", __name__, url_prefix="/f")


class __UploadError(Exception):
    code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    description: str

    def __init__(
        self,
        code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        description: str = str | None,
    ):
        self.code = code
        self.description = description


class __ValidationError(__UploadError):
    code: int = HTTPStatus.BAD_REQUEST
    description: dict[str, str]

    def __init__(self, description: dict[str, str]):
        self.description = description


@blueprint.errorhandler(__UploadError)
def __upload_error_handler(error: __UploadError):
    return {
        "error": error.description,
    }, error.code


@blueprint.errorhandler(HTTPException)
def __http_error_handler(error: HTTPException):
    if request.method != HTTPMethod.DELETE and isinstance(error, NotFound):
        return _base_error_handler(error)

    return {
        "error": error.description,
    }, error.code


@blueprint.route("/", methods=[HTTPMethod.GET])
def index():
    return redirect(url_for("pages.index"))


@blueprint.route("/", methods=[HTTPMethod.POST])
@auth.login_required
def upload_file():
    form = UploadForm(request.files)
    if not form.validate_on_submit():
        raise __ValidationError(description=form.errors)

    fd = form.file.data
    file_contents = fd.read()
    fd.close()
    file_original_name = Path(fd.filename)
    file_size = len(file_contents)
    file_mimetype = magic.from_buffer(file_contents, mime=True)
    file_hash = hashlib.sha256(file_contents).hexdigest()

    view_route = "uploads.view"
    existing_upload = Upload.query.filter_by(file_hash=file_hash).first()
    if existing_upload:
        existing_upload.original_name = file_original_name
        existing_upload.mimetype = file_mimetype
        db.session.commit()

        return {
            "url": url_for(view_route, name=existing_upload.name, _external=True),
        }, HTTPStatus.CREATED

    upload = Upload(
        original_name=file_original_name,
        size=file_size,
        mimetype=file_mimetype,
        file_hash=file_hash,
    )
    db.session.add(upload)

    try:
        db.session.commit()
        upload.path.parent.mkdir(exist_ok=True)
        upload.path.write_bytes(file_contents)
    except (FileNotFoundError, OSError, IntegrityError) as error:
        db.session.rollback()
        upload.path.unlink(missing_ok=True)
        app.logger.error(error)
        raise __UploadError(
            description="An error occured while saving the file. Check the application logs."
        ) from error

    return {
        "url": url_for(view_route, name=upload.name, _external=True),
    }, HTTPStatus.CREATED


@blueprint.route("<string:name>", methods=[HTTPMethod.GET])
def view(name: str):
    upload = Upload.query.filter_by(name=name).first_or_404()
    # Treat html/xml types as plaintext for display purposes so they're not rendered by browsers.
    mimetype = (
        "text/plain"
        if upload.mimetype
        in [
            "text/html",
            "multipart/related",
            "application/xhtml+xml",
            "application/xml",
        ]
        else upload.mimetype
    )

    if app.config.get("uploads.use_x_accel_redirect"):
        relative_path = upload.path.relative_to(paths.UPLOADS)
        response = make_response()
        response.headers["Content-Type"] = mimetype
        response.headers["Content-Disposition"] = (
            f'inline; filename="{upload.original_name}"'
        )
        response.headers["X-Accel-Redirect"] = f"/{relative_path}"
        return response

    return send_file(
        upload.path,
        mimetype=mimetype,
        download_name=str(upload.original_name),
    )


@blueprint.route("<string:name>", methods=[HTTPMethod.DELETE])
@auth.login_required
def delete(name: str):
    upload = Upload.query.filter_by(name=name).first_or_404()
    db.session.delete(upload)
    db.session.commit()
    return {"status": "deleted"}
