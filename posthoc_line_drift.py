# -*- coding: utf-8 -*-
"""POST-HOC check of a claim from J.R. Miller's betting book: "lines move towards the favourite before kick-off,
so back favourites early and underdogs late". Not part of PREREGISTRATION.md; everything below is exploratory.

Specification (fixed before the first run):
  Books      Pinnacle pre-closing -> closing (all seasons); Bet365 and market average pre-closing -> closing (2019/20+).
  Sanity     all three prices > 1; overround 1.00-1.15 for Pinnacle, 1.00-1.25 for Bet365 / average, at both times.
  Fair p     proportional margin removal.
  Favourite  home or away outcome with the higher PRE-closing fair probability (draw never the favourite).
             Selecting on the noisy pre-closing price biases drift AGAINST the claim (regression to the mean);
             the closing-based definition is reported as a sensitivity check and is biased the other way.
  Metrics    1) mean change of the favourite's fair probability, close - pre (pp)
             2) among matches where it moved by >= 0.5 pp: share where the favourite shortened (claim: ~75%)
             3) paired per-match return difference of a 1-unit back bet: favourite pre - close ("early is better")
                and underdog close - pre ("late is better"); raw odds, commission-free
  Split      exploration 2016/17-2022/23 and 2023/24-2025/26 reported separately; a direction counts only if both agree.
  Inference  matches are independent -> normal approximation, 99% intervals; Wilson interval for shares.

Usage:
    python posthoc_line_drift.py
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "outputs", "posthoc")
EXPLORATION = ["1617", "1718", "1819", "1920", "2021", "2122", "2223"]
LATER = ["2324", "2425", "2526"]
Z99 = 2.576
MOVE_PP = 0.5
BOOKS = {
    "pinnacle": (["PSH", "PSD", "PSA"], ["PSCH", "PSCD", "PSCA"], (1.00, 1.15)),
    "bet365": (["B365H", "B365D", "B365A"], ["B365CH", "B365CD", "B365CA"], (1.00, 1.25)),
    "average": (["AvgH", "AvgD", "AvgA"], ["AvgCH", "AvgCD", "AvgCA"], (1.00, 1.25)),
}


def load():
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        season, div = os.path.basename(path)[:-4].split("_", 1)
        df = pd.read_csv(path, encoding="latin-1")
        df = df[df["HomeTeam"].notna()].copy()
        df["season"], df["div"] = season, div
        frames.append(df)
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam", "div"])
    for cols_pre, cols_close, _ in BOOKS.values():
        for c in cols_pre + cols_close:
            df[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
    return df.reset_index(drop=True)


def fair(df, cols, rng):
    o = df[cols].to_numpy(dtype=float)
    ok = np.all(np.isfinite(o) & (o > 1.0), axis=1)
    inv = 1.0 / np.where(ok[:, None], o, 2.0)
    over = inv.sum(axis=1)
    ok &= (over >= rng[0]) & (over <= rng[1])
    return o, inv / over[:, None], ok


def mean_ci(x):
    x = np.asarray(x, dtype=float)
    m, se = float(x.mean()), float(x.std(ddof=1) / math.sqrt(len(x)))
    return m, (m - Z99 * se, m + Z99 * se)


def wilson(k, n):
    if n == 0:
        return float("nan"), (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z99 ** 2 / n
    c = (p + Z99 ** 2 / (2 * n)) / d
    h = Z99 * math.sqrt(p * (1 - p) / n + Z99 ** 2 / (4 * n * n)) / d
    return p, (c - h, c + h)


def analyse(df, book):
    cols_pre, cols_close, rng = BOOKS[book]
    o_pre, p_pre, ok_pre = fair(df, cols_pre, rng)
    o_cl, p_cl, ok_cl = fair(df, cols_close, rng)
    keep = ok_pre & ok_cl & (p_pre[:, 0] != p_pre[:, 2]) & df["FTR"].isin(["H", "D", "A"]).to_numpy()
    if keep.sum() < 200:
        return None
    d = df[keep]
    o_pre, p_pre, o_cl, p_cl = o_pre[keep], p_pre[keep], o_cl[keep], p_cl[keep]
    idx = np.arange(len(d))
    fav = np.where(p_pre[:, 0] > p_pre[:, 2], 0, 2)           # 0 = home, 2 = away
    dog = 2 - fav
    won = {k: (d["FTR"].to_numpy() == k) for k in ("H", "D", "A")}
    won_by_col = np.stack([won["H"], won["D"], won["A"]], axis=1)

    dp = (p_cl[idx, fav] - p_pre[idx, fav]) * 100
    moved = np.abs(dp) >= MOVE_PP
    k_short = int((dp[moved] > 0).sum())

    fav_close_def = np.where(p_cl[:, 0] > p_cl[:, 2], 0, 2)
    dp_close_def = (p_cl[idx, fav_close_def] - p_pre[idx, fav_close_def]) * 100

    def ret(odds, side):
        w = won_by_col[idx, side]
        return np.where(w, odds[idx, side] - 1.0, -1.0)

    fav_pre, fav_cl = ret(o_pre, fav), ret(o_cl, fav)
    dog_pre, dog_cl = ret(o_pre, dog), ret(o_cl, dog)
    share, share_ci = wilson(k_short, int(moved.sum()))
    return {
        "matches": int(len(d)),
        "fav_prob_change_pp": mean_ci(dp),
        "moved_matches": int(moved.sum()),
        "share_moved_towards_favourite": (share, share_ci),
        "fav_prob_change_pp_closing_definition": mean_ci(dp_close_def),
        "fav_return_pre": mean_ci(fav_pre), "fav_return_close": mean_ci(fav_cl),
        "fav_early_minus_late": mean_ci(fav_pre - fav_cl),
        "dog_return_pre": mean_ci(dog_pre), "dog_return_close": mean_ci(dog_cl),
        "dog_late_minus_early": mean_ci(dog_cl - dog_pre),
    }


def fmt(mci, scale=1.0, unit=""):
    m, (lo, hi) = mci
    return f"{m*scale:+.2f}{unit} [{lo*scale:+.2f}, {hi*scale:+.2f}]"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    df = load()
    results = {}
    for book in BOOKS:
        for name, seasons in (("exploration", EXPLORATION), ("later", LATER)):
            r = analyse(df[df["season"].isin(seasons)], book)
            results[f"{book}/{name}"] = r
            if r is None:
                print(f"\n{book} {name}: not enough data")
                continue
            s, (slo, shi) = r["share_moved_towards_favourite"]
            print(f"\n== {book} · {name} · {r['matches']:,} matches")
            print(f"  favourite fair p change, close - pre:  {fmt(r['fav_prob_change_pp'], unit=' pp')}"
                  f"   (closing-defined favourite: {fmt(r['fav_prob_change_pp_closing_definition'], unit=' pp')})")
            print(f"  moved >= {MOVE_PP} pp: {r['moved_matches']:,} matches, towards favourite {s*100:.1f}% [{slo*100:.1f}, {shi*100:.1f}]"
                  f"   (Miller: ~75%)")
            print(f"  favourite return: pre {fmt(r['fav_return_pre'], 100, '%')}  close {fmt(r['fav_return_close'], 100, '%')}"
                  f"  early - late {fmt(r['fav_early_minus_late'], 100, ' pp')}")
            print(f"  underdog  return: pre {fmt(r['dog_return_pre'], 100, '%')}  close {fmt(r['dog_return_close'], 100, '%')}"
                  f"  late - early {fmt(r['dog_late_minus_early'], 100, ' pp')}")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "line_drift.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nresults: {os.path.join(OUT, 'line_drift.json')}")


if __name__ == "__main__":
    main()
