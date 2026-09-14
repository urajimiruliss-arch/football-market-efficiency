# -*- coding: utf-8 -*-
"""Data quality checks BEFORE analysis. Looks only at the odds themselves and field completeness —
no odds-versus-outcome relationship is computed here, so the pre-registration protocol is not affected.

Per league: matches, duplicates, missing results and required odds, unparseable dates,
Pinnacle closing overround and the number of matches outside [1.00, 1.15].
"""
import collections
import csv
import glob
import os
import statistics as st
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
NEED = {
    "result": ["FTR"],
    "pin_pre": ["PSH", "PSD", "PSA"],
    "pin_close": ["PSCH", "PSCD", "PSCA"],
    "b365_pre": ["B365H", "B365D", "B365A"],
    "avg_close": ["AvgCH", "AvgCD", "AvgCA"],
}


def pos(x):
    try:
        v = float(x)
        return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None


def parse_date(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    by_div = collections.defaultdict(lambda: collections.Counter())
    over = collections.defaultdict(list)
    seen = collections.defaultdict(set)
    for path in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        season, div = os.path.basename(path)[:-4].split("_", 1)
        with open(path, encoding="latin-1", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("HomeTeam"):
                    continue
                c = by_div[div]
                c["matches"] += 1
                key = (row.get("Date"), row.get("HomeTeam"), row.get("AwayTeam"))
                if key in seen[div]:
                    c["duplicates"] += 1
                seen[div].add(key)
                if not parse_date(row.get("Date")):
                    c["bad_date"] += 1
                if row.get("FTR") not in ("H", "D", "A"):
                    c["miss_result"] += 1
                for name, cols in NEED.items():
                    if name == "result":
                        continue
                    if any(pos(row.get(col)) is None for col in cols):
                        c[f"miss_{name}"] += 1
                odds = [pos(row.get(col)) for col in NEED["pin_close"]]
                if all(odds):
                    o = sum(1 / x for x in odds)
                    over[div].append(o)
                    if not (1.00 <= o <= 1.15):
                        c["overround_out"] += 1

    cols = ["matches", "duplicates", "bad_date", "miss_result", "miss_pin_pre", "miss_pin_close",
            "miss_b365_pre", "miss_avg_close", "overround_out"]
    print(f"{'league':<6} " + " ".join(f"{h:>14}" for h in cols) + f" {'Pinnacle closing overround, median':>36}")
    total = collections.Counter()
    for div in sorted(by_div):
        c = by_div[div]
        total.update(c)
        med = st.median(over[div]) if over[div] else float("nan")
        print(f"{div:<6} " + " ".join(f"{c[h]:>14,}" for h in cols) + f" {med:>36.4f}")
    allo = [x for v in over.values() for x in v]
    print(f"{'ALL':<6} " + " ".join(f"{total[h]:>14,}" for h in cols) + f" {st.median(allo):>36.4f}")
    print(f"\nPinnacle closing overround: min {min(allo):.4f}, 1st pct {sorted(allo)[len(allo)//100]:.4f}, "
          f"99th pct {sorted(allo)[len(allo)*99//100]:.4f}, max {max(allo):.4f}")


if __name__ == "__main__":
    main()
