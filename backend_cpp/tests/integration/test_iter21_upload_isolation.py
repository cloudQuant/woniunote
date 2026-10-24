"""Real HTTP checks for run-owned UploadController and UEditor file placement.

These are API-level upload checks. They exercise the real authentication
fixture and do not replace the browser editor's UI acceptance flow.
"""

from __future__ import annotations

import os
import re
import stat
import struct
import zlib
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import pytest
import requests

from iter21_support import BASE_URL, RUN_ID, TIMEOUT, response_json, url


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    chunk = kind + payload
    return (
        struct.pack(">I", len(payload))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    )


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
    + _png_chunk(b"IEND", b"")
)


def _owned_run_paths() -> tuple[Path, Path, Path]:
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{12}", RUN_ID):
        pytest.fail("isolated runner did not provide a valid run id")
    if os.environ.get("WONIUNOTE_TEST_RUN_ID") != RUN_ID:
        pytest.fail("test process run id does not match the isolated runner")

    raw_run_dir = os.environ.get("WONIUNOTE_TEST_RUNTIME_DIR", "")
    if not raw_run_dir or not Path(raw_run_dir).is_absolute():
        pytest.fail("isolated runner did not provide an absolute runtime directory")

    parsed_base = urlsplit(BASE_URL)
    if (
        parsed_base.scheme != "http"
        or parsed_base.hostname != "127.0.0.1"
        or parsed_base.port is None
        or parsed_base.port in {3306, 6379, 5173, 8888}
        or parsed_base.path
        or parsed_base.query
        or parsed_base.fragment
    ):
        pytest.fail("isolated runner did not provide its loopback backend URL")

    try:
        run_dir = Path(raw_run_dir).resolve(strict=True)
    except OSError:
        pytest.fail("isolated runner runtime directory is unavailable")

    if run_dir.name != RUN_ID or run_dir.parent.name != "woniunote-iter21":
        pytest.fail("runtime directory does not match the runner's run identity")

    for directory in (
        run_dir.parent,
        run_dir,
        run_dir / "uploads",
        run_dir / "backend-runtime",
    ):
        if directory.is_symlink() or not directory.is_dir():
            pytest.fail("run-owned upload isolation directory is unavailable")
        metadata = directory.stat()
        if stat.S_IMODE(metadata.st_mode) != 0o700 or metadata.st_uid != os.geteuid():
            pytest.fail("run-owned upload isolation directory is not private")

    return run_dir, run_dir / "uploads", run_dir / "backend-runtime"


@pytest.fixture(autouse=True)
def require_owned_upload_context():
    # Fail before the authenticated fixture registers a user if the runner
    # did not provide its private runtime and loopback backend identity.
    _owned_run_paths()


def _local_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        pytest.fail(f"{label} omitted its upload URL")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        pytest.fail(f"{label} returned a non-local upload path")
    if not parsed.path.startswith("/"):
        pytest.fail(f"{label} returned a malformed upload path")
    return parsed.path


def _relative_parts(path: str) -> tuple[str, ...]:
    parsed = PurePosixPath(path)
    parts = parsed.parts[1:]
    if not parsed.is_absolute() or not parts or any(part in {".", ".."} for part in parts):
        pytest.fail("upload URL contains an unsafe path")
    return parts


def _assert_download(path: str) -> None:
    downloaded = requests.get(url(path), timeout=TIMEOUT)
    assert downloaded.status_code == 200, "uploaded image URL did not return HTTP 200"
    content_types = downloaded.raw.headers.getlist("Content-Type")
    assert [value.split(";", 1)[0].strip().lower() for value in content_types] == [
        "image/png"
    ], "uploaded image URL must return exactly one image/png Content-Type header"
    assert downloaded.content == PNG_BYTES, "downloaded image bytes changed"


def _assert_owned_file(path: Path, run_dir: Path) -> None:
    assert not path.is_symlink(), "uploaded file must not be a symlink"
    assert path.is_file(), "uploaded file was not written to its run-owned location"
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(run_dir)
    except ValueError:
        pytest.fail("uploaded file resolved outside this run directory")
    assert resolved.read_bytes() == PNG_BYTES, "run-owned file bytes differ from the upload"


def test_upload_controller_image_round_trips_from_document_root(user):
    run_dir, document_root, _backend_runtime = _owned_run_paths()

    response = requests.post(
        url("/api/upload/image"),
        headers=user.headers,
        files={"file": ("iter21-isolation.png", PNG_BYTES, "image/png")},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "image upload did not return HTTP 200"
    body = response_json(response)
    assert body.get("code") == 200, "image upload returned an unsuccessful response"
    data = body.get("data")
    assert isinstance(data, dict), "image upload omitted its response data"

    image_url = _local_path(data.get("url"), "UploadController")
    match = re.fullmatch(
        r"/uploads/uploads/images/(\d{4})/(\d{2})/(\d+_\d{4}\.png)", image_url
    )
    assert match, "UploadController returned an unexpected image URL"

    relative_parts = _relative_parts(image_url)
    stored_file = document_root.joinpath(*relative_parts)
    # upload_path is document_root/uploads; UploadController appends a relative
    # path beginning with uploads/, and its public URL adds the serving prefix.
    expected_file = (
        run_dir
        / "uploads"
        / "uploads"
        / "uploads"
        / "images"
        / match.group(1)
        / match.group(2)
        / match.group(3)
    )
    assert stored_file == expected_file, "image URL does not map through document_root to upload_path"
    _assert_owned_file(stored_file, run_dir)
    _assert_download(image_url)


def test_ueditor_image_stays_in_run_uploads_not_cwd_or_shared_parent(user):
    run_dir, uploads, backend_runtime = _owned_run_paths()

    response = requests.post(
        url("/api/uedit"),
        params={"action": "uploadimage"},
        headers=user.headers,
        files={"upfile": ("iter21-ueditor-isolation.png", PNG_BYTES, "image/png")},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, "UEditor upload did not return HTTP 200"
    body = response_json(response)
    assert body.get("state") == "SUCCESS", "UEditor rejected the image upload"

    image_url = _local_path(body.get("url"), "UEditor")
    prefix = "/api/uploads/"
    assert image_url.startswith(prefix), "UEditor returned an unexpected image URL"
    filename = image_url[len(prefix) :]
    assert re.fullmatch(r"[A-Za-z0-9_.-]+\.png", filename), "UEditor returned an unsafe filename"

    stored_file = uploads / filename
    assert stored_file.parent == uploads
    _assert_owned_file(stored_file, run_dir)
    assert not (backend_runtime / "uploads" / filename).exists(), (
        "UEditor wrote under backend-runtime/uploads instead of run/uploads"
    )
    assert not (run_dir.parent / "uploads" / filename).exists(), (
        "UEditor wrote into a shared parent uploads directory"
    )
    _assert_download(image_url)
