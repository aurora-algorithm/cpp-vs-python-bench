"""thumbs_pillow.py with a stopwatch around each stage, for the "where does the time go" picture.

usage: python py/thumbs_pillow_stages.py IN_DIR OUT_DIR STAGES.tsv
Writes one row per photo: decode, resize and encode seconds. Decode is Pillow's ImageFile.load (libjpeg-turbo),
resize is Image.resize minus the decode it triggers, encode is Image.save (libwebp plus the file write).
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageFile

SIZE = (512, 512)
QUALITY = 80
clock = {"decode": 0.0, "resize": 0.0}

_load = ImageFile.ImageFile.load
_resize = Image.Image.resize


def timed_load(self, *a, **k):
    t = time.perf_counter()
    try:
        return _load(self, *a, **k)
    finally:
        clock["decode"] += time.perf_counter() - t


def timed_resize(self, *a, **k):
    t, before = time.perf_counter(), clock["decode"]
    try:
        return _resize(self, *a, **k)
    finally:
        clock["resize"] += time.perf_counter() - t - (clock["decode"] - before)


ImageFile.ImageFile.load = timed_load
Image.Image.resize = timed_resize


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(exist_ok=True)
    rows = []
    for path in sorted(src.glob("*.jpg")):
        clock.update(decode=0.0, resize=0.0)
        with Image.open(path) as im:
            im.thumbnail(SIZE)
            t = time.perf_counter()
            im.save(dst / f"{path.stem}.webp", quality=QUALITY)
            encode = time.perf_counter() - t
        rows.append(f"{path.name}\t{clock['decode']:.6f}\t{clock['resize']:.6f}\t{encode:.6f}")
    Path(sys.argv[3]).write_text("file\tdecode\tresize\tencode\n" + "\n".join(rows) + "\n")


main()
