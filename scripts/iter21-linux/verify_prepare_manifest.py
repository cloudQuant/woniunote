#!/usr/bin/env python3
"""Verify that a builder output was prepared for the requested build inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--builder", choices=("system-libs", "vcpkg"), required=True)
    parser.add_argument("--variant", choices=("release", "test"), required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--vcpkg-installed-dir")
    parser.add_argument("--cmake-definition", action="append", default=[])
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"prepare manifest error: {exc}", file=sys.stderr)
        return 2

    expected = {
        "action": "prepare",
        "result": "completed",
        "variant": args.variant,
        "source": {"sha256": args.snapshot_sha256},
        "builder": {
            "kind": args.builder,
            "image_id": args.image_id,
            "vcpkg_installed_dir": args.vcpkg_installed_dir,
        },
        "cmake_definitions": args.cmake_definition,
    }
    for key, value in expected.items():
        actual = manifest.get(key)
        if isinstance(value, dict):
            if not isinstance(actual, dict):
                print(f"prepare manifest mismatch for {key}: expected an object", file=sys.stderr)
                return 1
            for child, child_value in value.items():
                if actual.get(child) != child_value:
                    print(f"prepare manifest mismatch for {key}.{child}", file=sys.stderr)
                    return 1
        elif actual != value:
            print(f"prepare manifest mismatch for {key}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
