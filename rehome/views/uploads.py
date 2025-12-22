from http import HTTPMethod, HTTPStatus

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
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
)

from rehome import paths
from rehome.auth import auth
from rehome.forms.upload import UploadForm
from rehome.models.upload import Upload, UploadSaveError
from rehome.views.pages import _base_error_handler

blueprint = Blueprint("uploads", __name__, url_prefix="/f")


class UploadError(Exception):
    code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    description: str | None

    def __init__(
        self,
        code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        description: str | None = None,
    ):
        self.code = code
        self.description = description


class ValidationError(UploadError):
    code: int = HTTPStatus.BAD_REQUEST
    description: dict[str, str]

    def __init__(self, description: dict[str, str]):
        self.description = description


@blueprint.errorhandler(UploadError)
def __upload_error_handler(error: UploadError):
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


@blueprint.get("/")
def index():
    return redirect(url_for("pages.index"))


@blueprint.post("/")
@auth.login_required
def upload_file():
    form = UploadForm(request.files)
    if not form.validate_on_submit():
        raise ValidationError(description=form.errors)

    fd = form.file.data
    upload = Upload.from_file(fd)

    try:
        upload.save(fd)
    except UploadSaveError as error:
        msg = "An error occurred while saving the file."
        app.logger.exception(msg)
        raise UploadError(description=f"{msg} Check the application logs.") from error

    return __make_upload_file_response(upload)


@blueprint.get("<string:name>")
def view(name: str):
    upload = Upload.one_or_404(name=name)
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


@blueprint.delete("<string:name>")
@auth.login_required
def delete(name: str):
    upload = Upload.one_or_404(name=name)
    upload.delete()
    return {"status": "deleted"}
