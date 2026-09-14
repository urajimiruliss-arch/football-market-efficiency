-- 04 · D1 home advantage vs the market, by season (2020/21 was played mostly without spectators)
-- Concepts: filtering one outcome from the long view, differences of aggregates, LAG window function

WITH by_season AS (
    SELECT season,
           COUNT(*)      AS matches,
           AVG(won)      AS home_rate,
           AVG(p_close)  AS mean_p_home
    FROM priced
    WHERE split = :split AND outcome = 'H' AND p_close IS NOT NULL
    GROUP BY season
)
SELECT season, matches, home_rate, mean_p_home,
       home_rate - mean_p_home                             AS diff,
       home_rate - LAG(home_rate) OVER (ORDER BY season)   AS home_rate_change_vs_prev
FROM by_season
ORDER BY season;
