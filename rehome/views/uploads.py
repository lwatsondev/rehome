from http import HTTPMethod, HTTPStatus

from flask import (
    Blueprint,
    Response,
    make_response,
    request,
    send_file,
)
from flask import current_app as app
from sqlalchemy import select
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
)

from rehome import db, paths
from rehome.auth import auth
from rehome.forms.upload import UploadForm
from rehome.models.upload import (
    ORDER_ASC,
    ORDER_DESC,
    SORT_COLUMNS,
    Upload,
    UploadSaveError,
)
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
@auth.login_required
def list_uploads():
    sort = request.args.get("sort", "created")
    order = request.args.get("order", ORDER_ASC)

    if sort not in SORT_COLUMNS:
        raise UploadError(
            code=HTTPStatus.BAD_REQUEST,
            description=f"Invalid sort: {sort!r}. Choose from: {', '.join(SORT_COLUMNS)}",
        )

    if order not in (ORDER_ASC, ORDER_DESC):
        raise UploadError(
            code=HTTPStatus.BAD_REQUEST,
            description=f"Invalid order: {order!r}. Choose from: {ORDER_ASC}, {ORDER_DESC}",
        )

    col = SORT_COLUMNS[sort]
    col = col.desc() if order == ORDER_DESC else col.asc()

    uploads = db.session.scalars(select(Upload).order_by(col)).all()
    return [
        {
            "slug": str(upload.slug),
            "name": str(upload.name),
            "size": upload.size,
            "mimetype": upload.mimetype,
            "created_at": upload.created_at.isoformat(),
            "url": upload.url,
        }
        for upload in uploads
    ]


@blueprint.post("/")
@auth.login_required
def upload_file():
    form = UploadForm(request.files)
    if not form.validate_on_submit():
        raise ValidationError(description=form.errors)

    fd = form.file.data
    upload = Upload.from_file(fd, fd.filename)

    try:
        upload.save(fd)
    except UploadSaveError as error:
        msg = "An error occurred while saving a file."
        app.logger.exception(msg)
        raise UploadError(description=f"{msg} Check the application logs.") from error

    return __make_upload_file_response(upload)


@blueprint.get("<string:slug>")
def view(slug: str):
    upload = Upload.one_or_404(slug=slug)

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
        response.headers["Content-Disposition"] = f'inline; filename="{upload.name}"'
        response.headers["X-Accel-Redirect"] = f"/{relative_path}"
        return response

    return send_file(
        upload.path,
        mimetype=mimetype,
        download_name=str(upload.name),
    )


@blueprint.delete("/")
@auth.login_required
def delete_uploads():
    slugs = (request.get_json() or {}).get("slugs", [])

    if "*" in slugs:
        uploads = db.session.scalars(select(Upload)).all()
        for upload in uploads:
            upload.delete()
        return {"deleted": len(uploads)}

    uploads, not_found = [], []
    for slug in slugs:
        upload = db.session.get(Upload, slug)
        if upload:
            uploads.append(upload)
        else:
            not_found.append(slug)

    if not_found:
        raise UploadError(
            code=HTTPStatus.NOT_FOUND,
            description=f"Not found: {', '.join(not_found)}",
        )

    for upload in uploads:
        upload.delete()

    return {"deleted": len(uploads)}
