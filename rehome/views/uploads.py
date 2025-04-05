import hashlib
import os
from http import HTTPMethod, HTTPStatus
from pathlib import Path

import magic
from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    request,
    send_file,
    url_for,
)
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


def __make_upload_file_response(upload: Upload) -> Response:
    response = make_response(
        {
            "url": upload.url,
        }
    )
    response.headers["Location"] = upload.url
    response.status_code = HTTPStatus.CREATED

    return response


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
    file_original_name = Path(fd.filename)
    fd.seek(0, os.SEEK_END)
    file_size = fd.tell()
    fd.seek(0, os.SEEK_SET)
    file_mimetype = magic.from_buffer(fd.read(4096), mime=True)
    fd.seek(0, os.SEEK_SET)
    file_hash = hashlib.file_digest(fd, hashlib.sha256).hexdigest()
    fd.seek(0, os.SEEK_SET)

    existing_upload_query = db.select(Upload).filter_by(file_hash=file_hash)
    existing_upload = db.session.execute(existing_upload_query).scalar()
    if existing_upload:
        existing_upload.original_name = file_original_name
        existing_upload.mimetype = file_mimetype
        db.session.commit()
        return __make_upload_file_response(existing_upload)

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
        fd.save(
            upload.path,
            buffer_size=app.config.get("uploads.save_chunk_size", 1024 * 128),
        )  # Using 128KB chunks to match ZFS' default recordsize.
    except (FileNotFoundError, OSError, IntegrityError) as error:
        db.session.rollback()
        upload.path.unlink(missing_ok=True)
        app.logger.error(error)
        raise __UploadError(
            description="An error occured while saving the file. Check the application logs."
        ) from error

    return __make_upload_file_response(upload)


@blueprint.route("<string:name>", methods=[HTTPMethod.GET])
def view(name: str):
    upload = db.one_or_404(db.select(Upload).filter_by(name=name))
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
    upload = db.one_or_404(db.select(Upload).filter_by(name=name))
    db.session.delete(upload)
    db.session.commit()
    return {"status": "deleted"}
