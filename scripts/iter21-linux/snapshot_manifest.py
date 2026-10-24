#!/usr/bin/env python3
"""Create and verify deterministic manifests for frozen Iteration 21 snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path


CONTROL_FILES = {".woniunote-iter21-source"}
MANIFEST_SCHEMA = 1


def excluded_directory(component: str) -> bool:
    return (
        component == ".git"
        or component == ".env"
        or component.startswith(".env.")
        or component in {"build", "node_modules", "dist", "coverage", "__pycache__", "secret", "secrets", ".venv", "venv"}
        or component.startswith("build-")
        or component.startswith("build_")
        or component.startswith("build.")
        or component == "config.local"
        or component.startswith("config.local.")
    )


def excluded_file(component: str) -> bool:
    return (
        component in {".env", "secret", "secrets", "config.local"}
        or component.startswith(".env.")
        or component.startswith("config.local.")
        or component.endswith(".local")
    )


def canonical_path(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if any(ord(char) < 32 for char in relative):
        raise ValueError(f"snapshot contains a path with control characters: {relative!r}")
    return relative


def snapshot_entries(root: Path) -> list[dict[str, object]]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"snapshot root is not a directory: {root}")

    root_real = os.path.realpath(root)
    paths: list[Path] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories.sort(key=os.fsencode)
        files.sort(key=os.fsencode)

        for directory in list(directories):
            path = current_path / directory
            relative = canonical_path(path, root)
            if any(excluded_directory(part) for part in Path(relative).parts):
                raise ValueError(f"snapshot includes an excluded directory: {relative}")
            if path.is_symlink():
                directories.remove(directory)
                paths.append(path)

        for filename in files:
            path = current_path / filename
            relative = canonical_path(path, root)
            parts = Path(relative).parts
            if any(excluded_directory(part) for part in parts[:-1]) or excluded_file(parts[-1]):
                raise ValueError(f"snapshot includes an excluded file: {relative}")
            if relative in CONTROL_FILES:
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"source marker must be a regular file: {relative}")
                continue
            paths.append(path)

    entries: list[dict[str, object]] = []
    for path in sorted(paths, key=lambda item: os.fsencode(canonical_path(item, root))):
        relative = canonical_path(path, root)
        if relative in CONTROL_FILES:
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(path)
            resolved_target = os.path.realpath(path)
            if os.path.commonpath((root_real, resolved_target)) != root_real:
                raise ValueError(f"snapshot symlink resolves outside the snapshot: {relative} -> {target}")
            entries.append({"path": relative, "type": "symlink", "target": target})
        elif stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "mode": format(stat.S_IMODE(metadata.st_mode), "04o"),
                    "sha256": digest.hexdigest(),
                }
            )
        else:
            raise ValueError(f"snapshot contains a non-file, non-symlink entry: {relative}")
    return entries


def canonical_manifest(entries: list[dict[str, object]]) -> bytes:
    lines = [
        json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        for entry in entries
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def write_snapshot_manifest(root: Path, output: Path | None) -> str:
    entries = snapshot_entries(root)
    body = canonical_manifest(entries)
    digest = hashlib.sha256(body).hexdigest()
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "snapshot_sha256": digest,
        "hash_definition": "sha256 of sorted canonical JSONL entries; excludes the source marker",
        "entries": entries,
    }
    serialized = (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if output is not None:
        output = output.resolve()
        root_real = root.resolve(strict=True)
        if os.path.commonpath((str(root_real), str(output))) == str(root_real):
            raise ValueError("manifest output must be outside the frozen source snapshot")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(serialized)
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="frozen source snapshot directory")
    parser.add_argument("--manifest", type=Path, help="optional JSON manifest output outside the snapshot")
    parser.add_argument("--expected", help="expected snapshot SHA-256 to verify")
    args = parser.parse_args()

    try:
        digest = write_snapshot_manifest(args.root, args.manifest)
        if args.expected and digest.lower() != args.expected.lower():
            print(f"snapshot SHA-256 mismatch: expected {args.expected}, got {digest}", file=sys.stderr)
            return 1
    except (OSError, ValueError) as exc:
        print(f"snapshot manifest error: {exc}", file=sys.stderr)
        return 2

    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
