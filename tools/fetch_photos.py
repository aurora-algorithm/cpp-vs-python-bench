#!/usr/bin/env python3
"""Builds the benchmark's photo folder from CC0 "Quality images" on Wikimedia Commons.

usage: python3 tools/fetch_photos.py OUT_DIR [COUNT=100]

Each original is downloaded once, rotated upright, resized so its long edge is 4032 px (a 12-megapixel phone
photo) and saved as a baseline JPEG at quality 90. OUT_DIR/photos.tsv records every file's source page, author,
licence and the sha256 of the prepared JPEG, so anyone can rebuild the same folder. Also writes photo-001.ppm
(the first photo's raw pixels), test 1's input.
"""
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

API = "https://commons.wikimedia.org/w/api.php"
UA = "cpp-vs-python-bench/1.0 (benchmark photo set; https://github.com/)"
SEARCH = "incategory:Quality_images incategory:CC-Zero filemime:image/jpeg filew:>3900 filew:<6100"
LONG_EDGE = 4032
# Phone-like shapes only: 4:3 and 3:2, landscape or portrait (no panoramas or squares).
MIN_RATIO, MAX_RATIO = 1.30, 1.55
QUALITY = 90
MAX_BYTES = 30_000_000


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retried, then raised
            if attempt == 4:
                raise
            print(f"  retry {url[:80]}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def candidates():
    offset = 0
    while True:
        q = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6", "gsrlimit": "50",
             "gsrsearch": SEARCH, "gsroffset": str(offset), "prop": "imageinfo",
             "iiprop": "url|size|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist"}
        d = json.loads(get(f"{API}?{urllib.parse.urlencode(q)}"))
        pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        if not pages:
            return
        yield from pages
        if "continue" not in d:
            return
        offset = int(d["continue"]["gsroffset"])


def strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip().replace("\t", " ").replace("\n", " ")


def main() -> None:
    out = Path(sys.argv[1])
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in candidates():
        if len(rows) == count:
            break
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        w, h = ii["width"], ii["height"]
        ratio = max(w, h) / min(w, h)
        if lic != "CC0" or not (MIN_RATIO <= ratio <= MAX_RATIO) or ii["size"] > MAX_BYTES:
            continue
        try:
            im = Image.open(io.BytesIO(get(ii["url"])))
            im = ImageOps.exif_transpose(im).convert("RGB")
        except Exception as e:  # noqa: BLE001 - a broken file is skipped and logged
            print(f"skip {p['title']}: {e}", flush=True)
            continue
        scale = LONG_EDGE / max(im.size)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        name = f"photo-{len(rows) + 1:03d}.jpg"
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=QUALITY, subsampling="4:2:0", optimize=False, progressive=False)
        (out / name).write_bytes(buf.getvalue())
        if not rows:
            im.save(out / "photo-001.ppm")
        rows.append([name, f"{im.width}x{im.height}", hashlib.sha256(buf.getvalue()).hexdigest(),
                     p["title"], strip_html(meta.get("Artist", {}).get("value", "")), lic,
                     ii["descriptionurl"]])
        print(f"{name} {im.width}x{im.height} {p['title']}", flush=True)
        time.sleep(0.5)
    if len(rows) < count:
        sys.exit(f"only {len(rows)} photos found")
    head = ["file", "size", "sha256", "commons_title", "author", "licence", "source"]
    (out / "photos.tsv").write_text("\n".join("\t".join(r) for r in [head, *rows]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
