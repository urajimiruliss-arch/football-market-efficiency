# Prospective pre-registration P1: does the longshot bias in Pinnacle's closing line persist?

**Frozen:** 2026-09-14, before any 2026/27 data was downloaded or inspected.
Nothing below changes after this date.

## Motivation

In the pre-registered holdout (2023/24–2025/26) of [`PREREGISTRATION.md`](PREREGISTRATION.md), outcomes with
Pinnacle closing fair probability below 0.20 returned −17.8% at Pinnacle's closing odds (372 wins against
422.5 expected), after +0.8% in 2019/20–2022/23. A holdout that has been looked at cannot confirm what it
suggested. This test uses matches that had not been played when it was written.

## Data

football-data.co.uk, the same six leagues (E0, E1, D1, I1, SP1, F1), season 2026/27,
**only matches dated 2026-09-15 or later.** Earlier 2026/27 matches are excluded even though they exist.

Same processing as the main study: proportional margin removal, matches with Pinnacle closing overround
outside `[1.00, 1.15]` or any missing closing price excluded, duplicates removed.

## Primary hypothesis

For every outcome with Pinnacle closing fair probability `p < 0.20`, return of backing it at Pinnacle's
closing odds: `odds − 1` if it happened, else `−1`.

- **Claim:** mean return **< 0**, one-sided, **p < 0.01**, bootstrap of matches (10,000 resamples).
- Reported with it: observed wins, expected wins `Σp`, and the ratio.

## Secondary (reported, not used for the claim)

- Logistic calibration slope `b` on all outcomes, as in H1.
- The primary statistic recomputed with **power-method** margin removal (`p_i = (1/o_i)^k`, `k` such that
  `Σ p_i = 1`), to check that the result does not depend on the margin-removal method.

## Single look

The test is run **once**, at the earlier of:
- the number of qualifying outcomes reaching **2,900** (about the holdout's 2,915; with return standard
  deviation near 3 stakes this gives ~80% power against −17.8%), or
- **2027-06-01**.

Before then only the **count** of qualifying outcomes may be checked, never returns or win counts.

## Interpretation

- Claim holds → the longshot bias persisted into a season that did not exist when it was predicted. Any
  question of exploiting it (e.g. laying longshots on an exchange after commission and spread) is a separate,
  separately registered study.
- Mean return < 0 but p ≥ 0.01 → not confirmed; reported with its interval.
- Mean return ≥ 0 → the holdout effect was most likely chance.
