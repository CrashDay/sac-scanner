# SAC Scanner Agent Context

This repository is the actual SAC scanner project. When Codex opens this repo
on any machine, inspect this folder directly.

## Runtime

Start the local dashboard from the repository root:

```bash
python3 -m sac_scanner.server --port 8765
```

On Windows, use:

```powershell
py -m sac_scanner.server --port 8765
```

The dashboard is:

```text
http://127.0.0.1:8765
```

The live API endpoint is:

```text
http://127.0.0.1:8765/api/scan
```

## Strategy

The scanner follows the SAC small-account framework:

- price between $1 and $20
- leading percent gain or gap
- relative volume of at least 5x
- fresh news catalyst preferred
- float under 20M preferred
- meaningful 20-30% upside potential preferred
- pullback-style entries on 1-minute or 5-minute charts
- small-account risk controls

This is educational tooling, not financial advice or an order-entry system.

## Project Map

- `sac_scanner/scoring.py`: SAC grading and risk sizing rules
- `sac_scanner/models.py`: Candidate, RiskPlan, and ScanResult dataclasses
- `sac_scanner/live.py`: live Schwab scan builder and closed-market cache
- `sac_scanner/universe.py`: listed-equity universe builder
- `sac_scanner/schwab.py`: Schwab OAuth/token handling and market-data client
- `sac_scanner/day_trader.py`: manual SAC day-trader state and ledger helpers
- `sac_scanner/server.py`: local HTTP server and API routes
- `public/`: browser dashboard
- `config/watchlist.txt`: scanner-generated closed-market candidate cache
- `tests/`: unit tests for scoring, universe, and day-trader behavior

## Current Live Scan Behavior

The active scanner uses a generated local listed-equity universe from Nasdaq
Trader symbol directory files. Generate it per machine with:

```bash
python3 -m sac_scanner refresh-universe
```

On Windows:

```powershell
py -m sac_scanner refresh-universe
```

This writes `data/universe/equities.json`. That file is generated local data and
is intentionally ignored by git.

During weekdays from 4:00 AM to 8:00 PM Eastern, the scanner uses the local
universe and Schwab quotes/history/fundamentals. Outside those hours, the
dashboard uses `config/watchlist.txt` only as a trusted scanner-generated cache
of the last active candidates.

Do not treat `config/watchlist.txt` as a manual input list. Legacy bare-symbol
watchlists are ignored unless the scanner cache header is present.

Do not use `config/annotations.json` as a live scan input. The live scanner no
longer depends on local annotations for float/news/setup/entry/stop.

Schwab does not reliably provide true public float. The scanner uses available
fundamental values as a proxy when present and marks float unknown otherwise.

## Schwab Credentials

By default the scanner looks for Schwab config at:

```text
/Users/tonyday/Trader/config/schwab.env
```

On Windows or any non-Mac setup, point the scanner at the local env file:

```powershell
$env:SAC_SCHWAB_ENV = "C:\path\to\schwab.env"
py -m sac_scanner.server --port 8765
```

Required values are `SCHWAB_APP_KEY` and `SCHWAB_APP_SECRET`. A refresh token can
come from `SCHWAB_REFRESH_TOKEN` or the configured token cache.

## Verification

Run tests from the repository root:

```bash
python3 -m unittest
```

On Windows:

```powershell
py -m unittest
```
