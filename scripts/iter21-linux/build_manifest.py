#!/usr/bin/env python3
"""Write a small provenance manifest for an Iteration 21 builder action."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--action", choices=("prepare", "build"), required=True)
    parser.add_argument("--builder", choices=("system-libs", "vcpkg"), required=True)
    parser.add_argument("--variant", choices=("release", "test"), required=True)
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    parser.add_argument("--source-commit")
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--prepare-manifest")
    parser.add_argument("--image", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--jobs", required=True, type=int)
    parser.add_argument("--cpus", required=True)
    parser.add_argument("--vcpkg-installed-dir")
    parser.add_argument("--cmake-definition", action="append", default=[])
    parser.add_argument("--cmake-option", action="append", default=[])
    args = parser.parse_args()

    manifest = {
        "schema": 1,
        "action": args.action,
        "result": "completed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "directory": args.snapshot_dir,
            "sha256": args.snapshot_sha256,
            "commit": args.source_commit or None,
            "manifest": args.source_manifest,
        },
        "builder": {
            "kind": args.builder,
            "image": args.image,
            "image_id": args.image_id,
            "jobs": args.jobs,
            "cpus": args.cpus,
            "vcpkg_installed_dir": args.vcpkg_installed_dir,
        },
        "variant": args.variant,
        "cmake_options": args.cmake_option,
        "cmake_definitions": args.cmake_definition,
        "prepared_configuration_manifest": args.prepare_manifest,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
