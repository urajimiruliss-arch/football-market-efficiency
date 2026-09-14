-- 06 · H3 as a trader would see it: cumulative P&L, maximum drawdown and the longest losing streak (1-unit stakes)
-- Concepts: window functions (ROW_NUMBER, running SUM, running MAX), named WINDOW, gaps-and-islands

WITH bets AS (
    SELECT match_date, match_id, outcome,
           CASE WHEN won = 1 THEN b365 - 1 ELSE -1 END AS ret
    FROM priced
    WHERE split = :split
      AND p_open IS NOT NULL AND b365_ok = 1
      AND NOT (close_over IS NOT NULL AND close_over NOT BETWEEN 1.00 AND 1.15)
      AND b365 * p_open - 1 >= 0.02
),
curve AS (
    SELECT *,
           ROW_NUMBER() OVER w AS k,
           SUM(ret)     OVER w AS pnl                          -- running P&L in units
    FROM bets
    WINDOW w AS (ORDER BY match_date, match_id, outcome ROWS UNBOUNDED PRECEDING)
),
marked AS (
    SELECT *,
           -- peak includes the starting bankroll level 0, so a losing start counts as drawdown
           MAX(MAX(pnl) OVER (ORDER BY k ROWS UNBOUNDED PRECEDING), 0) - pnl AS drawdown,
           -- gaps-and-islands: consecutive losses share the same (k − rank among losses)
           k - ROW_NUMBER() OVER (PARTITION BY ret < 0 ORDER BY k)          AS island
    FROM curve
),
losing_streaks AS (
    SELECT island, COUNT(*) AS length, MIN(match_date) AS started
    FROM marked
    WHERE ret < 0
    GROUP BY island
)
SELECT (SELECT COUNT(*) FROM curve)                              AS bets,
       (SELECT pnl FROM curve ORDER BY k DESC LIMIT 1)           AS final_pnl_units,
       (SELECT MAX(drawdown) FROM marked)                        AS max_drawdown_units,
       (SELECT match_date FROM marked ORDER BY drawdown DESC, k LIMIT 1) AS max_drawdown_date,
       (SELECT MAX(length) FROM losing_streaks)                  AS longest_losing_streak,
       (SELECT started FROM losing_streaks ORDER BY length DESC, started LIMIT 1) AS streak_started;
