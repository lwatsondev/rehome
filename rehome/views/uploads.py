from datetime import UTC, datetime, timedelta
from http import HTTPMethod, HTTPStatus

import humanize
import mistune
import nh3
from flask import (
    Blueprint,
    Response,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask import current_app as app
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
)

from rehome import paths
from rehome.auth import auth
from rehome.extensions import db
from rehome.forms.upload import UploadForm
from rehome.models.upload import (
    ORDER_ASC,
    ORDER_DESC,
    SORT_COLUMNS,
    Upload,
    UploadSaveError,
    build_filter_clauses,
)
from rehome.views.pages import _base_error_handler

blueprint = Blueprint("uploads", __name__, url_prefix="/f")

_MIN_EXPIRY_SECONDS = 10 * 60
_MAX_VIEWER_SIZE = 1024 * 1024 * 2  # 2 MB

_MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})

_markdown = mistune.create_markdown(plugins=["strikethrough", "table", "url"])

_MARKDOWN_ALLOWED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "hr",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "del",
    "code",
    "pre",
    "a",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}

_MARKDOWN_ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "th": {"align"},
    "td": {"align"},
}


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

    filter_clauses = build_filter_clauses(
        name=request.args.get("name"),
        slug=request.args.get("slug"),
        mimetype=request.args.get("mimetype"),
        expired="expired" in request.args,
    )

    uploads = db.session.scalars(
        select(Upload).where(*filter_clauses).order_by(col)
    ).all()

    return [
        {
            "slug": str(upload.slug),
            "name": str(upload.name),
            "size": upload.size,
            "mimetype": upload.mimetype,
            "created_at": upload.created_at.isoformat(),
            "expires_at": upload.expires_at.isoformat() if upload.expires_at else None,
            "url": upload.url,
        }
        for upload in uploads
    ]


@blueprint.post("/")
@auth.login_required
def upload_file():
    try:
        form = UploadForm(CombinedMultiDict([request.form, request.files]))
    except OSError as exc:
        raise UploadError(
            code=HTTPStatus.BAD_REQUEST,
            description="Upload interrupted.",
        ) from exc

    if not form.validate_on_submit():
        raise ValidationError(description=form.errors)

    fd = form.file.data
    upload = Upload.from_file(fd, fd.filename)

    if form.expires_in.data is not None:
        if form.expires_in.data == 0:
            upload.expires_at = None
        else:
            upload.expires_at = datetime.now(UTC) + timedelta(
                seconds=max(_MIN_EXPIRY_SECONDS, form.expires_in.data)
            )
    elif sa_inspect(upload).transient:
        upload.expires_at = None

    try:
        upload.save(fd)
    except UploadSaveError as error:
        msg = "An error occurred while saving a file."
        app.logger.exception(msg)
        raise UploadError(description=f"{msg} Check the application logs.") from error

    if db.session.is_modified(upload):
        db.session.commit()

    return __make_upload_file_response(upload)


def _get_upload(slug: str) -> Upload:
    upload = Upload.one_or_404(slug=slug)

    if upload.is_expired:
        app.logger.debug(f"{upload.slug} has expired and will be deleted.")
        upload.delete()
        raise NotFound

    return upload


def _read_text_content(upload: Upload) -> str | None:
    if upload.size > _MAX_VIEWER_SIZE or upload.mimetype.startswith("audio/"):
        return None

    try:
        return upload.path.read_text(encoding="utf-8")
    except UnicodeDecodeError, OSError:
        return None


def _apply_expiry_cache(response: Response, upload: Upload) -> Response:
    if upload.expires_at_utc is not None:
        response.cache_control.max_age = int(
            (upload.expires_at_utc - datetime.now(UTC)).total_seconds()
        )

    return response


def _serve_raw(upload: Upload, as_attachment: bool = False) -> Response:
    force_plain_text = app.config.get("uploads.force_plain_text_mimetypes")
    mimetype = "text/plain" if upload.mimetype in force_plain_text else upload.mimetype

    if app.config.get("uploads.use_x_accel_redirect"):
        relative_path = upload.path.relative_to(paths.UPLOADS)
        disposition = "attachment" if as_attachment else "inline"

        response = make_response()
        response.headers["Content-Type"] = mimetype
        response.headers["Content-Disposition"] = (
            f'{disposition}; filename="{upload.name}"'
        )
        response.headers["X-Accel-Redirect"] = f"/{relative_path}"
    else:
        response = send_file(
            upload.path,
            mimetype=mimetype,
            as_attachment=as_attachment,
            download_name=str(upload.name),
        )

    return _apply_expiry_cache(response, upload)


@blueprint.get("<string:slug>")
def view(slug: str):
    upload = _get_upload(slug)

    if "text/html" not in request.headers.get("Accept", ""):
        return _serve_raw(upload)

    content = _read_text_content(upload)
    if content is not None:
        highlight_languages = app.config.get("uploads.mimetype_to_highlight_language")
        ext_languages = {
            ext: lang
            for lang, exts in app.config.get(
                "uploads.highlight_language_extensions"
            ).items()
            for ext in exts
        }

        suffix = upload.name.suffix.lower()
        language = (
            ext_languages.get(suffix)
            or suffix.lstrip(".")
            or highlight_languages.get(upload.mimetype, "plaintext")
        )

        template_ctx = {
            "upload": upload,
            "size": humanize.naturalsize(upload.size, gnu=True),
            "language": language,
        }
        template_ctx["content"] = content

        if upload.name.suffix.lower() in _MARKDOWN_SUFFIXES:
            template_ctx["rendered"] = nh3.clean(
                _markdown(content),
                tags=_MARKDOWN_ALLOWED_TAGS,
                attributes=_MARKDOWN_ALLOWED_ATTRS,
                set_tag_attribute_values={"a": {"target": "_blank"}},
                url_schemes={"http", "https", "mailto"},
            )

        return _apply_expiry_cache(
            make_response(render_template("pages/upload_view.html.j2", **template_ctx)),
            upload,
        )

    return _serve_raw(upload)


@blueprint.get("<string:slug>/raw")
def raw(slug: str):
    upload = _get_upload(slug)

    if _read_text_content(upload) is None:
        return redirect(url_for("uploads.view", slug=slug))

    return _serve_raw(upload, as_attachment="attachment" in request.args)


@blueprint.delete("/")
@auth.login_required
def delete_uploads():
    filter_clauses = build_filter_clauses(
        name=request.args.get("name"),
        slug=request.args.get("slug"),
        mimetype=request.args.get("mimetype"),
        expired="expired" in request.args,
    )

    if "*" in request.args.values():
        uploads = db.session.scalars(select(Upload)).all()
        for upload in uploads:
            upload.delete()

        return {"deleted": len(uploads)}

    if filter_clauses:
        uploads = db.session.scalars(select(Upload).where(*filter_clauses)).all()
        for upload in uploads:
            upload.delete()

        return {"deleted": len(uploads)}

    return {"deleted": 0}
