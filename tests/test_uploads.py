import hashlib
import io
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import pytest

import rehome.paths
from rehome.extensions import db
from rehome.models.upload import Upload, _generate_slug

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def uploads_dir(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(rehome.paths, "UPLOADS", uploads)
    return uploads


def _post_bytes(client, content: bytes, filename: str, auth_headers):
    return client.post(
        "/f/",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        headers=auth_headers,
    )


@pytest.mark.parametrize(
    ("filename", "suffix"),
    [
        ("hello.txt", ".txt"),
        ("image.png", ".png"),
        ("script.py", ".py"),
        ("archive.tar.gz", ".tar.gz"),
        ("video.mp4", ".mp4"),
    ],
)
def test_upload(client, uploads_dir, auth_headers, filename, suffix):
    content = (FIXTURES / filename).read_bytes()
    response = _post_bytes(client, content, filename, auth_headers)

    assert response.status_code == HTTPStatus.CREATED
    assert "url" in response.json

    slug = response.json["url"].split("/")[-1]
    path = uploads_dir / slug
    assert path.is_file()
    assert "".join(path.suffixes) == suffix

    db.session.rollback()  # Ensure we have a clean session to test the database record.
    record = db.session.get(Upload, slug)
    assert record is not None
    assert str(record.name) == filename
    assert path.read_bytes() == content
    assert record.file_hash == hashlib.sha256(content).hexdigest()


def test_generate_slug_retries_on_collision(app):
    db.session.add(
        Upload(Path("abcde.txt"), Path("original.txt"), 100, "text/plain", "deadbeef")
    )
    db.session.flush()

    with mock.patch(
        "rehome.models.upload.random_string", side_effect=["abcde", "fghij"]
    ):
        slug = _generate_slug(Path("original.txt"))

    assert slug == Path("fghij.txt")


def test_delete_removes_file(client, uploads_dir, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    response = _post_bytes(client, content, "hello.txt", auth_headers)

    slug = response.json["url"].split("/")[-1]
    path = uploads_dir / slug
    assert path.is_file()

    record = db.session.get(Upload, slug)
    db.session.delete(record)
    db.session.commit()

    assert not path.exists()


def test_upload_rename(client, uploads_dir, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    first = _post_bytes(client, content, "hello.txt", auth_headers)
    second = _post_bytes(client, content, "other.txt", auth_headers)

    assert first.json["url"] == second.json["url"]

    slug = first.json["url"].split("/")[-1]
    db.session.rollback()  # Ensure we have a clean session to test the database record.
    record = db.session.get(Upload, slug)
    assert record is not None
    assert str(record.name) == "other.txt"


def test_list_uploads(client, uploads_dir, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    _post_bytes(client, content, "hello.txt", auth_headers)

    response = client.get("/f/", headers=auth_headers)

    assert response.status_code == HTTPStatus.OK
    data = response.json
    assert len(data) == 1
    assert data[0]["name"] == "hello.txt"
    assert "slug" in data[0]
    assert "size" in data[0]
    assert "mimetype" in data[0]
    assert "created_at" in data[0]
    assert "url" in data[0]


def test_wildcard_delete(client, uploads_dir, auth_headers):
    txt_slug = (
        _post_bytes(
            client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )
    png_slug = (
        _post_bytes(
            client, (FIXTURES / "image.png").read_bytes(), "image.png", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )

    response = client.delete("/f/", query_string={"name": "*"}, headers=auth_headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json["deleted"] == 2
    assert db.session.get(Upload, txt_slug) is None
    assert db.session.get(Upload, png_slug) is None
    assert list(uploads_dir.iterdir()) == []


def test_upload_client_disconnect(client, uploads_dir, auth_headers):
    with mock.patch(
        "flask.wrappers.Request._load_form_data",
        side_effect=OSError("No more data"),
    ):
        response = client.post(
            "/f/",
            data={"file": (io.BytesIO(b"data"), "file.txt")},
            content_type="multipart/form-data",
            headers=auth_headers,
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json["error"] == "Upload interrupted."


def _post_expiring(
    client, content: bytes, filename: str, auth_headers, expires_in: int
):
    return client.post(
        "/f/",
        data={"file": (io.BytesIO(content), filename), "expires_in": str(expires_in)},
        content_type="multipart/form-data",
        headers=auth_headers,
    )


def test_upload_with_expiry(client, uploads_dir, auth_headers):
    before = datetime.now(UTC)
    response = _post_expiring(
        client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers, 3600
    )
    after = datetime.now(UTC)

    assert response.status_code == HTTPStatus.CREATED

    slug = response.json["url"].split("/")[-1]
    db.session.rollback()
    record = db.session.get(Upload, slug)

    assert record.expires_at is not None
    expires_at = record.expires_at.replace(tzinfo=UTC)
    assert (
        before + timedelta(seconds=3600)
        <= expires_at
        <= after + timedelta(seconds=3600)
    )


def test_expiry_minimum_clamp(client, uploads_dir, auth_headers):
    before = datetime.now(UTC)
    response = _post_expiring(
        client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers, 10
    )
    after = datetime.now(UTC)

    assert response.status_code == HTTPStatus.CREATED

    slug = response.json["url"].split("/")[-1]
    db.session.rollback()
    record = db.session.get(Upload, slug)

    assert record.expires_at is not None
    expires_at = record.expires_at.replace(tzinfo=UTC)
    assert (
        before + timedelta(seconds=10 * 60)
        <= expires_at
        <= after + timedelta(seconds=10 * 60)
    )


def test_expired_file_returns_404(client, uploads_dir, auth_headers):
    response = _post_expiring(
        client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers, 3600
    )
    slug = response.json["url"].split("/")[-1]

    record = db.session.get(Upload, slug)
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.session.commit()

    view_response = client.get(f"/f/{slug}")

    assert view_response.status_code == HTTPStatus.NOT_FOUND
    db.session.rollback()
    assert db.session.get(Upload, slug) is None
    assert not (uploads_dir / slug).exists()


def test_no_expiry_by_default(client, uploads_dir, auth_headers):
    response = _post_bytes(
        client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers
    )
    slug = response.json["url"].split("/")[-1]

    db.session.rollback()
    record = db.session.get(Upload, slug)
    assert record.expires_at is None


def test_invalid_expires_in(client, uploads_dir, auth_headers):
    response = client.post(
        "/f/",
        data={"file": (io.BytesIO(b"data"), "hello.txt"), "expires_in": "not-a-number"},
        content_type="multipart/form-data",
        headers=auth_headers,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "expires_in" in response.json["error"]


def test_list_filter_by_name(client, uploads_dir, auth_headers):
    _post_bytes(
        client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers
    )
    _post_bytes(
        client, (FIXTURES / "image.png").read_bytes(), "image.png", auth_headers
    )

    response = client.get("/f/", query_string={"name": "*.txt"}, headers=auth_headers)

    assert response.status_code == HTTPStatus.OK
    data = response.json
    assert len(data) == 1
    assert data[0]["name"] == "hello.txt"


def test_delete_with_filter(client, uploads_dir, auth_headers):
    txt_slug = (
        _post_bytes(
            client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )
    png_slug = (
        _post_bytes(
            client, (FIXTURES / "image.png").read_bytes(), "image.png", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )

    response = client.delete(
        "/f/", query_string={"name": "*.txt"}, headers=auth_headers
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json["deleted"] == 1
    assert db.session.get(Upload, txt_slug) is None
    assert db.session.get(Upload, png_slug) is not None


def test_delete_wildcard_ignores_filter(client, uploads_dir, auth_headers):
    txt_slug = (
        _post_bytes(
            client, (FIXTURES / "hello.txt").read_bytes(), "hello.txt", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )
    png_slug = (
        _post_bytes(
            client, (FIXTURES / "image.png").read_bytes(), "image.png", auth_headers
        )
        .json["url"]
        .split("/")[-1]
    )

    response = client.delete(
        "/f/", query_string={"name": "*", "mimetype": "text/*"}, headers=auth_headers
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json["deleted"] == 2
    assert db.session.get(Upload, txt_slug) is None
    assert db.session.get(Upload, png_slug) is None
