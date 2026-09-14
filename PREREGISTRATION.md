# Pre-registration: How efficiently do bookmakers price European football?

**Frozen:** 2026-09-13, before any analysis relating odds to match outcomes.
Definitions, thresholds, statistics and the holdout below are not changed after this date.

## Data

football-data.co.uk, six leagues (England Premier League and Championship, Bundesliga, Serie A, La Liga,
Ligue 1), seasons 2016/17–2025/26, ~23,500 matches. Raw files are not published (no formal licence);
only derived aggregates, charts and conclusions are, with attribution.

Columns used: `FTR` (result), Pinnacle pre-closing `PSH/PSD/PSA`, Pinnacle closing `PSCH/PSCD/PSCA`,
Bet365 pre-closing `B365H/B365D/B365A`, market-average closing `AvgCH/AvgCD/AvgCA`.
A match is excluded from a hypothesis only if a column that hypothesis needs is missing or non-positive.

**Fair probabilities** from any bookmaker are obtained by proportional margin removal:
`p_i = (1/odds_i) / Σ_j (1/odds_j)` over home, draw, away.

## Split

- **Exploration:** 2016/17 – 2022/23 (7 seasons). Results reported as in-sample.
- **Holdout:** 2023/24 – 2025/26 (3 seasons). Evaluated **once**, after the exploration write-up is complete.
- No thresholds are tuned on exploration data — every threshold below is fixed now.

## Confirmatory hypotheses

Significance on the holdout: **p < 0.01** (three hypotheses, Bonferroni-conservative).
Outcomes within a match are dependent (they sum to one), so all uncertainty is estimated by
**bootstrap resampling of matches** (10,000 resamples), never of individual outcomes.

### H1 — Pinnacle's closing line is well calibrated

Stack all three outcomes of every match. Fit logistic regression `y ~ a + b · logit(p_close)` where
`p_close` is Pinnacle closing fair probability.
- Claim: calibration holds, i.e. the 99% bootstrap CI contains `b = 1` and `a = 0`.
- Reported additionally: Brier score, log-loss, calibration by outcome type (home / draw / away).

### H2 — The soft market shows a favourite–longshot bias at the close

For every outcome, return of backing at market-average closing odds: `r = AvgC − 1` if it happened, else `−1`.
Bands by Pinnacle closing fair probability: `[0, 0.20)`, `[0.20, 0.40)`, `[0.40, 0.60)`, `[0.60, 1]`.
- Statistic: mean return in the top band minus mean return in the bottom band.
- Claim: the difference is **> 0** (longshots lose more), one-sided.

### H3 — Soft-book prices above the sharp price are positive expected value at bet time

Selection uses only information available at bet time (no closing prices).
`p_sharp` = Pinnacle **pre-closing** fair probability. For each outcome, `edge = B365 · p_sharp − 1`.
Bet £1 at Bet365 pre-closing odds on every outcome with **edge ≥ 0.02**.
- Statistic: ROI = mean return per bet.
- Claim: ROI **> 0**, one-sided.
- Reported additionally: closing-line value — share of selected bets where the Bet365 price exceeds the
  Pinnacle **closing** fair price, and number of bets per season.
- Power note: a single back bet has σ ≈ 150% of stake, so detecting ROI = 2% needs on the order of
  40,000 bets; the result is interpreted with that in mind, and a non-significant positive ROI is reported
  as "not confirmed", not as "refuted".

## Descriptive (not confirmatory)

### D1 — Did the market price the empty-stadium effect?

Season 2020/21 was largely played without crowds — a one-off natural experiment that cannot be held out.
Compare, per season, the observed home-win rate with the mean Pinnacle closing home probability.
Reported with bootstrap intervals; no significance claim.

## Controls applied throughout

- Every effect is also shown per league and per season, to check it is not carried by one subgroup.
- Odds sanity: matches where Pinnacle closing overround is outside `[1.00, 1.15]` are reported and excluded.
- Duplicated matches (same date, home and away team) are removed before analysis.

---

## Addendum — data notes (added 2026-09-13, after freeze; no definitions changed)

Recorded from `quality.py`, which inspects completeness and odds only — no odds-versus-outcome
relationship was computed before this note.

- 23,457 matches; 0 duplicates, 0 unparseable dates, 0 missing results.
- Pinnacle pre-closing odds missing for 1,164 matches (~5%), closing for 1,139 (~5%), spread evenly across leagues.
- Bet365 pre-closing odds missing for 6 matches.
- **Market-average closing odds (`AvgCH/AvgCD/AvgCA`) are absent for the first three seasons of every league
  (2016/17–2018/19; 7,134 matches)** — the source introduced these columns in 2019/20. Under the rule above,
  those matches are excluded from H2, so **H2 exploration covers 2019/20–2022/23 (4 seasons)**. Earlier
  Betbrain average columns are *pre-closing*, a different quantity, and are deliberately **not** substituted.
- Pinnacle closing overround: median 1.0265, 1st–99th percentile 1.0182–1.0397. One match (England
  Championship, overround 0.9335) falls outside `[1.00, 1.15]` and is excluded as specified.

## Addendum 2 — exploration diagnostics and a stricter H3 reading (added 2026-09-13, before the holdout; no definitions changed)

**Why this was needed.** On exploration seasons H3's per-season ROI changes sign at 2019/20
(2016/17–2018/19: 803 bets, ROI −13.2%; 2019/20–2022/23: 451 bets, ROI +36.1%). The break coincides with
a change in the source's columns, and all holdout seasons lie after it, so a collection artifact could have
been "confirmed" by the holdout.

**Timing diagnostic (odds only, all seasons, no outcomes read — `diag_timing.py`).** The distance of Pinnacle
pre-closing and Bet365 pre-closing fair probabilities from Pinnacle closing is stable across all ten seasons
(Bet365 is closer to the close in 40–44% of matches every season). No change in collection timing that would
create look-ahead is visible. What did change: the H3 rule triggers on 3.3–4.6% of outcomes before 2019/20
and 1.2–2.0% after, because Bet365 diverges from Pinnacle less often.

**Composition diagnostic (exploration seasons only — `h3_decomp.py`).** The sign change is carried by rare
long-odds winners: bets at odds ≥ 10 won 6 of 192 before 2019/20 and 14 of 83 after, against roughly 13 and 5–6
expected. Excluding odds ≥ 10, ROI is −0.7% before and +18.1% after (~2 standard errors, on a split found by
inspection). This is read as variance in a fat-tailed return, not as evidence of an edge or of an artifact.

**Stricter reading of H3 on the holdout (declared before it is opened).** H3's statistic and threshold are
unchanged. In addition, a significant positive holdout ROI is described as an **edge only if ROI also remains
positive after excluding bets at odds ≥ 10**; otherwise it is reported as "significant but driven by long-odds
winners". The holdout report also shows ROI without the five largest winners and observed versus expected
winners at odds ≥ 10. This only tightens the claim; it cannot make a negative result positive.

**Presentation.** The H2 chart title "favourite–longshot bias" presupposed an effect that exploration does not
show (the sign of top-minus-bottom varies by league from −9.0 to +13.9 points); it is renamed neutrally.
