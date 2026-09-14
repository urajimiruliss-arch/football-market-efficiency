# -*- coding: utf-8 -*-
"""Decomposition of H3 on exploration seasons: is the "2019/20 break" carried by a handful of long-odds winners?

Exploration seasons only (2016/17–2022/23); the holdout is not read.
The timing check (diag_timing.py) rejected a collection artifact: the relation between Pinnacle and Bet365
pre-closing prices is the same in every season. The remaining candidate is variance: return σ is 2.59 stakes
and the selection leans towards high odds.

For the periods "before 2019/20" and "from 2019/20":
  - bets, ROI, ROI without the 5 largest wins, ROI without bets at odds ≥ 10;
  - odds distribution and the contribution of winners at odds ≥ 10;
  - ROI by odds band.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as A

PRE = ["1617", "1718", "1819"]
POST = ["1920", "2021", "2122", "2223"]
BANDS = [(1.0, 2.5), (2.5, 5.0), (5.0, 10.0), (10.0, 1e9)]


def bets(df):
    op, okp = A.odds_matrix(df, ["PSH", "PSD", "PSA"])
    ob, okb = A.odds_matrix(df, ["B365H", "B365D", "B365A"])
    oc, okc, sane = A.closing_sane(df)
    keep = okp & okb & ~(okc & ~sane)
    d = df[keep].reset_index(drop=True)
    ps, _ = A.fair(op[keep])
    b365 = ob[keep]
    y = A.outcome_matrix(d)
    sel = (b365 * ps - 1.0) >= A.H3_EDGE
    rows = []
    seasons = d["season"].to_numpy()
    for i, j in zip(*np.nonzero(sel)):
        odds = b365[i, j]
        rows.append((seasons[i], odds, y[i, j], odds - 1.0 if y[i, j] else -1.0))
    return rows


def report(label, rows):
    if not rows:
        print(f"\n{label}: no bets"); return
    odds = np.array([r[1] for r in rows]); won = np.array([r[2] for r in rows]); ret = np.array([r[3] for r in rows])
    n = len(ret)
    top5 = np.sort(ret)[-5:]
    roi_wo_top5 = (ret.sum() - top5.sum()) / (n - 5) if n > 5 else float("nan")
    lo = odds < 10
    big_win = won.astype(bool) & (odds >= 10)
    print(f"\n{label}: bets {n}, ROI {ret.mean()*100:+.1f}%")
    print(f"   without the 5 largest wins: {roi_wo_top5*100:+.1f}%   (those 5 made {top5.sum():+.1f} units of profit over {n} bets)")
    print(f"   without bets at odds ≥ 10:  {ret[lo].mean()*100:+.1f}%  ({lo.sum()} bets left)")
    print(f"   odds: median {np.median(odds):.2f}, share ≥5: {(odds>=5).mean()*100:.0f}%, share ≥10: {(odds>=10).mean()*100:.0f}%")
    print(f"   winners at odds ≥ 10: {big_win.sum()}, their profit {ret[big_win].sum():+.1f} units of a total {ret.sum():+.1f}")
    for a, b in BANDS:
        m = (odds >= a) & (odds < b)
        if m.any():
            print(f"   odds {a:>4.1f}–{('∞' if b > 1e8 else f'{b:.1f}'):<4}: bets {m.sum():>4}, won {int(won[m].sum()):>3}, ROI {ret[m].mean()*100:+7.1f}%")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = bets(A.load(A.EXPLORATION))
    report("Before 2019/20 (2016/17–2018/19)", [r for r in rows if r[0] in PRE])
    report("From 2019/20 (2019/20–2022/23)", [r for r in rows if r[0] in POST])


if __name__ == "__main__":
    main()
