# How efficiently do bookmakers price European football?

A pre-registered test of market efficiency on ~23,500 matches from six European leagues (2016/17–2025/26),
with an untouched holdout, bootstrap inference and explicit artifact checks.

**Headline:** Pinnacle's closing line was well calibrated in 2016/17–2022/23, but in the pre-registered holdout
(2023/24–2025/26) it was not — longshots won markedly less often than priced, in every season and league.
Post-hoc checks rule out missing data and margin composition as explanations. A prospective test on the
2026/27 season is registered in [`PREREGISTRATION_P1_2026-27.md`](PREREGISTRATION_P1_2026-27.md).

No betting recommendation follows from this work.

---

## Data

[football-data.co.uk](https://www.football-data.co.uk/) — results and odds for England Premier League and
Championship, Bundesliga, Serie A, La Liga and Ligue 1. Odds used: Pinnacle pre-closing and closing,
Bet365 pre-closing, market-average closing.

The source publishes no formal licence, so **raw files are not included in this repository**; only derived
aggregates and figures are. `download.py` fetches the same files and records a SHA-256 manifest.

## Method

1. **Pre-registration before any odds-versus-outcome analysis** — [`PREREGISTRATION.md`](PREREGISTRATION.md),
   with two dated addenda written before the holdout was opened.
2. **Split:** exploration 2016/17–2022/23, holdout 2023/24–2025/26. The holdout script writes a lock file on
   first run and refuses to run again.
3. **Inference:** outcomes within a match are dependent, so every interval comes from 10,000 bootstrap
   resamples of *matches*. Confirmatory threshold p < 0.01.
4. **Fair probabilities:** proportional margin removal (fixed in advance).
5. **Controls:** every effect broken down by league and season; duplicates and implausible overrounds removed.

## Results

| Hypothesis | Exploration 2016/17–2022/23 | Holdout 2023/24–2025/26 | Verdict |
|---|---|---|---|
| **H1** Pinnacle closing line calibrated (logistic slope b = 1, intercept a = 0) | b = 1.044 [0.995, 1.094], a = +0.028 [−0.003, +0.060] | b = 1.096 [1.013, 1.179], a = +0.062 [+0.009, +0.115] | **Not confirmed** |
| **H2** Favourite–longshot bias at market-average closing odds (top band minus bottom band > 0) | +2.2 pp [−9.9, +14.0], p = 0.31 | +21.0 pp [+7.6, +33.7], p < 0.001 | **Confirmed** |
| **H3** Bet365 priced ≥ 2% above Pinnacle's pre-closing fair price is +EV | 1,254 bets, ROI +4.5% [−14.0, +24.3], p = 0.27 | 265 bets, ROI −17.2% [−49.3, +22.6], p = 0.89 | **Not confirmed** |

Intervals are 99%. H2 exploration covers 2019/20–2022/23 only: market-average closing odds do not exist in the
source before 2019/20 (documented before analysis).

**Descriptive — empty stadiums.** In 2020/21, largely played without crowds, home teams won 40.2% of matches
against a market expectation of 41.2%: the market absorbed the loss of home advantage almost immediately.

Figures: [`outputs/exploration/`](outputs/exploration/) and [`outputs/holdout/`](outputs/holdout/).

## What explains the holdout? (post-hoc — does not change the verdicts)

Run after the single holdout look ([`posthoc_holdout.py`](posthoc_holdout.py)):

- **Not missing data.** Pinnacle closing odds are absent for ~49% of 2025/26 matches, but uniformly across all
  six leagues (44.7–51.3%), and for 0% of matches in every earlier season.
- **Not margin composition.** The average bookmaker's price relative to Pinnacle's fair price is stable
  2019/20–2025/26 (longshots about −7%, favourites about −3.5% to −4%), so a change in how margin is loaded
  cannot produce the holdout effect.
- **The bias is in Pinnacle's own closing prices.** Backing outcomes with closing fair probability below 0.20 at
  Pinnacle's closing odds returned **+0.8%** in 2019/20–2022/23 but **−17.8%** in the holdout. Longshots won
  **372 times against 422.5 expected** (142/171.0, 168/177.1, 62/74.4 by season) — roughly 2.6 standard
  deviations, present in every holdout season and league.

Either the market's pricing of longshots changed after 2022/23, or the holdout is an unlucky draw. Only new
data can separate the two; hence the prospective test.

## A lesson on variance (H3)

In exploration H3's ROI flipped from −13% (2016/17–2018/19) to +36% (2019/20–2022/23). It looked like a data
artifact at a change in the source's columns. Two checks showed otherwise:

- **Timing** ([`diag_timing.py`](diag_timing.py), odds only): the relation between Pinnacle and Bet365
  pre-closing prices is identical in all ten seasons — no look-ahead was introduced.
- **Composition** ([`h3_decomp.py`](h3_decomp.py)): the flip is carried by long-odds winners (6 of 192 before,
  14 of 83 after). Pooled across exploration, winners at odds ≥ 10 numbered **20 against 21.3 expected**.

Returns on these bets have a standard deviation of ~2.6 stakes, so demonstrating a 2% ROI would need about
**170,000 bets**. The data holds 1,254. The test was never going to be decisive — and the power calculation says
so before any result is read.

## Limitations

- One data source; pre-closing odds are stamped only as "Friday or Tuesday afternoon".
- Proportional margin removal is known to slightly overstate longshot probabilities. It was fixed in advance and
  identical across periods, so it cannot explain the *change* between them, but it may affect levels.
- Closing prices describe the market at kick-off; bets at those prices may not have been available in size.

## Reproduce

```bash
python download.py
python quality.py
python analysis.py exploration
python analysis.py holdout --one-look
python posthoc_holdout.py
```

Python 3, numpy, pandas, matplotlib. Logistic regression and bootstrap are implemented directly in numpy.
