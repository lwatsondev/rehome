import hashlib
import io
import struct
import tarfile
import zlib

import pytest
from sqlalchemy import select

import rehome.paths
from rehome.extensions import db
from rehome.models.upload import Upload


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


def _make_txt() -> bytes:
    return b"hello, world\n"


def _make_png() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc
    idat_payload = zlib.compress(b"\x00\xff\xff\xff")
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_payload) & 0xFFFFFFFF)
    idat = struct.pack(">I", len(idat_payload)) + b"IDAT" + idat_payload + idat_crc
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc
    return sig + ihdr + idat + iend


def _make_py() -> bytes:
    return b'print("hello, world")\n'


def _make_tar_gz() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        content = b"hello\n"
        info = tarfile.TarInfo(name="hello.txt")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _make_mp4() -> bytes:
    brands = b"isom" + struct.pack(">I", 0) + b"isommp42"
    ftyp = struct.pack(">I", 8 + len(brands)) + b"ftyp" + brands
    mdat = struct.pack(">I", 8) + b"mdat"
    return ftyp + mdat


@pytest.mark.parametrize(
    ("content", "filename", "suffix"),
    [
        (_make_txt(), "hello.txt", ".txt"),
        (_make_png(), "image.png", ".png"),
        (_make_py(), "script.py", ".py"),
        (_make_tar_gz(), "archive.tar.gz", ".tar.gz"),
        (_make_mp4(), "video.mp4", ".mp4"),
    ],
)
def test_upload(client, uploads_dir, auth_headers, content, filename, suffix):  # noqa: PLR0913
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
    content = _make_txt()
    first = _post_bytes(client, content, "hello.txt", auth_headers)
    second = _post_bytes(client, content, "other.txt", auth_headers)

    assert first.json["url"] == second.json["url"]

    name = first.json["url"].split("/")[-1]
    record = db.session.scalar(select(Upload).filter_by(name=name))
    assert str(record.original_name) == "other.txt"
