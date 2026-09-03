#!/usr/bin/env python3
"""Generate access codes and print them ready to paste into env vars.

    python scripts/gen_access_codes.py 10 --label Pro

Codes are NEVER written to the repo. Put the output into the ACCESS_CODES (or
ACCESS_CODES_JSON) variable of your deployment, or into DATA_DIR/access_codes.json
on the volume.

With --out the merged list is written straight to a file and nothing is printed,
so a large batch never passes through the terminal or shell history:

    python scripts/gen_access_codes.py 500 --out /data/access_codes.json --merge
"""
from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path


def gen_code(prefix: str = "SM-WEB") -> str:
    a = secrets.token_hex(3).upper()
    b = secrets.token_hex(2).upper()
    return f"{prefix}-{a}-{b}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate SteamShowcase access codes")
    ap.add_argument("count", nargs="?", type=int, default=5, help="how many codes (default 5)")
    ap.add_argument("--label", default="Pro", help="label shown to the user (default Pro)")
    ap.add_argument("--type", default="unlimited", help="code type: unlimited or trial")
    ap.add_argument("--hours", type=float, default=0.0,
                    help="lifetime for --type trial; ignored for unlimited. A trial code "
                         "without hours would grant permanent Pro")
    ap.add_argument("--prefix", default="SM-WEB", help="code prefix (default SM-WEB)")
    ap.add_argument("--out", type=Path, help="write the JSON list to this file instead of printing")
    ap.add_argument("--merge", action="store_true",
                    help="with --out: keep the codes already in the file (needed to preserve "
                         "codes buyers have not redeemed yet)")
    args = ap.parse_args()

    codes = []
    while len(codes) < args.count:
        c = gen_code(args.prefix)
        if c not in codes:
            codes.append(c)

    meta = {"type": args.type, "label": args.label}
    if args.type == "trial":
        if args.hours <= 0:
            raise SystemExit("--type trial requires --hours (e.g. --hours 2)")
        meta["hours"] = args.hours
    payload = {c: dict(meta) for c in codes}

    if args.out:
        merged = {}
        if args.merge and args.out.is_file():
            try:
                existing = json.loads(args.out.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    merged.update(existing)
            except Exception as exc:
                raise SystemExit(f"{args.out} exists but is not readable JSON: {exc}")
        merged.update(payload)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        # Only counts, never the codes themselves.
        print(f"{args.out}: +{len(payload)} new, {len(merged)} total")
        return

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
