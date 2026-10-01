"""Copy the work folder into the git checkout before a release.

The work folder (Desktop/showcaseclaude) is not a git repository; the GitHub repo
lives in Desktop/showcase-webs. This script compares the two trees and copies new
and changed files into the checkout. It never deletes anything: files that exist only
in the checkout are listed so the owner can decide.

    py -3.14 scripts/release_sync.py                 # dry run: print what would change
    py -3.14 scripts/release_sync.py --apply         # copy the files
    py -3.14 scripts/release_sync.py --target D:/other/checkout

Skipped: runtime data, owner references, caches, secrets (.env) and local settings,
the same things .gitignore keeps out of the repo.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = SOURCE.parent / "showcase-webs"
# Skipped only at the top level (static/models is part of the site).
ROOT_SKIP = {"data", "output", "IMAGE", "models", "railway-backup", ".claude", ".tmpvol", ".tmpro",
             "extensions"}  # extensions/: local prototypes (Ko-fi uploader test), not part of the site
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", "node_modules", ".venv", "venv", ".playwright-cli",
             ".tmp_pytest_env", ".tmp_u2net_test"}
SKIP_FILES = {".env", "ENV.txt", "tail.txt", "PROMT.txt", ".locale-cache.json"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".tmp", ".log")


def tree(root: Path) -> dict:
    found = {}
    for folder, dirs, names in os.walk(root):
        top = Path(folder) == root
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (top and d in ROOT_SKIP)]
        for name in names:
            if name in SKIP_FILES or name.endswith(SKIP_SUFFIXES):
                continue
            path = Path(folder) / name
            found[path.relative_to(root).as_posix()] = path
    return found


def digest(path: Path) -> str:
    # Compare text files without line endings: git stores LF, Windows copies may be CRLF.
    data = path.read_bytes()
    if b"\0" not in data[:8192]:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--apply", action="store_true", help="copy files (default: dry run)")
    args = parser.parse_args()
    target = args.target.resolve()
    if not (target / ".git").exists():
        print(f"{target} is not a git checkout", file=sys.stderr)
        return 2
    source_files, target_files = tree(SOURCE), tree(target)
    added = sorted(set(source_files) - set(target_files))
    changed = sorted(k for k in set(source_files) & set(target_files) if digest(source_files[k]) != digest(target_files[k]))
    listed = subprocess.run(["git", "-C", str(target), "ls-files"], capture_output=True, text=True).stdout.splitlines()
    only_in_repo = sorted(k for k in set(target_files) - set(source_files) if k in set(listed))

    for label, items in (("new", added), ("changed", changed)):
        for item in items:
            print(f"{label:8} {item}")
    for item in only_in_repo:
        print(f"repo-only {item}  (not deleted; remove by hand if it is obsolete)")
    print(f"\n{len(added)} new, {len(changed)} changed, {len(only_in_repo)} only in the repo -> {target}")
    if not args.apply:
        print("Dry run. Add --apply to copy.")
        return 0
    for item in added + changed:
        destination = target / item
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_files[item], destination)
    print("Copied. Next: cd into the checkout, `git status`, review, commit, push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
