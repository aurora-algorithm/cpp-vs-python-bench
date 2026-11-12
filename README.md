# C++ vs Python: a pixel loop and 100 photos to WebP thumbnails

Code and per-run results behind the "C++ vs Python speed: 67x faster, until you resize real photos" Short.

## What is tested
**Test 1, the plain loop.** Each program reads one photo's raw pixels (`photo-001.ppm`, 4032 x 2678) and shrinks it
4x by hand: every output pixel is the rounded average of a 4 x 4 block, channel by channel. The outputs are
byte-identical (sha256 checked every round).

| Cell | Program |
|---|---|
| `py-loop` | `py/shrink_loop.py`, plain nested `for` loops |
| `cpp-loop` | `cpp/src/shrink_loop.cpp`, the same loops |
| `py-numpy` | `py/shrink_numpy.py`, the same arithmetic as NumPy array operations |

**Test 2, thumbnails.** Each program turns 100 photos (JPEGs, 4032 px on the long edge) into WebP thumbnails, 512 px on the long edge,
quality 80. Every program writes the same thumbnail sizes (Pillow's `thumbnail()` rounding, mirrored in
`cpp/src/common.hpp`). `tools/check_thumbs.py` compares sizes and PSNR against Pillow's thumbnails every round
(`results/i7win-20261109/round*/thumbs-check.json`).

| Cell | Program |
|---|---|
| `py-pillow` | `py/thumbs_pillow.py`: `Image.open`, `im.thumbnail((512, 512))`, `im.save(..., quality=80)` |
| `cpp-opencv` | `cpp/src/thumbs_opencv.cpp`: `cv::imread`, `cv::resize(INTER_AREA)`, `cv::imwrite(IMWRITE_WEBP_QUALITY 80)` |
| `py-pyvips` | `py/thumbs_pyvips.py`: `pyvips.Image.thumbnail(path, 512).webpsave(Q=80)` |
| `cpp-libvips` | `cpp/src/thumbs_vips.cpp`: `vips_thumbnail` + `vips_webpsave(Q 80)`, the calls pyvips makes |

pyvips and the C++ program load the same `libvips-42.dll` (vips-dev-x64-web-8.18.7). Every program runs one thread:
`cv::setNumThreads(1)`, `VIPS_CONCURRENCY=1`; Pillow is single-threaded.

In each recorded round, Pillow and OpenCV run once more with a stopwatch around each stage per photo: decode, resize,
encode (`py/thumbs_pillow_stages.py`, and `thumbs_opencv` with `STAGES_OUT`).

## Setup
- **Machine:** Intel i7-13700F PC, Windows 11 (10.0.26200), Balanced power plan, native (no containers).
- **Versions** (`results/i7win-20261109/meta.json`): Python 3.14.10, Pillow 13.0.0 (libjpeg-turbo 3.2.0, libwebp
  1.6.0), NumPy 2.5.4, pyvips 3.2.0, libvips 8.18.7, OpenCV 4.14.0 (prebuilt Windows package), clang 23.1.5
  `-O3 -march=native` against the MSVC runtime, hyperfine 2.0.0.
- **Pinning:** every cell pinned to logical CPU 4 (one performance core) with `tools/pin.py`. Before each cell the
  script waits until CPUs 4 and 5 average under 5% (both under 15%) and the whole machine is under 20%.
- **Runs:** hyperfine `-N`, 1 warm-up, then 10 runs (test 1) or 5 runs (test 2) per cell per round. 5 recorded rounds
  (hyperfine's live screen saved as an asciinema cast, `round*/*.cast`), with the language order alternating between
  rounds, plus 1 plain round without the recorder.
- **Photos:** 100 CC0 "Quality images" from Wikimedia Commons, resized to 4032 px on the long edge and saved as
  baseline JPEG quality 90 by `tools/fetch_photos.py`. `data/photos.tsv` lists each file's source page, author,
  licence and sha256. The photos themselves are not in the repo.

## Results (medians of all recorded runs, `results/i7win-20261109/summary.json`)
| Cell | Median | Runs |
|---|---|---|
| `py-loop` | 2.193 s | 50 |
| `cpp-loop` | 0.033 s | 50 |
| `py-numpy` | 0.299 s | 50 |
| `py-pillow` | 6.096 s | 25 |
| `cpp-opencv` | 8.449 s | 25 |
| `py-pyvips` | 4.504 s | 25 |
| `cpp-libvips` | 4.474 s | 25 |

The plain round is within 1.3% of the recorded medians for every cell (`plain_vs_recorded` in the same file).

Where test 2's time goes (`stages_s` in the same file, seconds for all 100 photos, median of the 5 rounds):

| Stage | Pillow | OpenCV |
|---|---|---|
| decode | 2.208 | 5.547 |
| resize | 1.207 | 1.514 |
| encode | 2.626 | 1.559 |
| everything else | 0.190 | 0.174 |

Pillow's `thumbnail()` asks libjpeg-turbo for a reduced decode: photo-001 (4032 x 2678) is decoded at 2016 x 1339
(`results/i7win-20261109/why_py.json`, `pillow_draft`). `cv::imread` decodes the full photo.

`why_py.json` also lists the 9 bytecode instructions CPython 3.14 runs for the inner line of `shrink_loop.py`.

## Reproduce
On Windows 11 with Visual Studio 2022's C++ build tools, LLVM for Windows, CMake, Ninja, hyperfine, Python 3.14
(for the programs) and Python 3.12 with `psutil` and `pywinpty` (for the session script):

```bash
python3 tools/fetch_photos.py data/photos 100     # anywhere with Pillow; compare sha256 with data/photos.tsv
# put opencv-4.14.0-windows.exe and vips-dev-x64-web-8.18.7.zip in the repo root, then in Git Bash:
tools/setup.sh                                     # unpacks both into tools/, makes venv/, runs build.cmd
python tools/session.py results/<name> 5           # Python 3.12 with psutil + pywinpty
python3 tools/summarize.py results/<name>
```

Wikimedia search results can change over time, so a fresh `fetch_photos.py` run may pick other photos; the sha256
column in `data/photos.tsv` tells you whether you have the same set.

`build.cmd` also writes `cpp/build/shrink_loop.s` (the session copies it into the results folder). It is about 11 MB,
so it is not in the repo.

## Notes
- Test 2 runs both libraries with their default decoding.
- OpenCV is the prebuilt Windows package (`opencv_world`), with its own bundled libjpeg-turbo 3.1.2 and libwebp
  (`opencv_build` in `meta.json`).
- Each program runs one thread on one core.
- The pyvips script ends with `os._exit(0)` after its last file is written, because libvips 8.18 sometimes crashed
  during Python's teardown on Windows.
