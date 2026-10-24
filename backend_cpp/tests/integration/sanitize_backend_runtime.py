#!/usr/bin/env python3
"""Copy allowlisted metadata from run-owned Linux backend attempts."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
INSTANCE_RE = re.compile(r"^(primary|secondary-[0-9a-f]{12})$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-\[\]]{0,255}$")
ALLOWED_FIELDS = (
    "run_id",
    "instance",
    "backend_container_id",
    "binary_sha256",
    "runtime_image",
    "runtime_image_id",
    "base_image",
    "base_image_id",
    "runtime_spec_sha256",
    "http_port",
    "credentials_included",
)


def fail() -> None:
    raise ValueError("backend runtime metadata is invalid")


def private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        fail()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail()
        result[key] = value
    return result


def sanitized_payload(source: Path, run_id: str, expected_instance: str) -> dict[str, Any]:
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        fail()
    payload = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(payload, dict) or not set(ALLOWED_FIELDS).issubset(payload):
        fail()

    if payload.get("run_id") != run_id or payload.get("instance") != expected_instance:
        fail()
    if not RUN_ID_RE.fullmatch(str(payload.get("run_id", ""))):
        fail()
    if not INSTANCE_RE.fullmatch(str(payload.get("instance", ""))):
        fail()
    if not CONTAINER_ID_RE.fullmatch(str(payload.get("backend_container_id", ""))):
        fail()
    for field in ("binary_sha256", "runtime_spec_sha256"):
        if not SHA256_RE.fullmatch(str(payload.get(field, ""))):
            fail()
    for field in ("runtime_image", "base_image"):
        if not isinstance(payload.get(field), str) or not IMAGE_RE.fullmatch(payload[field]):
            fail()
    for field in ("runtime_image_id", "base_image_id"):
        value = payload.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            fail()
    if type(payload.get("http_port")) is not int or not 1024 <= payload["http_port"] <= 65535:
        fail()
    if payload.get("credentials_included") is not False:
        fail()

    return {field: payload[field] for field in ALLOWED_FIELDS}


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: sanitize_backend_runtime.py EVIDENCE_DIR RESULT_DIR RUN_ID", file=sys.stderr)
        return 2
    evidence_dir = Path(sys.argv[1])
    result_dir = Path(sys.argv[2])
    run_id = sys.argv[3]
    try:
        if not RUN_ID_RE.fullmatch(run_id):
            fail()
        private_directory(evidence_dir)
        private_directory(result_dir)
        sources = sorted(evidence_dir.glob("backend-runtime-*.json"))
        outputs: list[tuple[Path, bytes]] = []
        for source in sources:
            match = re.fullmatch(r"backend-runtime-(primary|secondary-[0-9a-f]{12})\.json", source.name)
            if not match:
                fail()
            output = result_dir / source.name
            if output.exists() or output.is_symlink():
                fail()
            content = sanitized_payload(source, run_id, match.group(1))
            outputs.append((output, (json.dumps(content, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))

        for output, content in outputs:
            temporary = output.with_suffix(output.suffix + ".tmp")
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            os.replace(temporary, output)
            os.chmod(output, 0o600)
    except (OSError, ValueError, json.JSONDecodeError):
        print("ERROR: refused unsafe backend runtime metadata; no metadata was exported.", file=sys.stderr)
        return 2
    print(f"Exported allowlisted Linux backend metadata records: {len(outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
