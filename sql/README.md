# SQL reproduction

The study's point estimates, recomputed in plain SQL (SQLite, Python standard library only) and cross-checked
against the numbers `analysis.py` published in `outputs/*/results.json`. **82 of 82 checks match** (relative
tolerance 1e-9).

This layer adds no hypotheses and no inference. Bootstrap confidence intervals and the logistic regression stay in
Python. The holdout was already opened once, and here it is only re-described.

## Run

```bash
python download.py          # raw CSVs, if not present
python sql/build_db.py      # data/football.sqlite, rebuilt from data/raw (not published)
python sql/run_queries.py   # prints every result, then the cross-check summary; exit code 1 on any mismatch
```

## Design

`schema.sql` keeps the betting logic in views, so each query reads like the pre-registration:

| object | grain | what it encodes |
|---|---|---|
| `matches` | match | raw facts: result and four sets of 1X2 prices |
| `outcomes` | match × outcome | the long format a bet lives in (`UNION ALL` unpivot) |
| `match_overround` | match | overrounds and "all three prices present" flags |
| `priced` | match × outcome | fair probabilities by proportional margin removal, with the same 1.00–1.15 sanity rule as `analysis.py` |

## Queries

| file | question | SQL concepts |
|---|---|---|
| `01_coverage_pivot.sql` | Where are Pinnacle closing odds missing? | `GROUP BY`, conditional aggregation pivot |
| `02_h2_return_by_band.sql` | H2: return by probability band, top minus bottom | CTE, `CASE` bucketing, window over an aggregate |
| `03_h1_calibration_table.sql` | H1: calibration table and Brier score | binning, `HAVING`, scalar subquery |
| `04_d1_home_advantage.sql` | D1: home-win rate vs market expectation by season | `LAG` |
| `05_h3_value_bets.sql` | H3: bets, ROI, ROI without odds ≥ 10, by season | `UNION ALL` totals row (no `ROLLUP` in SQLite) |
| `06_h3_equity_curve.sql` | H3 as a trading record: P&L path, max drawdown, longest losing streak | running `SUM`/`MAX`, named `WINDOW`, gaps-and-islands |

## What the equity curve adds

Query 06 answers the question a trading desk asks before looking at ROI: what would holding the strategy have felt
like? It uses 1-unit stakes on H3 value bets.

| split | bets | final P&L | max drawdown | longest losing streak |
|---|---|---|---|---|
| exploration 2016/17–2022/23 | 1,254 | +56.7 units | 153.2 units | 27 bets |
| holdout 2023/24–2025/26 | 265 | −45.5 units | 53.6 units | 24 bets |

In exploration, the strategy ended positive only after a drawdown almost three times its final profit. Even a
genuine edge of that size would have been hard to sit through, and the holdout then showed there was none.
