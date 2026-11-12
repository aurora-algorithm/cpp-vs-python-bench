#!/usr/bin/env python3
"""Medians of one session: every cell over all recorded runs, the plain round, and the stage split.

usage: python3 tools/summarize.py results/<session>   -> results/<session>/summary.json
Stage seconds are summed over all photos per round; "other" is the stage run's wall time minus the three stages
(interpreter start, imports, file listing). Each is the median over the recorded rounds.
"""

import json
import statistics
import sys
from pathlib import Path

STAGE_CELLS = ("py-pillow", "cpp-opencv")


def load_runs(session: Path) -> list[dict]:
    lines = (session / "runs.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def cell_stats(rows: list[dict]) -> dict:
    recorded = [r for r in rows if r["round"] != "plain"]
    plain = [r for r in rows if r["round"] == "plain"]
    cells = {}
    for name in dict.fromkeys(r["cell"] for r in recorded):
        mine = [r for r in recorded if r["cell"] == name]
        runs = [t for r in mine for t in r["runs_s"]]
        plain_runs = [t for r in plain if r["cell"] == name for t in r["runs_s"]]
        median = statistics.median(runs)
        plain_median = statistics.median(plain_runs) if plain_runs else None
        cells[name] = {
            "label": mine[0]["label"],
            "test": mine[0]["test"],
            "median_s": round(median, 4),
            "min_s": round(min(runs), 4),
            "max_s": round(max(runs), 4),
            "runs": len(runs),
            "plain_median_s": round(plain_median, 4) if plain_median else None,
            "plain_vs_recorded": round(plain_median / median - 1, 4) if plain_median else None,
            "busy_after": sorted({b for r in mine for b in r.get("busy_after", [])}),
        }
    return cells


def stage_sums(session: Path, row: dict) -> dict:
    tsv = session / f"round{row['round']}" / f"{row['cell']}.stages.tsv"
    lines = [line.split("\t") for line in tsv.read_text().splitlines()[1:] if line]
    sums = {k: sum(float(line[i]) for line in lines) for i, k in ((1, "decode"), (2, "resize"), (3, "encode"))}
    sums["other"] = row["stages_wall_s"] - sum(sums.values())
    sums["wall"] = row["stages_wall_s"]
    return sums


def stages(session: Path, rows: list[dict]) -> dict:
    out = {}
    for name in STAGE_CELLS:
        per_round = [
            stage_sums(session, r) for r in rows if r["cell"] == name and r["round"] != "plain" and "stages_wall_s" in r
        ]
        if not per_round:
            sys.exit(f"no stage runs for {name}")
        out[name] = {k: round(statistics.median(p[k] for p in per_round), 3) for k in per_round[0]}
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    session = Path(sys.argv[1])
    rows = load_runs(session)
    if not rows:
        sys.exit(f"{session}: no runs")
    cells = cell_stats(rows)
    summary = {"session": session.name, "cells": cells, "stages_s": stages(session, rows)}
    (session / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    for name, c in cells.items():
        print(f"{name:12s} {c['median_s']:.3f} s  n={c['runs']}  plain {c['plain_vs_recorded']:+.1%}")


if __name__ == "__main__":
    main()
