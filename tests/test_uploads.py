import hashlib
import io
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import select

import rehome.paths
from rehome.extensions import db
from rehome.models.upload import Upload, _generate_name

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

    name = response.json["url"].split("/")[-1]
    path = uploads_dir / name
    assert path.is_file()
    assert "".join(path.suffixes) == suffix

    db.session.rollback()  # Ensure we have a clean session to test the database record.
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert record is not None
    assert str(record.original_name) == filename
    assert path.read_bytes() == content
    assert record.file_hash == hashlib.sha256(content).hexdigest()


def test_generate_name_retries_on_collision(app):
    db.session.add(
        Upload(Path("abcde.txt"), Path("original.txt"), 100, "text/plain", "deadbeef")
    )
    db.session.flush()

    with mock.patch(
        "rehome.models.upload.random_string", side_effect=["abcde", "fghij"]
    ):
        name = _generate_name(Path("original.txt"))

    assert name == Path("fghij.txt")


def test_delete_removes_file(client, uploads_dir, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    response = _post_bytes(client, content, "hello.txt", auth_headers)

    name = response.json["url"].split("/")[-1]
    path = uploads_dir / name
    assert path.is_file()

    record = db.session.scalar(select(Upload).filter_by(name=name))
    db.session.delete(record)
    db.session.commit()

    assert not path.exists()


def test_upload_rename(client, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    first = _post_bytes(client, content, "hello.txt", auth_headers)
    second = _post_bytes(client, content, "other.txt", auth_headers)

    assert first.json["url"] == second.json["url"]

    name = first.json["url"].split("/")[-1]
    db.session.rollback()  # Ensure we have a clean session to test the database record.
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert str(record.original_name) == "other.txt"
