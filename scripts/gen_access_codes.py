#!/usr/bin/env python3
"""Generate access codes and print them ready to paste into env vars.

    python scripts/gen_access_codes.py 10 --label Pro

Codes are NEVER written to the repo. Put the output into the ACCESS_CODES (or
ACCESS_CODES_JSON) variable of your deployment, or into DATA_DIR/access_codes.json
on the volume.
"""
from __future__ import annotations

import argparse
import json
import secrets


def gen_code(prefix: str = "SM-WEB") -> str:
    a = secrets.token_hex(3).upper()
    b = secrets.token_hex(2).upper()
    return f"{prefix}-{a}-{b}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate SteamShowcase access codes")
    ap.add_argument("count", nargs="?", type=int, default=5, help="how many codes (default 5)")
    ap.add_argument("--label", default="Pro", help="label shown to the user (default Pro)")
    ap.add_argument("--type", default="unlimited", help="code type (default unlimited)")
    ap.add_argument("--prefix", default="SM-WEB", help="code prefix (default SM-WEB)")
    args = ap.parse_args()

    codes = []
    while len(codes) < args.count:
        c = gen_code(args.prefix)
        if c not in codes:
            codes.append(c)

    payload = {c: {"type": args.type, "label": args.label} for c in codes}

    print("# --- codes ---")
    for c in codes:
        print(c)
    print()
    print("# --- simple form: paste as ACCESS_CODES ---")
    print("ACCESS_CODES=" + ",".join(codes))
    print()
    print("# --- labelled form: paste as ACCESS_CODES_JSON (single line) ---")
    print("ACCESS_CODES_JSON=" + json.dumps(payload, separators=(",", ":")))
    print()
    print("# --- or write to the volume as DATA_DIR/access_codes.json ---")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
