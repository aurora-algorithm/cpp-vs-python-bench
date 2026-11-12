"""Test 1: shrink a photo 4x by hand. Every output pixel is the average of a 4 x 4 block, one channel at a time.

usage: python py/shrink_loop.py IN.ppm OUT.ppm
"""
import os
import sys
import time

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
    out = bytearray(out_w * out_h * 3)
    progress = open(os.environ["PROGRESS_OUT"], "w") if os.environ.get("PROGRESS_OUT") else None
    start = time.perf_counter()
    for y in range(out_h):
        for x in range(out_w):
            for c in range(3):
                total = 0
                for dy in range(BLOCK):
                    row = ((y * BLOCK + dy) * width + x * BLOCK) * 3 + c
                    for dx in range(BLOCK):
                        total += src[row + dx * 3]
                out[(y * out_w + x) * 3 + c] = (total + 8) // 16
        if progress and (y % 8 == 7 or y == out_h - 1):
            progress.write(f"{y + 1}\t{time.perf_counter() - start:.6f}\n")
    with open(sys.argv[2], "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (out_w, out_h))
        f.write(out)


main()
