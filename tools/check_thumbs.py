"""Checks that every program wrote the same thumbnails: same files, same pixel sizes, and close pixels.

usage: python tools/check_thumbs.py REFERENCE_DIR OTHER_DIR...
Prints one JSON object: per folder, the file count, how many sizes match the reference exactly, the largest size
difference in pixels, and the lowest and median PSNR (dB) against the reference thumbnail.
"""
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.float64)


def psnr(a, b):
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    mse = np.mean((a[:h, :w] - b[:h, :w]) ** 2)
    return 99.0 if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def main():
    ref = Path(sys.argv[1])
    names = sorted(p.name for p in ref.glob("*.webp"))
    out = {}
    for d in map(Path, sys.argv[1:]):
        same, worst, scores = 0, 0, []
        files = sorted(p.name for p in d.glob("*.webp"))
        for n in names:
            a, b = load(ref / n), load(d / n)
            diff = max(abs(a.shape[0] - b.shape[0]), abs(a.shape[1] - b.shape[1]))
            same += diff == 0
            worst = max(worst, diff)
            scores.append(psnr(a, b))
        out[d.name] = {"files": len(files), "same_size": same, "max_size_diff_px": worst,
                       "psnr_min_db": round(min(scores), 2), "psnr_median_db": round(statistics.median(scores), 2)}
    print(json.dumps(out))


main()
