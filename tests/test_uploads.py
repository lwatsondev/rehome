import hashlib
import io
import pathlib

import pytest
from sqlalchemy import select

import rehome.paths
from rehome.extensions import db
from rehome.models.upload import Upload

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


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

    assert response.status_code == 201
    assert "url" in response.json

    name = response.json["url"].split("/")[-1]
    path = uploads_dir / name
    assert path.is_file()
    assert "".join(path.suffixes) == suffix

    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert record is not None
    assert str(record.original_name) == filename
    assert path.read_bytes() == content
    assert record.file_hash == hashlib.sha256(content).hexdigest()


def test_upload_rename(client, auth_headers):
    content = (FIXTURES / "hello.txt").read_bytes()
    first = _post_bytes(client, content, "hello.txt", auth_headers)
    second = _post_bytes(client, content, "other.txt", auth_headers)

    assert first.json["url"] == second.json["url"]

    name = first.json["url"].split("/")[-1]
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert str(record.original_name) == "other.txt"
