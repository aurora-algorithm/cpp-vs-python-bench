"""Test 2, libvips from Python: the same thumbnails as thumbs_pillow.py, through pyvips.

usage: python py/thumbs_pyvips.py IN_DIR OUT_DIR
"""
import os
import sys
import time
from pathlib import Path

# Python 3.8+ on Windows no longer looks up a DLL's dependencies on PATH, so libvips-42.dll's own DLLs need this.
if os.name == "nt" and os.environ.get("VIPS_BIN"):
    os.add_dll_directory(os.environ["VIPS_BIN"])

import pyvips  # noqa: E402

SIZE = 512
QUALITY = 80


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(exist_ok=True)
    progress = open(os.environ["PROGRESS_OUT"], "w") if os.environ.get("PROGRESS_OUT") else None
    start = time.perf_counter()
    for i, path in enumerate(sorted(src.glob("*.jpg")), 1):
        thumb = pyvips.Image.thumbnail(str(path), SIZE)
        thumb.webpsave(str(dst / f"{path.stem}.webp"), Q=QUALITY)
        if progress:
            progress.write(f"{i}\t{time.perf_counter() - start:.6f}\n")
    if progress:
        progress.close()


main()
# Every thumbnail is written and closed by now. On Windows, libvips 8.18 sometimes crashes with an access violation
# while Python tears down (seen in the i7 smoke, run 2), so the process leaves without the teardown.
sys.stdout.flush()
os._exit(0)
