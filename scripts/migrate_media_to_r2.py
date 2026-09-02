#!/usr/bin/env python3
"""Upload persistent legacy media directories to the public R2 bucket."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smweb import object_store


DIRS = ("avatars", "gallery", "profile_assets", "profile_bg", "profile_sc")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not object_store.configured():
        raise SystemExit("R2 credentials are not configured")
    total = 0
    for dirname in DIRS:
        base = args.source / dirname
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            key = path.relative_to(args.source).as_posix()
            total += 1
            if args.apply:
                # gallery/ keys carry a random suffix and are never rewritten;
                # avatars and profile media are overwritten under a stable key.
                object_store.upload_file(
                    path, key, public=True, immutable=key.startswith("gallery/")
                )
            print(("UPLOAD " if args.apply else "CHECK  ") + key)
    print(f"{'Uploaded' if args.apply else 'Would upload'} {total} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
