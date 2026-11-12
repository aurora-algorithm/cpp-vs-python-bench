"""Test 2: turn every JPEG in a folder into a WebP thumbnail, 512 px on its long edge, with Pillow.

usage: python py/thumbs_pillow.py IN_DIR OUT_DIR
"""
import os
import sys
import time
from pathlib import Path

from PIL import Image

SIZE = (512, 512)
QUALITY = 80


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(exist_ok=True)
    progress = open(os.environ["PROGRESS_OUT"], "w") if os.environ.get("PROGRESS_OUT") else None
    start = time.perf_counter()
    for i, path in enumerate(sorted(src.glob("*.jpg")), 1):
        with Image.open(path) as im:
            im.thumbnail(SIZE)
            im.save(dst / f"{path.stem}.webp", quality=QUALITY)
        if progress:
            progress.write(f"{i}\t{time.perf_counter() - start:.6f}\n")


main()
