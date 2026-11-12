#!/usr/bin/env python3
"""The C++ vs Python measurement session, natively on Windows (i7-13700F).

Every cell runs under hyperfine (1 warm-up, then RUNS runs, no shell) pinned to one performance core, inside a
pseudo-console so the live screen is recorded as a cast. Rounds alternate which language goes first. After each
recorded cell, one more run logs progress (rows or photos done against time) for the race chart, and the two
popular-library programs run once more with a stopwatch around each stage. A final round runs without the
recorder, to check that recording didn't move the numbers. Outputs are checked every round: test 1's shrunken
photo must be byte-identical across programs; test 2's thumbnails must have the same sizes and close pixels.

usage: python tools/session.py RESULTS_DIR [ROUNDS=5]     (from the repo root, with Python 3.12)
env:   BENCH_PHOTOS (default data/photos), BENCH_NO_GATE=1 (pilot only), HYPERFINE (path to hyperfine.exe)
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

PINNED_CPU = 4
# logical CPU 4 is a performance core (SMT sibling 5); 16-23 are E-cores
HYPERFINE = os.environ.get("HYPERFINE") or str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Links/hyperfine.exe")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PY = str(Path(sys.executable).with_name("python.exe"))
VENV_PY = "venv/Scripts/python.exe"
CPP = "cpp/build"
VIPS_BIN = str(Path("tools/vips-dev-8.18/bin").resolve())
PHOTOS = os.environ.get("BENCH_PHOTOS", "data/photos")
PPM = f"{PHOTOS}/photo-001.ppm"
COLS, ROWS = 52, 4
# libvips and OpenCV would start worker threads; every program gets exactly one thread on the one pinned core.
ENV = {"VIPS_CONCURRENCY": "1", "VIPS_BIN": VIPS_BIN, "PATH": VIPS_BIN + os.pathsep + os.environ["PATH"]}

# (cell, test, side, label shown by hyperfine, runs, argv); {out} is a file for test 1 and a folder for test 2
CELLS = [
    ("py-loop", 1, "py", "Python loop", 10, [VENV_PY, "py/shrink_loop.py", PPM, "{out}"]),
    ("cpp-loop", 1, "cpp", "C++ loop", 10, [f"{CPP}/shrink_loop.exe", PPM, "{out}"]),
    ("py-numpy", 1, "py", "Python NumPy", 10, [VENV_PY, "py/shrink_numpy.py", PPM, "{out}"]),
    ("py-pillow", 2, "py", "Python Pillow", 5, [VENV_PY, "py/thumbs_pillow.py", PHOTOS, "{out}"]),
    ("cpp-opencv", 2, "cpp", "C++ OpenCV", 5, [f"{CPP}/thumbs_opencv.exe", PHOTOS, "{out}"]),
    ("py-pyvips", 2, "py", "Python pyvips", 5, [VENV_PY, "py/thumbs_pyvips.py", PHOTOS, "{out}"]),
    ("cpp-libvips", 2, "cpp", "C++ libvips", 5, [f"{CPP}/thumbs_vips.exe", PHOTOS, "{out}"]),
]
STAGES = {
    "py-pillow": [VENV_PY, "py/thumbs_pillow_stages.py", PHOTOS, "{out}", "{stages}"],
    "cpp-opencv": [f"{CPP}/thumbs_opencv.exe", PHOTOS, "{out}"],
}


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def quiet_gate(max_wait: int = 1800) -> dict:
    """Waits until the pinned core and its sibling are idle (mean under 5%, both under 15%, over 5 s) and the whole
    machine is under 20%; returns that reading. Gives up after max_wait: a busy machine voids the numbers."""
    if os.environ.get("BENCH_NO_GATE") == "1":
        return {"gate": "skipped"}
    waited = 0
    while True:
        per = psutil.cpu_percent(interval=5, percpu=True)
        mine = [per[PINNED_CPU], per[PINNED_CPU + 1]]
        reading = {"cores": mine, "total": round(sum(per) / len(per), 1)}
        if sum(mine) / 2 < 5 and max(mine) < 15 and reading["total"] < 20:
            return reading
        if waited >= max_wait:
            raise RuntimeError(f"machine stayed busy for {max_wait} s: {reading}")
        if waited % 300 == 0:
            log(f"machine busy {reading}, waiting")
        waited += 5


def busy_now() -> list[str]:
    """Names of processes that would void a measurement (renders, browsers, other benchmarks)."""
    bad = {"chrome.exe", "remotion.exe", "ffmpeg.exe", "node.exe", "cargo.exe", "dotnet.exe", "java.exe", "go.exe"}
    return sorted({p.info["name"] for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() in bad})


def pinned(argv: list[str]) -> list[str]:
    return [PY, str(Path(__file__).with_name("pin.py")), str(PINNED_CPU), *argv]


def hyperfine(label: str, runs: int, argv: list[str], export: Path) -> list[str]:
    cmd = subprocess.list2cmdline(argv)
    return [HYPERFINE, "-N", "--warmup", "1", "--runs", str(runs), "-n", label, "--export-json", str(export), cmd]


def wall_times(report: dict) -> list[float]:
    out = []
    for m in report["results"][0]["measurements"]:
        t = m["time_wall_clock"]
        if t["unit"] != "second" or m["exit_code"] != 0:
            raise RuntimeError(f"unexpected measurement {m}")
        out.append(t["value"])
    return out


def order_for(round_no: int) -> list[tuple]:
    """Each test's cells, C++ first in odd rounds and Python first in even ones."""
    cells = []
    for test in (1, 2):
        group = [c for c in CELLS if c[1] == test]
        first = "cpp" if round_no % 2 == 1 else "py"
        cells += sorted(group, key=lambda c: c[2] != first)
    return cells


def digest(out: Path) -> str:
    if not out.is_dir():
        return hashlib.sha256(out.read_bytes()).hexdigest()
    h = hashlib.sha256()
    for f in sorted(out.rglob("*")):
        if f.is_file():
            h.update(f.name.encode() + f.read_bytes())
    return h.hexdigest()


def fill(argv: list[str], **kw: Path) -> list[str]:
    # Forward slashes: hyperfine -N splits the command like a POSIX shell, where a backslash is an escape.
    return [a.format(**{k: v.as_posix() for k, v in kw.items()}) if "{" in a else a for a in argv]


def run_cell(cell: tuple, rdir: Path, record: bool) -> dict:
    name, test, side, label, runs, argv = cell
    out = rdir / (f"{name}.ppm" if test == 1 else f"{name}.out")
    real = fill(argv, out=out)
    export = rdir / f"{name}.json"
    hf = pinned(hyperfine(label, runs, real, export))
    env = dict(os.environ, **ENV)
    gate = quiet_gate()
    t0 = time.time()
    if record:
        cast = rdir / f"{name}.cast"
        rc = subprocess.call([PY, str(Path(__file__).with_name("cast.py")), str(cast), str(COLS), str(ROWS), "--", *hf],
                             creationflags=NO_WINDOW, env=env)
    else:
        rc = subprocess.call(hf, stdout=subprocess.DEVNULL, creationflags=NO_WINDOW, env=env)
    busy = busy_now()
    if rc != 0 or not export.exists():
        direct = subprocess.run(real, check=False, capture_output=True, text=True, creationflags=NO_WINDOW, env=env)
        raise RuntimeError(f"{name}: hyperfine failed ({rc}); direct run rc {direct.returncode}:\n{direct.stderr[-2000:]}")
    result = {"cell": name, "test": test, "side": side, "label": label, "runs_s": wall_times(json.loads(export.read_text())),
              "gate_before": gate, "busy_after": busy, "started": t0, "sha256": digest(out)}
    if record:
        penv = dict(env, PROGRESS_OUT=str(rdir / f"{name}.progress.tsv"))
        subprocess.check_call(pinned(real), env=penv, stdout=subprocess.DEVNULL, creationflags=NO_WINDOW)
        if name in STAGES:
            stages = rdir / f"{name}.stages.tsv"
            sargv = fill(STAGES[name], out=rdir / f"{name}.stages-out", stages=stages)
            senv = dict(env, STAGES_OUT=str(stages))
            s0 = time.perf_counter()
            subprocess.check_call(pinned(sargv), env=senv, stdout=subprocess.DEVNULL, creationflags=NO_WINDOW)
            result["stages_wall_s"] = time.perf_counter() - s0
    return result


def check_round(rdir: Path, rows: list[dict]) -> dict:
    shas = {r["sha256"] for r in rows if r["test"] == 1}
    if len(shas) != 1:
        raise RuntimeError(f"{rdir.name}: test 1 outputs differ")
    dirs = [str(rdir / f"{c[0]}.out") for c in CELLS if c[1] == 2]
    report = json.loads(subprocess.check_output([VENV_PY, "tools/check_thumbs.py", *dirs], text=True, creationflags=NO_WINDOW))
    expected = len(list(Path(PHOTOS).glob("*.jpg")))
    for d, r in report.items():
        if r["files"] != expected or r["max_size_diff_px"] > 1 or r["psnr_min_db"] < 25:
            raise RuntimeError(f"{rdir.name}/{d}: thumbnails differ too much {r}")
    (rdir / "thumbs-check.json").write_text(json.dumps(report, indent=1))
    return report


def versions() -> dict:
    def cmd(*a: str, env: dict | None = None) -> str:
        return subprocess.run(a, check=False, capture_output=True, text=True, creationflags=NO_WINDOW, env=env).stdout.strip()
    env = dict(os.environ, **ENV)
    py = cmd(VENV_PY, "-c", "import os; os.add_dll_directory(os.environ['VIPS_BIN']); import json,sys,PIL,numpy,pyvips; from PIL import features as f; print(json.dumps({"
             "'python': sys.version.split()[0], 'pillow': PIL.__version__, 'numpy': numpy.__version__,"
             "'pyvips': pyvips.__version__, 'libvips': '.'.join(str(pyvips.version(i)) for i in range(3)),"
             "'pillow_libjpeg_turbo': f.version('libjpeg_turbo'), 'pillow_webp': f.version('webp')}))", env=env)
    opencv = cmd(f"{CPP}/opencv_info.exe", env=env)
    return {
        "python": json.loads(py),
        "opencv_build": [l.strip() for l in opencv.splitlines() if any(k in l for k in ("General configuration for OpenCV", "JPEG:", "WEBP:", "Parallel framework"))],
        "libvips_dll": cmd(f"{VIPS_BIN}/vips.exe", "--version", env=env),
        "libvips_config": cmd(f"{VIPS_BIN}/vips.exe", "--vips-config", env=env),
        "clang": cmd(r"C:\Program Files\LLVM\bin\clang++.exe", "--version").splitlines()[0],
        "hyperfine": cmd(HYPERFINE, "--version"),
        "os": platform.platform(),
        "cpu": platform.processor(),
        "power_plan": cmd("powercfg", "/getactivescheme"),
    }


def main() -> int:
    results = Path(sys.argv[1])
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    results.mkdir(parents=True, exist_ok=False)
    photos = sorted(Path(PHOTOS).glob("*.jpg"))
    (results / "meta.json").write_text(json.dumps(
        {"versions": versions(), "rounds": rounds, "pinned_cpu": PINNED_CPU, "photos": PHOTOS,
         "photo_count": len(photos), "photo_bytes": sum(p.stat().st_size for p in photos),
         "ppm_sha256": hashlib.sha256(Path(PPM).read_bytes()).hexdigest(),
         "photos_sha256": digest(Path(PHOTOS)), "started": time.ctime()}, indent=2))
    shutil.copy(f"{CPP}/shrink_loop.s", results / "shrink_loop.s")
    (results / "why_py.json").write_text(subprocess.check_output([VENV_PY, "tools/why_py.py"], text=True, creationflags=NO_WINDOW))
    log("waiting for a quiet machine (up to 1 h)")
    quiet_gate(max_wait=3600)
    for r in range(1, rounds + 2):
        record = r <= rounds
        rdir = results / (f"round{r}" if record else "plain")
        rdir.mkdir()
        log(f"round {r} ({'recorded' if record else 'plain'})")
        rows = []
        for cell in order_for(r):
            res = run_cell(cell, rdir, record)
            res["round"] = r if record else "plain"
            rows.append(res)
            med = sorted(res["runs_s"])[len(res["runs_s"]) // 2]
            log(f"  {res['cell']:20s} median {med:.3f} s{'  BUSY ' + ','.join(res['busy_after']) if res['busy_after'] else ''}")
            with open(results / "runs.jsonl", "a") as f:
                f.write(json.dumps(res) + "\n")
        log(f"  thumbs {json.dumps(check_round(rdir, rows))}")
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
