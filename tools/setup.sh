#!/bin/bash
# One-time setup on the Windows machine (Git Bash). Expects opencv-4.14.0-windows.exe and
# vips-dev-x64-web-8.18.7.zip in the repo root, and the photos in data/photos (tools/fetch_photos.py) or photos.tar.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d data/photos ] || tar xf photos.tar -C data
[ -d tools/opencv ] || ./opencv-4.14.0-windows.exe -o"$(cygpath -w "$PWD/tools")" -y
[ -d tools/vips-dev-8.18 ] || py -3.12 -c "import zipfile; zipfile.ZipFile('vips-dev-x64-web-8.18.7.zip').extractall('tools')"
[ -d venv ] || py -3.14 -m venv venv
venv/Scripts/python.exe -m pip install --quiet --disable-pip-version-check pillow numpy pyvips
VIPS_BIN="$(cygpath -w "$PWD/tools/vips-dev-8.18/bin")" PATH="$PWD/tools/vips-dev-8.18/bin:$PATH" \
  venv/Scripts/python.exe -c "import os; os.add_dll_directory(os.environ['VIPS_BIN']); import pyvips; print('pyvips', pyvips.__version__, 'libvips', pyvips.version(0), pyvips.version(1), pyvips.version(2))"
cmd //c build.cmd
ls cpp/build/*.exe cpp/build/*.dll
