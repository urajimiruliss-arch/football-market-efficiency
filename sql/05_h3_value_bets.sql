-- 05 · H3 value bets: back Bet365 when its pre-closing price is ≥ 2% above Pinnacle's pre-closing fair price
-- Concepts: CTE, derived columns, UNION ALL for a totals row (SQLite has no ROLLUP), conditional AVG

WITH candidates AS (
    SELECT season, b365,
           b365 * p_open - 1                                AS edge,
           CASE WHEN won = 1 THEN b365 - 1 ELSE -1 END      AS ret
    FROM priced
    WHERE split = :split
      AND p_open IS NOT NULL AND b365_ok = 1
      -- a match whose closing prices exist but have an insane overround is excluded, as in analysis.py
      AND NOT (close_over IS NOT NULL AND close_over NOT BETWEEN 1.00 AND 1.15)
),
bets AS (
    SELECT * FROM candidates WHERE edge >= 0.02
)
SELECT season,
       COUNT(*)                                  AS bets,
       AVG(ret)                                  AS roi,
       AVG(CASE WHEN b365 < 10 THEN ret END)     AS roi_odds_lt_10,
       SUM(b365 >= 10 AND ret > 0)               AS winners_odds_ge_10
FROM bets
GROUP BY season
UNION ALL
SELECT 'all', COUNT(*), AVG(ret), AVG(CASE WHEN b365 < 10 THEN ret END), SUM(b365 >= 10 AND ret > 0)
FROM bets
ORDER BY season;
