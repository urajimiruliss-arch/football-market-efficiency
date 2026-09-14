# -*- coding: utf-8 -*-
"""Analysis strictly per PREREGISTRATION.md. No tunable thresholds — everything is a constant from the spec.

Usage:
    python analysis.py exploration
    python analysis.py holdout --one-look      # ONCE: writes the lock file outputs/holdout/LOCK

H1  Pinnacle closing-line calibration: logistic regression y ~ a + b·logit(p); 99% bootstrap CI contains b=1 and a=0
H2  favourite–longshot bias at market-average closing odds: top band minus bottom band > 0
H3  Bet365 pre-closing ≥ 2% above Pinnacle's pre-closing fair price → ROI > 0
D1  descriptive: home-win rate vs mean Pinnacle probability by season (empty-stadium season 2020/21)
Uncertainty: bootstrap over MATCHES (outcomes within a match are dependent), 10,000 resamples.
"""
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "outputs")

EXPLORATION = ["1617", "1718", "1819", "1920", "2021", "2122", "2223"]
HOLDOUT = ["2324", "2425", "2526"]
ALPHA = 0.01
N_BOOT = 10_000
CHUNK = 100
SEED = 20260913
OVERROUND_RANGE = (1.00, 1.15)
H2_BANDS = [(0.00, 0.20), (0.20, 0.40), (0.40, 0.60), (0.60, 1.0000001)]
H3_EDGE = 0.02
OUTCOMES = ["H", "D", "A"]

rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------- data
def load(seasons):
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        season, div = os.path.basename(path)[:-4].split("_", 1)
        if season not in seasons:
            continue
        df = pd.read_csv(path, encoding="latin-1")
        df = df[df["HomeTeam"].notna()].copy()
        df["season"], df["div"] = season, div
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["Date", "HomeTeam", "AwayTeam", "div"])
    cols = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA", "B365H", "B365D", "B365A", "AvgCH", "AvgCD", "AvgCA"]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
    return df.reset_index(drop=True)


def odds_matrix(df, prefix_cols):
    o = df[prefix_cols].to_numpy(dtype=float)
    ok = np.all(np.isfinite(o) & (o > 1.0), axis=1)
    return o, ok


def fair(o):
    inv = 1.0 / o
    return inv / inv.sum(axis=1, keepdims=True), inv.sum(axis=1)


def outcome_matrix(df):
    return np.stack([(df["FTR"] == k).to_numpy(dtype=float) for k in OUTCOMES], axis=1)


def closing_sane(df):
    o, ok = odds_matrix(df, ["PSCH", "PSCD", "PSCA"])
    over = np.where(ok, (1.0 / np.where(ok[:, None], o, 2.0)).sum(axis=1), np.nan)   # per-match mask broadcast to 3 outcomes
    sane = ok & (over >= OVERROUND_RANGE[0]) & (over <= OVERROUND_RANGE[1])
    return o, ok, sane


def boot_weights(m):
    """Yields match weights for the bootstrap: (CHUNK, m) matrices of multinomial counts."""
    done = 0
    while done < N_BOOT:
        c = min(CHUNK, N_BOOT - done)
        yield rng.multinomial(m, np.full(m, 1.0 / m), size=c).astype(float)
        done += c


def pct(a, lo, hi):
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


# ---------------------------------------------------------------- H1
def logit_fit(x, y, w, iters=8):
    """Weighted logistic regression y ~ a + b·x by Newton's method. w: (N,) or (C, N)."""
    two_d = w.ndim == 2
    W = w if two_d else w[None, :]
    a = np.zeros(W.shape[0]); b = np.ones(W.shape[0])
    for _ in range(iters):
        eta = a[:, None] + b[:, None] * x[None, :]
        mu = 1.0 / (1.0 + np.exp(-eta))
        r = W * (y[None, :] - mu)
        v = W * mu * (1.0 - mu)
        g0, g1 = r.sum(1), (r * x[None, :]).sum(1)
        h00, h01, h11 = v.sum(1), (v * x[None, :]).sum(1), (v * x[None, :] ** 2).sum(1)
        det = h00 * h11 - h01 ** 2
        a = a + (h11 * g0 - h01 * g1) / det
        b = b + (h00 * g1 - h01 * g0) / det
    return (a, b) if two_d else (float(a[0]), float(b[0]))


def h1(df):
    o, ok, sane = closing_sane(df)
    d = df[sane].reset_index(drop=True)
    p, _ = fair(o[sane])
    y = outcome_matrix(d)
    m = len(d)
    x = np.log(p / (1 - p)).ravel()
    yy = y.ravel()
    a, b = logit_fit(x, yy, np.ones(m * 3))
    ab, bb = [], []
    diffs = {k: [] for k in OUTCOMES}
    for W in boot_weights(m):
        W3 = np.repeat(W, 3, axis=1)
        aa, bbb = logit_fit(x, yy, W3)
        ab.append(aa); bb.append(bbb)
        tot = W.sum(1)
        for j, k in enumerate(OUTCOMES):
            diffs[k].append((W * (y[:, j] - p[:, j])).sum(1) / tot)
    ab, bb = np.concatenate(ab), np.concatenate(bb)
    ci_a, ci_b = pct(ab, 0.5, 99.5), pct(bb, 0.5, 99.5)
    pflat = p.ravel()
    res = {
        "matches": m, "excluded_overround_or_missing": int((~sane).sum()),
        "a": a, "b": b, "ci99_a": ci_a, "ci99_b": ci_b,
        "claim_calibrated": bool(ci_a[0] <= 0 <= ci_a[1] and ci_b[0] <= 1 <= ci_b[1]),
        "brier": float(np.mean((pflat - yy) ** 2)),
        "log_loss": float(-np.mean(yy * np.log(pflat) + (1 - yy) * np.log(1 - pflat))),
        "by_outcome": {k: {"observed": float(y[:, j].mean()), "mean_p": float(p[:, j].mean()),
                           "ci99_observed_minus_p": pct(np.concatenate(diffs[k]), 0.5, 99.5)}
                       for j, k in enumerate(OUTCOMES)},
        "slope_by_league": {}, "slope_by_season": {},
    }
    for key, col in (("slope_by_league", "div"), ("slope_by_season", "season")):
        for g in sorted(d[col].unique()):
            idx = (d[col] == g).to_numpy()
            xs = np.log(p[idx] / (1 - p[idx])).ravel()
            res[key][g] = logit_fit(xs, y[idx].ravel(), np.ones(idx.sum() * 3))[1]
    # calibration chart data
    bins = np.linspace(0, 1, 21)
    cen, obs, cnt = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mk = (pflat >= lo) & (pflat < hi)
        if mk.sum() >= 50:
            cen.append(pflat[mk].mean()); obs.append(yy[mk].mean()); cnt.append(int(mk.sum()))
    return res, (cen, obs, cnt)


# ---------------------------------------------------------------- H2
def h2(df):
    oc, okc, sane = closing_sane(df)
    oa, oka = odds_matrix(df, ["AvgCH", "AvgCD", "AvgCA"])
    keep = sane & oka
    d = df[keep].reset_index(drop=True)
    p, _ = fair(oc[keep])
    oav = oa[keep]
    y = outcome_matrix(d)
    r = np.where(y == 1, oav - 1.0, -1.0)
    m = len(d)
    masks = [((p >= lo) & (p < hi)) for lo, hi in H2_BANDS]
    means = [float(r[mk].mean()) if mk.any() else float("nan") for mk in masks]
    stat = means[-1] - means[0]
    boot, band_boot = [], [[] for _ in H2_BANDS]
    for W in boot_weights(m):
        vals = []
        for i, mk in enumerate(masks):
            num = (W[:, :, None] * (r * mk)[None, :, :]).sum((1, 2))
            den = (W[:, :, None] * mk[None, :, :]).sum((1, 2))
            v = num / den
            band_boot[i].append(v); vals.append(v)
        boot.append(vals[-1] - vals[0])
    boot = np.concatenate(boot)
    res = {
        "matches": m, "seasons": sorted(d["season"].unique().tolist()),
        "band_mean_return": {f"{lo:.2f}-{min(hi,1):.2f}": {"mean": mu, "n": int(mk.sum()),
                             "ci99": pct(np.concatenate(band_boot[i]), 0.5, 99.5)}
                             for i, ((lo, hi), mk, mu) in enumerate(zip(H2_BANDS, masks, means))},
        "top_minus_bottom": stat, "ci99": pct(boot, 0.5, 99.5),
        "p_one_sided": float(np.mean(boot <= 0)),
        "by_league": {}, "by_season": {},
    }
    res["claim_flb"] = bool(res["p_one_sided"] < ALPHA and stat > 0)
    for key, col in (("by_league", "div"), ("by_season", "season")):
        for g in sorted(d[col].unique()):
            idx = (d[col] == g).to_numpy()
            rt, rb = r[idx][masks[-1][idx]], r[idx][masks[0][idx]]
            res[key][g] = float(rt.mean() - rb.mean()) if len(rt) and len(rb) else None
    return res, means


# ---------------------------------------------------------------- H3
def h3(df):
    op, okp = odds_matrix(df, ["PSH", "PSD", "PSA"])
    ob, okb = odds_matrix(df, ["B365H", "B365D", "B365A"])
    oc, okc, sane = closing_sane(df)
    bad_close = okc & ~sane                      # closing prices present but overround out of range — match excluded
    keep = okp & okb & ~bad_close
    d = df[keep].reset_index(drop=True)
    ps, _ = fair(op[keep])
    b365 = ob[keep]
    y = outcome_matrix(d)
    edge = b365 * ps - 1.0
    bet = edge >= H3_EDGE
    ret = np.where(y == 1, b365 - 1.0, -1.0)
    m = len(d)
    n_bets = int(bet.sum())
    roi = float(ret[bet].mean()) if n_bets else float("nan")
    boot = []
    for W in boot_weights(m):
        num = (W[:, :, None] * (ret * bet)[None, :, :]).sum((1, 2))
        den = (W[:, :, None] * bet[None, :, :]).sum((1, 2))
        boot.append(num / den)
    boot = np.concatenate(boot)
    okc_k, sane_k = okc[keep], sane[keep]
    pc, _ = fair(np.where(sane_k[:, None], oc[keep], 2.0))
    clv_mask = bet & sane_k[:, None]
    clv = float(((b365 * pc - 1.0) > 0)[clv_mask].mean()) if clv_mask.any() else float("nan")
    sd = float(ret[bet].std()) if n_bets else float("nan")
    z = 2.326 + 0.842
    res = {
        "matches": m, "bets": n_bets, "roi": roi, "ci99": pct(boot, 0.5, 99.5),
        "p_one_sided": float(np.mean(boot <= 0)), "sd_return": sd,
        "bets_needed_for_2pct_roi_power80": float((z * sd / 0.02) ** 2) if n_bets else None,
        "clv_share_beating_pinnacle_close": clv,
        "by_season": {}, "by_league": {},
    }
    res["claim_positive_roi"] = bool(res["p_one_sided"] < ALPHA and roi > 0)
    # Addendum 2: robustness to long-odds winners (declared before the holdout was opened)
    odds_b, ret_b, won_b, p_b = b365[bet], ret[bet], (y == 1)[bet], ps[bet]
    long = odds_b >= 10
    top5 = np.sort(ret_b)[-5:] if n_bets > 5 else ret_b
    res["robustness"] = {
        "roi_excluding_odds_ge_10": float(ret_b[~long].mean()) if (~long).any() else None,
        "bets_odds_lt_10": int((~long).sum()),
        "roi_excluding_top5_returns": float((ret_b.sum() - top5.sum()) / (n_bets - 5)) if n_bets > 5 else None,
        "winners_odds_ge_10_observed": int((won_b & long).sum()),
        "winners_odds_ge_10_expected": float(p_b[long].sum()),
    }
    ex10 = res["robustness"]["roi_excluding_odds_ge_10"]
    res["claim_edge_robust"] = bool(res["claim_positive_roi"] and ex10 is not None and ex10 > 0)
    for key, col in (("by_season", "season"), ("by_league", "div")):
        for g in sorted(d[col].unique()):
            idx = (d[col] == g).to_numpy()
            bb = bet[idx]
            res[key][g] = {"bets": int(bb.sum()), "roi": float(ret[idx][bb].mean()) if bb.any() else None}
    return res


# ---------------------------------------------------------------- D1
def d1(df):
    o, ok, sane = closing_sane(df)
    d = df[sane].reset_index(drop=True)
    p, _ = fair(o[sane])
    home = (d["FTR"] == "H").to_numpy(dtype=float)
    out = {}
    for s in sorted(d["season"].unique()):
        idx = (d["season"] == s).to_numpy()
        h, ph = home[idx], p[idx, 0]
        m = len(h)
        boots = []
        for W in boot_weights(m):
            boots.append((W * (h - ph)).sum(1) / W.sum(1))
            if len(boots) * CHUNK >= 2000:
                break
        out[s] = {"matches": m, "home_rate": float(h.mean()), "mean_p_home": float(ph.mean()),
                  "diff": float((h - ph).mean()), "ci95_diff": pct(np.concatenate(boots), 2.5, 97.5)}
    return out


# ---------------------------------------------------------------- report
def figures(outdir, cal, h2means, h3res, d1res):
    cen, obs, cnt = cal
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot([0, 1], [0, 1], color="#999", lw=1, ls="--", label="perfect calibration")
    ax.scatter(cen, obs, s=[max(8, c / 40) for c in cnt], color="#1f5fa8", label="observed (bins, size ∝ n)")
    ax.set_xlabel("Pinnacle closing fair probability"); ax.set_ylabel("observed frequency")
    ax.set_title("H1 — calibration of Pinnacle's closing line"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "h1_calibration.png"), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    labels = [f"{lo:.1f}–{min(hi,1):.1f}" for lo, hi in H2_BANDS]
    ax.bar(labels, [v * 100 for v in h2means], color=["#b23b3b", "#d98c5f", "#8fb3d9", "#1f5fa8"])
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xlabel("Pinnacle closing fair probability band"); ax.set_ylabel("return at market-average closing odds, %")
    ax.set_title("H2 — return by probability band"); fig.tight_layout()
    fig.savefig(os.path.join(outdir, "h2_bands.png"), dpi=150); plt.close(fig)

    seasons = sorted(h3res["by_season"])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(seasons, [(h3res["by_season"][s]["roi"] or 0) * 100 for s in seasons], color="#1f5fa8")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xlabel("season"); ax.set_ylabel("ROI, %"); ax.set_title("H3 — Bet365 above Pinnacle fair price (edge ≥ 2%)")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "h3_roi_by_season.png"), dpi=150); plt.close(fig)

    seasons = sorted(d1res)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(seasons, [d1res[s]["home_rate"] * 100 for s in seasons], marker="o", color="#b23b3b", label="observed home wins")
    ax.plot(seasons, [d1res[s]["mean_p_home"] * 100 for s in seasons], marker="o", color="#1f5fa8", label="Pinnacle closing expectation")
    ax.set_xlabel("season"); ax.set_ylabel("%"); ax.set_title("D1 — home advantage vs the market"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "d1_home.png"), dpi=150); plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    split = sys.argv[1] if len(sys.argv) > 1 else ""
    if split not in ("exploration", "holdout"):
        sys.exit("usage: python analysis.py exploration | holdout --one-look")
    outdir = os.path.join(OUT, split)
    os.makedirs(outdir, exist_ok=True)
    if split == "holdout":
        lock = os.path.join(outdir, "LOCK")
        if "--one-look" not in sys.argv:
            sys.exit("The holdout is looked at once. Run with --one-look when the exploration write-up is complete.")
        if os.path.exists(lock):
            sys.exit(f"The holdout has already been opened ({open(lock, encoding='utf-8').read().strip()}). Re-running is not allowed.")
        with open(lock, "w", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat(timespec="seconds"))
    seasons = EXPLORATION if split == "exploration" else HOLDOUT
    df = load(seasons)
    print(f"{split}: seasons {seasons[0]}–{seasons[-1]}, matches {len(df):,}")
    r1, cal = h1(df); print("H1 done")
    r2, means = h2(df); print("H2 done")
    r3 = h3(df); print("H3 done")
    rd = d1(df); print("D1 done")
    results = {"split": split, "seasons": seasons, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "n_boot": N_BOOT, "seed": SEED, "H1": r1, "H2": r2, "H3": r3, "D1": rd}
    with open(os.path.join(outdir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    figures(outdir, cal, means, r3, rd)

    print(f"\nH1  a = {r1['a']:+.4f} CI99 {r1['ci99_a'][0]:+.4f}…{r1['ci99_a'][1]:+.4f} | "
          f"b = {r1['b']:.4f} CI99 {r1['ci99_b'][0]:.4f}…{r1['ci99_b'][1]:.4f} | calibrated: {r1['claim_calibrated']}")
    print(f"    Brier {r1['brier']:.4f}, log-loss {r1['log_loss']:.4f}, matches {r1['matches']:,}")
    for k, v in r1["by_outcome"].items():
        print(f"    {k}: observed {v['observed']:.4f}, market {v['mean_p']:.4f}, "
              f"difference CI99 {v['ci99_observed_minus_p'][0]:+.4f}…{v['ci99_observed_minus_p'][1]:+.4f}")
    print(f"H2  top − bottom = {r2['top_minus_bottom']*100:+.2f} pp, CI99 {r2['ci99'][0]*100:+.2f}…{r2['ci99'][1]*100:+.2f}, "
          f"p = {r2['p_one_sided']:.4f} | bias: {r2['claim_flb']} | seasons {r2['seasons']}")
    for band, v in r2["band_mean_return"].items():
        print(f"    band {band}: return {v['mean']*100:+.2f}% (n={v['n']:,})")
    print(f"H3  bets {r3['bets']:,}, ROI {r3['roi']*100:+.2f}%, CI99 {r3['ci99'][0]*100:+.2f}…{r3['ci99'][1]*100:+.2f}, "
          f"p = {r3['p_one_sided']:.4f} | positive: {r3['claim_positive_roi']}")
    print(f"    return σ {r3['sd_return']:.2f}, bets needed for a 2% ROI at 80% power: {r3['bets_needed_for_2pct_roi_power80']:,.0f}; "
          f"CLV (Bet365 above Pinnacle's fair closing price): {r3['clv_share_beating_pinnacle_close']*100:.1f}%")
    rb = r3["robustness"]
    print(f"    robustness: ROI excluding odds ≥10 {rb['roi_excluding_odds_ge_10']*100:+.2f}% ({rb['bets_odds_lt_10']} bets), "
          f"ROI excluding 5 largest wins {rb['roi_excluding_top5_returns']*100:+.2f}%, "
          f"winners at odds ≥10: {rb['winners_odds_ge_10_observed']} vs {rb['winners_odds_ge_10_expected']:.1f} expected "
          f"| edge (strict reading): {r3['claim_edge_robust']}")
    print("D1  season: home-win rate / market expectation / difference [95%]")
    for s, v in rd.items():
        print(f"    {s}: {v['home_rate']*100:.1f}% / {v['mean_p_home']*100:.1f}% / {v['diff']*100:+.1f} pp "
              f"[{v['ci95_diff'][0]*100:+.1f}…{v['ci95_diff'][1]*100:+.1f}]")
    print(f"\nresults: {outdir}\\results.json, figures: h1_calibration.png, h2_bands.png, h3_roi_by_season.png, d1_home.png")


if __name__ == "__main__":
    main()
