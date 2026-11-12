"""Test 1, NumPy: the same 4x shrink as shrink_loop.py, written as array operations.

usage: python py/shrink_numpy.py IN.ppm OUT.ppm
"""
import sys

import numpy as np

BLOCK = 4


def read_ppm(path):
    data = open(path, "rb").read()
    magic, w, h, maxval = data.split(maxsplit=4)[:4]
    if magic != b"P6" or maxval != b"255":
        sys.exit(f"{path}: not an 8-bit P6 PPM")
    header = len(b" ".join([magic, w, h, maxval])) + 1
    return int(w), int(h), data[header:]


def main():
    width, height, src = read_ppm(sys.argv[1])
    out_w, out_h = width // BLOCK, height // BLOCK
    pixels = np.frombuffer(src, dtype=np.uint8).reshape(height, width, 3)
    pixels = pixels[: out_h * BLOCK, : out_w * BLOCK].astype(np.uint16)
    total = pixels.reshape(out_h, BLOCK, out_w, BLOCK, 3).sum(axis=(1, 3))
    out = ((total + 8) // 16).astype(np.uint8)
    with open(sys.argv[2], "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (out_w, out_h))
        f.write(out.tobytes())


main()
