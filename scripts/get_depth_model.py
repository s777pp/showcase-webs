"""Download the depth model for the Process "Depth" effect into <project>/models/ (local runs).

    py -3.14 scripts/get_depth_model.py

The Docker image downloads the same file itself (Dockerfile, same URL and checksum). /models/ is ignored by git and
scripts/release_sync.py, so the 99 MB file never reaches the repository.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

URL = ("https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/"
       "4472b7362082ad9968fee890ca0f1e5aca36b93d/onnx/model.onnx")
SHA256 = "afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c"
TARGET = Path(__file__).resolve().parents[1] / "models" / "depth_anything_v2_small.onnx"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if TARGET.is_file() and digest(TARGET) == SHA256:
        print(f"Already there: {TARGET}")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    partial = TARGET.with_suffix(".part")
    print("Downloading the depth model (99 MB)...")
    urllib.request.urlretrieve(URL, partial)
    if digest(partial) != SHA256:
        partial.unlink(missing_ok=True)
        print("Checksum mismatch: the file was not saved.")
        return 1
    partial.replace(TARGET)
    print(f"Saved: {TARGET}. Restart the site server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
