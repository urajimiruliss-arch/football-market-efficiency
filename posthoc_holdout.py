# -*- coding: utf-8 -*-
"""POST-HOC diagnostics after the single holdout look. They do NOT change the H1–H3 verdicts —
they only explain them, and are explicitly labelled as post-hoc in the report.

(a) Is missingness of Pinnacle closing prices random: share of matches without closing prices by season and league.
(b) Margin by probability band WITHOUT outcomes: how far the market-average closing price sits below Pinnacle's
    fair price, AvgC·p − 1, by band and season. If in recent seasons the average bookmaker cut longshots harder,
    H2's bias would be explained by margin rather than by mispriced probabilities.
(c) Return by band at Pinnacle closing odds versus market-average closing odds — exploration (2019/20–2022/23,
    where AvgC exists) versus holdout. If the bias is also present in Pinnacle's own prices, it matches H1 failing.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as A

EXPL_AVG = ["1920", "2021", "2122", "2223"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    df = A.load(A.EXPLORATION + A.HOLDOUT)
    print("POST-HOC: analysis after the single holdout look; the H1–H3 verdicts are not revisited.\n")

    # (a) missing Pinnacle closing prices
    _, okc = A.odds_matrix(df, ["PSCH", "PSCD", "PSCA"])
    miss = ~okc
    leagues = sorted(df["div"].unique())
    print("(a) share of matches without Pinnacle closing prices, %")
    print(f"{'season':<7} " + " ".join(f"{l:>6}" for l in leagues) + f" {'all':>6}")
    for s in sorted(df["season"].unique()):
        cells = []
        for l in leagues:
            i = ((df["season"] == s) & (df["div"] == l)).to_numpy()
            cells.append(f"{miss[i].mean()*100:>6.1f}" if i.any() else f"{'—':>6}")
        i = (df["season"] == s).to_numpy()
        tag = "  ← holdout" if s in A.HOLDOUT else ""
        print(f"{s:<7} " + " ".join(cells) + f" {miss[i].mean()*100:>6.1f}{tag}")

    # common sample for (b) and (c)
    oc, okc2, sane = A.closing_sane(df)
    oa, oka = A.odds_matrix(df, ["AvgCH", "AvgCD", "AvgCA"])
    keep = sane & oka
    d = df[keep].reset_index(drop=True)
    p, _ = A.fair(oc[keep])
    avg, pin = oa[keep], oc[keep]
    y = A.outcome_matrix(d)
    seasons = d["season"].to_numpy()

    # (b) market-average price relative to Pinnacle's fair price, without outcomes
    print("\n(b) market-average closing price relative to Pinnacle's fair price (AvgC·p − 1), %, by band")
    hdr = [f"{lo:.1f}–{min(hi,1):.1f}" for lo, hi in A.H2_BANDS]
    print(f"{'season':<7} " + " ".join(f"{h:>9}" for h in hdr))
    for s in sorted(set(seasons)):
        i = seasons == s
        cells = []
        for lo, hi in A.H2_BANDS:
            mk = (p[i] >= lo) & (p[i] < hi)
            cells.append(f"{((avg[i] * p[i] - 1)[mk]).mean()*100:>9.2f}" if mk.any() else f"{'—':>9}")
        tag = "  ← holdout" if s in A.HOLDOUT else ""
        print(f"{s:<7} " + " ".join(cells) + tag)

    # (c) return by band: at market-average and at Pinnacle closing prices
    r_avg = np.where(y == 1, avg - 1.0, -1.0)
    r_pin = np.where(y == 1, pin - 1.0, -1.0)
    print("\n(c) return of a back bet by band: market-average closing / Pinnacle closing, %  [outcomes]")
    for label, ss in (("exploration 2019/20–2022/23", EXPL_AVG), ("holdout 2023/24–2025/26", A.HOLDOUT)):
        i = np.isin(seasons, ss)
        print(f"  {label}:")
        for lo, hi in A.H2_BANDS:
            mk = (p[i] >= lo) & (p[i] < hi)
            print(f"    {lo:.1f}–{min(hi,1):.1f}: {r_avg[i][mk].mean()*100:>+7.2f} / {r_pin[i][mk].mean()*100:>+7.2f}  [{mk.sum():,}]")
    print("\n  bottom band (p < 0.20) by holdout season: market-average / Pinnacle, wins against expectation")
    for s in A.HOLDOUT:
        i = seasons == s
        mk = p[i] < 0.20
        wins = int(y[i][mk].sum())
        exp_wins = float(p[i][mk].sum())
        print(f"    {s}: {r_avg[i][mk].mean()*100:>+7.2f} / {r_pin[i][mk].mean()*100:>+7.2f}   wins {wins} against {exp_wins:.1f} expected of {mk.sum()}")


if __name__ == "__main__":
    main()
