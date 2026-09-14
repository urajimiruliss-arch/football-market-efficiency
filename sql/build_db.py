# -*- coding: utf-8 -*-
"""Loads the raw football-data.co.uk CSVs into data/football.sqlite (standard library only).

Row filtering mirrors analysis.load(): rows without HomeTeam are dropped, duplicates on
(Date, HomeTeam, AwayTeam, league) keep the first occurrence, non-numeric odds become NULL.

Usage:
    python sql/build_db.py
"""
import csv
import glob
import math
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
RAW = os.path.join(BASE, "data", "raw")
DB = os.path.join(BASE, "data", "football.sqlite")

sys.path.insert(0, BASE)
from analysis import EXPLORATION, HOLDOUT  # noqa: E402  single source of truth for the split

ODDS = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA", "B365H", "B365D", "B365A", "AvgCH", "AvgCD", "AvgCA"]


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def iso_date(s):
    try:
        d, m, y = s.strip().split("/")
    except (AttributeError, ValueError):
        return None
    y = int(y) + 2000 if len(y) == 2 else int(y)
    return f"{y:04d}-{int(m):02d}-{int(d):02d}"


def main():
    split_of = {s: "exploration" for s in EXPLORATION} | {s: "holdout" for s in HOLDOUT}
    if os.path.exists(DB):
        os.remove(DB)                       # generated file: always rebuilt from the raw CSVs
    con = sqlite3.connect(DB)
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())

    rows, seen = [], set()
    for path in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        season, div = os.path.basename(path)[:-4].split("_", 1)
        if season not in split_of:
            continue
        with open(path, encoding="latin-1", newline="") as f:
            for r in csv.DictReader(f):
                if not (r.get("HomeTeam") or "").strip():
                    continue
                key = (r.get("Date"), r["HomeTeam"], r.get("AwayTeam"), div)
                if key in seen:
                    continue
                seen.add(key)
                rows.append((season, split_of[season], div, iso_date(r.get("Date")), r["HomeTeam"], r.get("AwayTeam"),
                             (r.get("FTR") or None), *[num(r.get(c)) for c in ODDS]))

    con.executemany(
        "INSERT INTO matches (season, split, div, match_date, home_team, away_team, ftr,"
        " psh, psd, psa, psch, pscd, psca, b365h, b365d, b365a, avgch, avgcd, avgca)"
        " VALUES (?,?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?)", rows)
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    print(f"{DB}: {n:,} matches, sqlite {sqlite3.sqlite_version}")
    con.close()


if __name__ == "__main__":
    main()
