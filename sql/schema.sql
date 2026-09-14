-- Schema for the SQL reproduction of the study. Built by build_db.py from the same raw CSVs as analysis.py.
-- One table holds the facts; the views hold the betting logic, so every query below reads like the spec.

DROP VIEW IF EXISTS priced;
DROP VIEW IF EXISTS match_overround;
DROP VIEW IF EXISTS outcomes;
DROP TABLE IF EXISTS matches;

CREATE TABLE matches (
    match_id   INTEGER PRIMARY KEY,
    season     TEXT NOT NULL,          -- '1617' … '2526'
    split      TEXT NOT NULL,          -- 'exploration' | 'holdout'
    div        TEXT NOT NULL,          -- E0, E1, D1, I1, SP1, F1
    match_date TEXT,                   -- ISO yyyy-mm-dd
    home_team  TEXT NOT NULL,
    away_team  TEXT NOT NULL,
    ftr        TEXT,                   -- full-time result: H / D / A
    psh REAL, psd REAL, psa REAL,          -- Pinnacle, pre-closing
    psch REAL, pscd REAL, psca REAL,       -- Pinnacle, closing
    b365h REAL, b365d REAL, b365a REAL,    -- Bet365, pre-closing
    avgch REAL, avgcd REAL, avgca REAL     -- market average, closing
);
CREATE INDEX ix_matches_split ON matches (split, season, div);

-- One row per match × outcome: the natural grain for betting analysis (a bet is on an outcome, not a match).
CREATE VIEW outcomes AS
SELECT match_id, season, split, div, match_date, 'H' AS outcome, COALESCE(ftr = 'H', 0) AS won,
       psh AS ps_open, psch AS ps_close, b365h AS b365, avgch AS avg_close
FROM matches
UNION ALL
SELECT match_id, season, split, div, match_date, 'D', COALESCE(ftr = 'D', 0), psd, pscd, b365d, avgcd FROM matches
UNION ALL
SELECT match_id, season, split, div, match_date, 'A', COALESCE(ftr = 'A', 0), psa, psca, b365a, avgca FROM matches;

-- Match-level overrounds (sum of implied probabilities) and "all three prices present" flags.
CREATE VIEW match_overround AS
SELECT match_id,
       CASE WHEN psch > 1 AND pscd > 1 AND psca > 1 THEN 1.0 / psch + 1.0 / pscd + 1.0 / psca END AS close_over,
       CASE WHEN psh  > 1 AND psd  > 1 AND psa  > 1 THEN 1.0 / psh  + 1.0 / psd  + 1.0 / psa  END AS open_over,
       COALESCE(avgch > 1 AND avgcd > 1 AND avgca > 1, 0)    AS avg_ok,
       COALESCE(b365h > 1 AND b365d > 1 AND b365a > 1, 0)    AS b365_ok
FROM matches;

-- Fair probabilities by proportional margin removal: p = (1/odds) / overround.
-- p_close is NULL unless the closing overround is sane (1.00–1.15), exactly as closing_sane() in analysis.py.
CREATE VIEW priced AS
SELECT o.*, mo.close_over, mo.open_over, mo.avg_ok, mo.b365_ok,
       CASE WHEN mo.close_over BETWEEN 1.00 AND 1.15 THEN (1.0 / o.ps_close) / mo.close_over END AS p_close,
       CASE WHEN mo.open_over IS NOT NULL            THEN (1.0 / o.ps_open)  / mo.open_over  END AS p_open
FROM outcomes AS o
JOIN match_overround AS mo USING (match_id);
