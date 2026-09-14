-- 03 · H1 calibration table: Pinnacle closing fair probability vs observed frequency in 5-point bins
-- Concepts: integer binning, HAVING (filter after grouping), scalar subquery for a whole-sample metric
-- The Brier score is computed over ALL outcomes, not just the bins that pass HAVING.

SELECT CAST(p_close * 20 AS INTEGER) * 5                      AS bin_from_pct,
       COUNT(*)                                               AS n,
       AVG(p_close)                                           AS mean_p,
       AVG(won)                                               AS observed,
       AVG(won) - AVG(p_close)                                AS observed_minus_p,
       (SELECT AVG((p_close - won) * (p_close - won))
          FROM priced
         WHERE split = :split AND p_close IS NOT NULL)        AS brier_all
FROM priced
WHERE split = :split AND p_close IS NOT NULL
GROUP BY bin_from_pct
HAVING COUNT(*) >= 50
ORDER BY bin_from_pct;
