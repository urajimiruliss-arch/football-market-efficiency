# -*- coding: utf-8 -*-
"""Download historical results and odds from football-data.co.uk.

Source: https://www.football-data.co.uk/ — CSV files per league and season (results, odds from ~20 bookmakers
including Pinnacle and closing lines). The site publishes no formal licence, therefore:
  - raw files are NOT published (data/raw is in .gitignore);
  - only derived analysis (aggregates, figures, conclusions) is published, with attribution.

The script is idempotent: files already downloaded are not requested again. It pauses between requests.
Each file gets an entry in data/manifest.json: URL, size, rows, whether Pinnacle closing odds are present,
sha256 and download time.
"""
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
MANIFEST = os.path.join(BASE, "data", "manifest.json")
URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"

LEAGUES = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "D1": "Germany Bundesliga",
    "I1": "Italy Serie A",
    "SP1": "Spain La Liga",
    "F1": "France Ligue 1",
}
SEASONS = [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(2016, 2026)]   # 1617 … 2526
PAUSE_SEC = 1.5
HEADERS = {"User-Agent": "portfolio-research/1.0 (personal non-commercial analysis)"}


def inspect(content: bytes) -> dict:
    text = content.decode("latin-1")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0] if rows else []
    matches = [r for r in rows[1:] if len(r) > 3 and any(c.strip() for c in r)]
    return {"rows": len(matches), "columns": len(header),
            "has_pinnacle_closing": all(c in header for c in ("PSCH", "PSCD", "PSCA")),
            "has_pinnacle": all(c in header for c in ("PSH", "PSD", "PSA")),
            "has_market_avg_closing": all(c in header for c in ("AvgCH", "AvgCD", "AvgCA"))}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(RAW, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            manifest = json.load(f)
    fetched = skipped = failed = 0
    for div in LEAGUES:
        for season in SEASONS:
            name = f"{season}_{div}.csv"
            path = os.path.join(RAW, name)
            if os.path.exists(path) and name in manifest:
                skipped += 1
                continue
            url = URL.format(season=season, div=div)
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as r:
                    content = r.read()
            except urllib.error.HTTPError as e:
                print(f"  {name}: HTTP {e.code}")
                failed += 1
                time.sleep(PAUSE_SEC)
                continue
            except Exception as e:
                print(f"  {name}: error {type(e).__name__}: {e}")
                failed += 1
                time.sleep(PAUSE_SEC)
                continue
            with open(path, "wb") as f:
                f.write(content)
            info = inspect(content)
            manifest[name] = {"league": LEAGUES[div], "div": div, "season": season, "url": url,
                              "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                              "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **info}
            fetched += 1
            print(f"  {name}: {len(content)/1024:.0f} KB, matches {info['rows']}, "
                  f"Pinnacle closing: {'yes' if info['has_pinnacle_closing'] else 'no'}")
            time.sleep(PAUSE_SEC)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    total = sum(v["bytes"] for v in manifest.values())
    print(f"\ndownloaded {fetched}, already present {skipped}, errors {failed} | files in total {len(manifest)}, {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
