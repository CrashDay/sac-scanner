# SAC Small Account Scanner

A local stock scanner inspired by the principles in `SAC2024-Strategy-PDF.pdf`.
It ranks day-trade candidates by the quality filters described in the guide:

- Price between `$1` and `$20`
- Leading percent gain or gap
- Relative volume of at least `5x`
- News catalyst preferred, required for A quality
- Float under `20M` shares preferred
- Potential for a meaningful move, ideally `20-30%`
- Pullback-style entry context on the right kind of stocks
- Small-account risk controls: `$50` risk to target `$100`, `-$100` daily max loss, stop after three consecutive losers

This is educational tooling, not financial advice or an order-entry system.

## Quick Start

```bash
python3 -m sac_scanner scan examples/candidates.csv
```

Show only A-quality candidates:

```bash
python3 -m sac_scanner scan examples/candidates.csv --min-grade A
```

Calculate position sizing:

```bash
python3 -m sac_scanner scan examples/candidates.csv --account-size 1000 --risk-per-trade 50
```

## Live Schwab Dashboard

The dashboard keeps Schwab credentials on the local server and polls the scanner
from the browser.

```bash
python3 -m sac_scanner.server
```

Then open:

```text
http://127.0.0.1:8765
```

On macOS, you can also double-click `scripts/start-sac-scanner.command` from
Finder to start the local dashboard.

By default it reads Schwab settings from:

```text
/Users/tonyday/Trader/config/schwab.env
```

The live universe is maintained in `config/watchlist.txt`. Strategy fields that
Schwab quotes do not reliably provide, such as float and news catalyst, are kept
in `config/annotations.json`.

Seed those files from your existing Trader watchlist:

```bash
python3 -m sac_scanner import-trader-watchlist
```

If the dashboard says Schwab authorization needs to be refreshed, reconnect the
existing Schwab integration first, then reload the page.

You can override the Schwab env file with:

```bash
SAC_SCHWAB_ENV=/path/to/schwab.env python3 -m sac_scanner.server
```

## Input Columns

Required:

- `symbol`
- `price`
- `previous_close`
- `relative_volume`
- `has_news`
- `float_millions`

Optional but recommended:

- `volume`
- `gap_percent`
- `change_percent`
- `target_potential_percent`
- `setup`
- `entry_price`
- `stop_price`

If `gap_percent` or `change_percent` is missing, the scanner derives percent change from `price` and `previous_close`.

## Scoring

The scanner grades each symbol as:

- `A`: meets all core small-account quality criteria
- `B`: promising but missing one important criterion
- `C`: watch only
- `Reject`: fails hard filters such as price, low relative volume, or no upward move

Missing news or excessive float prevents A quality, but the scanner may keep the
symbol on the watchlist if the rest of the move is strong.

Candidates are sorted by grade and score, then by percent change and relative volume.
