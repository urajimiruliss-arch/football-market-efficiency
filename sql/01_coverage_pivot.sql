-- 01 · Data coverage: share of matches without Pinnacle closing odds, by season (rows) and league (columns)
-- Concepts: GROUP BY, aggregates, CASE inside an aggregate, pivoting with conditional aggregation
-- Finding reproduced: closing odds are missing for ~49% of 2025/26 matches, evenly across leagues (posthoc_holdout.py)

SELECT season,
       COUNT(*)                                                     AS matches,
       ROUND(100.0 * AVG(psch IS NULL), 1)                          AS missing_pct_all,
       ROUND(100.0 * AVG(CASE WHEN div = 'E0'  THEN psch IS NULL END), 1) AS E0,
       ROUND(100.0 * AVG(CASE WHEN div = 'E1'  THEN psch IS NULL END), 1) AS E1,
       ROUND(100.0 * AVG(CASE WHEN div = 'D1'  THEN psch IS NULL END), 1) AS D1,
       ROUND(100.0 * AVG(CASE WHEN div = 'I1'  THEN psch IS NULL END), 1) AS I1,
       ROUND(100.0 * AVG(CASE WHEN div = 'SP1' THEN psch IS NULL END), 1) AS SP1,
       ROUND(100.0 * AVG(CASE WHEN div = 'F1'  THEN psch IS NULL END), 1) AS F1
FROM matches
GROUP BY season
ORDER BY season;
