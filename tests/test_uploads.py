from pathlib import Path

import pytest
from sqlalchemy import select

import rehome.paths
from rehome.extensions import db
from rehome.models.upload import Upload

LOREM_IPSUM = Path(__file__).parent / "fixtures" / "lorem.txt"


@pytest.fixture
def uploads_dir(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(rehome.paths, "UPLOADS", uploads)
    return uploads


def _post_file(client, filename, auth_headers):
    with LOREM_IPSUM.open("rb") as f:
        return client.post(
            "/f/",
            data={"file": (f, filename)},
            content_type="multipart/form-data",
            headers=auth_headers,
        )


def test_upload_file(client, uploads_dir, auth_headers):
    response = _post_file(client, "lorem.txt", auth_headers)

    assert response.status_code == 201
    assert "url" in response.json
    assert next(uploads_dir.iterdir()).suffix == ".txt"

    name = response.json["url"].split("/")[-1]
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert record is not None
    assert str(record.original_name) == "lorem.txt"


def test_upload_rename(client, uploads_dir, auth_headers):
    first = _post_file(client, "lorem.txt", auth_headers)
    second = _post_file(client, "other.txt", auth_headers)

    assert first.json["url"] == second.json["url"]

    name = first.json["url"].split("/")[-1]
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert str(record.original_name) == "other.txt"
