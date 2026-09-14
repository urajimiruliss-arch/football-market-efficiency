# -*- coding: utf-8 -*-
"""Runs the numbered .sql files against data/football.sqlite and cross-checks the SQL answers
against the numbers analysis.py published in outputs/<split>/results.json.

This is a reproduction of point estimates (no new hypotheses, no bootstrap): the holdout is only re-described.

Usage:
    python sql/build_db.py
    python sql/run_queries.py            # prints every query result, then the cross-check summary
"""
import glob
import json
import math
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
DB = os.path.join(BASE, "data", "football.sqlite")
SPLITS = ["exploration", "holdout"]
checks, failures = 0, []


def query(con, path, split=None):
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    cur = con.execute(sql, {"split": split} if ":split" in sql else {})
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def show(title, rows):
    print(f"\n{title}")
    if not rows:
        print("  (no rows)")
        return
    cells = [[(f"{v:.4f}".rstrip("0").rstrip(".") or "0") if isinstance(v, float) else str(v) for v in r.values()] for r in rows]
    cols = list(rows[0])
    w = [max(len(c), *(len(x[i]) for x in cells)) for i, c in enumerate(cols)]
    print("  " + "  ".join(c.rjust(w[i]) for i, c in enumerate(cols)))
    for x in cells:
        print("  " + "  ".join(v.rjust(w[i]) for i, v in enumerate(x)))


def same(label, sql_value, py_value):
    global checks
    checks += 1
    if isinstance(py_value, float) or isinstance(sql_value, float):
        ok = sql_value is not None and py_value is not None and math.isclose(sql_value, py_value, rel_tol=1e-9, abs_tol=1e-12)
    else:
        ok = sql_value == py_value
    if not ok:
        failures.append(f"{label}: SQL {sql_value!r} vs Python {py_value!r}")


def cross_check(split, res, q):
    for r in q["02"]:
        ref = res["H2"]["band_mean_return"][r["band"]]
        same(f"{split} H2 {r['band']} n", r["n"], ref["n"])
        same(f"{split} H2 {r['band']} mean", r["mean_return"], ref["mean"])
    same(f"{split} H2 top-bottom", q["02"][0]["top_minus_bottom"], res["H2"]["top_minus_bottom"])

    same(f"{split} H1 brier", q["03"][0]["brier_all"], res["H1"]["brier"])

    for r in q["04"]:
        ref = res["D1"][r["season"]]
        same(f"{split} D1 {r['season']} matches", r["matches"], ref["matches"])
        same(f"{split} D1 {r['season']} home_rate", r["home_rate"], ref["home_rate"])
        same(f"{split} D1 {r['season']} mean_p_home", r["mean_p_home"], ref["mean_p_home"])

    h3 = res["H3"]
    for r in q["05"]:
        if r["season"] == "all":
            same(f"{split} H3 bets", r["bets"], h3["bets"])
            same(f"{split} H3 roi", r["roi"], h3["roi"])
            same(f"{split} H3 roi odds<10", r["roi_odds_lt_10"], h3["robustness"]["roi_excluding_odds_ge_10"])
            same(f"{split} H3 winners odds>=10", r["winners_odds_ge_10"], h3["robustness"]["winners_odds_ge_10_observed"])
        else:
            same(f"{split} H3 {r['season']} bets", r["bets"], h3["by_season"][r["season"]]["bets"])
            same(f"{split} H3 {r['season']} roi", r["roi"], h3["by_season"][r["season"]]["roi"])
    eq = q["06"][0]
    same(f"{split} H3 equity bets", eq["bets"], h3["bets"])
    same(f"{split} H3 final P&L = ROI x bets", eq["final_pnl_units"], h3["roi"] * h3["bets"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.exists(DB):
        sys.exit("data/football.sqlite not found: run python sql/build_db.py first")
    con = sqlite3.connect(DB)
    files = {os.path.basename(p)[:2]: p for p in sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*.sql")))}

    show(os.path.basename(files["01"]), query(con, files["01"]))
    for split in SPLITS:
        q = {k: query(con, p, split) for k, p in files.items() if k != "01"}
        for k in q:
            show(f"{os.path.basename(files[k])}  [{split}]", q[k])
        with open(os.path.join(BASE, "outputs", split, "results.json"), encoding="utf-8") as f:
            cross_check(split, json.load(f), q)

    print(f"\ncross-check against analysis.py results.json: {checks - len(failures)}/{checks} match")
    for line in failures:
        print("  MISMATCH", line)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
