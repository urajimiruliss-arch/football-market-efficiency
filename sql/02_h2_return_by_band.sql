-- 02 · H2 favourite–longshot bias: average return of a 1-unit bet per probability band,
--      priced at market-average closing odds, banded by Pinnacle's closing fair probability
-- Concepts: CTE (WITH), CASE bucketing, a named parameter (:split), window function over an aggregate

WITH bets AS (
    SELECT CASE WHEN p_close < 0.20 THEN '0.00-0.20'
                WHEN p_close < 0.40 THEN '0.20-0.40'
                WHEN p_close < 0.60 THEN '0.40-0.60'
                ELSE                     '0.60-1.00' END      AS band,
           CASE WHEN won = 1 THEN avg_close - 1 ELSE -1 END   AS ret
    FROM priced
    WHERE split = :split
      AND p_close IS NOT NULL          -- sane Pinnacle closing line
      AND avg_ok = 1                   -- all three market-average closing prices present
)
SELECT band,
       COUNT(*)                                   AS n,
       AVG(ret)                                   AS mean_return,
       -- H2 statistic on every row: top band minus bottom band
       MAX(CASE WHEN band = '0.60-1.00' THEN AVG(ret) END) OVER ()
     - MAX(CASE WHEN band = '0.00-0.20' THEN AVG(ret) END) OVER () AS top_minus_bottom
FROM bets
GROUP BY band
ORDER BY band;
