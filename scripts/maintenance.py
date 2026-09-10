#!/usr/bin/env python3
"""Turn the site-wide maintenance notice on or off from a VPS shell."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smweb.maintenance import get_state, set_state


def main(argv: list[str]) -> int:
    command = (argv[1] if len(argv) > 1 else "status").strip().lower()
    if command in {"on", "enable"}:
        state = set_state(True, " ".join(argv[2:]))
    elif command in {"off", "disable"}:
        state = set_state(False)
    elif command == "status":
        state = get_state()
    else:
        print('Usage: python scripts/maintenance.py on ["custom message"] | off | status')
        return 2
    label = "ON" if state["enabled"] else "OFF"
    suffix = f" — {state['message']}" if state.get("message") else ""
    print(f"Maintenance notice: {label}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
