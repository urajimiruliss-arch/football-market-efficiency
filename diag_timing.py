# -*- coding: utf-8 -*-
"""Diagnostic for H3's break at 2019/20. Odds only — outcomes are not used.

Artifact hypothesis: after a change in how the source collects data, different bookmakers' "pre-closing" odds
were captured at different times. If Pinnacle's pre-closing price in the file is much closer to the close than
Bet365's, the H3 rule would look ahead (a fresh sharp line against a stale soft price).

Per season (all 10, outcomes are not read):
  - |Pinnacle pre-closing − Pinnacle closing|   (how "early" Pinnacle's price was captured)
  - |Bet365 pre-closing − Pinnacle closing|
  - |Bet365 pre-closing − Pinnacle pre-closing|
  - share of outcomes where Bet365 is ≥ 2% above Pinnacle's pre-closing fair price (how often H3 triggers)
All in fair probabilities (proportional margin removal), in percentage points.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as A


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    df = A.load(A.EXPLORATION + A.HOLDOUT)
    op, okp = A.odds_matrix(df, ["PSH", "PSD", "PSA"])
    oc, okc, sane = A.closing_sane(df)
    ob, okb = A.odds_matrix(df, ["B365H", "B365D", "B365A"])
    keep = okp & okb & sane
    d = df[keep].reset_index(drop=True)
    pp, _ = A.fair(op[keep])
    pc, _ = A.fair(oc[keep])
    pb, _ = A.fair(ob[keep])
    trig = (ob[keep] * pp - 1.0) >= A.H3_EDGE
    print(f"{'season':<7} {'matches':>7} {'|PS−PSC|':>10} {'|B365−PSC|':>11} {'|B365−PS|':>10} {'H3 trig.':>10} {'B365 closer to close':>21}")
    for s in sorted(d["season"].unique()):
        i = (d["season"] == s).to_numpy()
        a = np.abs(pp[i] - pc[i]).mean() * 100
        b = np.abs(pb[i] - pc[i]).mean() * 100
        c = np.abs(pb[i] - pp[i]).mean() * 100
        closer = (np.abs(pb[i] - pc[i]).sum(axis=1) < np.abs(pp[i] - pc[i]).sum(axis=1)).mean() * 100
        tag = "  ← holdout" if s in A.HOLDOUT else ""
        print(f"{s:<7} {i.sum():>7} {a:>9.2f}  {b:>10.2f}  {c:>9.2f}  {trig[i].mean()*100:>8.2f}%  {closer:>19.1f}%{tag}")


if __name__ == "__main__":
    main()
