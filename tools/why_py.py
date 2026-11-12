"""What CPython runs for test 1's innermost line, for the video's "why" picture.

usage: python tools/why_py.py     (with the benchmark's Python)
Prints JSON: the Python version, the bytecode instructions of `total += src[row + dx * 3]` in shrink_loop.py,
and the size in bytes of one pixel value as a Python int object.
"""
import dis
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "py/shrink_loop.py"
NEEDLE = "total += src[row + dx * 3]"


def main():
    text = SRC.read_text()
    line = next(i for i, l in enumerate(text.splitlines(), 1) if NEEDLE in l)
    module = compile(text, str(SRC), "exec")
    fn = next(c for c in module.co_consts if getattr(c, "co_name", "") == "main")
    ins = [f"{i.opname} {i.argrepr}".strip() for i in dis.get_instructions(fn) if i.positions and i.positions.lineno == line]
    draft = None
    try:
        from PIL import Image
        photo = SRC.parents[1] / "data/photos/photo-001.jpg"
        with Image.open(photo) as im:
            full = im.size
            im.draft(None, (1024, 1024))  # what thumbnail((512, 512)) asks for: reducing_gap 2.0
            draft = {"photo": photo.name, "full": list(full), "decoded": list(im.size)}
    except ImportError:
        pass
    print(json.dumps({"pillow_draft": draft, "python": sys.version.split()[0], "line": line, "source": NEEDLE, "bytecode": ins,
                      "int_object_bytes": sys.getsizeof(255), "pixel_bytes_cpp": 1, "int_bytes_cpp": 4}))


main()
