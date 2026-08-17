from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen


NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
DEFAULT_UNIVERSE_PATH = Path("data/universe/equities.json")


@dataclass(frozen=True)
class UniverseSymbol:
    symbol: str
    name: str
    exchange: str
    source: str


def refresh_universe(path: Path = DEFAULT_UNIVERSE_PATH) -> dict:
    nasdaq_text = fetch_text(NASDAQ_LISTED_URL)
    other_text = fetch_text(OTHER_LISTED_URL)
    symbols = build_universe(nasdaq_text, other_text)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [NASDAQ_LISTED_URL, OTHER_LISTED_URL],
        "count": len(symbols),
        "symbols": [asdict(symbol) for symbol in symbols],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def load_universe_symbols(path: Path = DEFAULT_UNIVERSE_PATH) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    symbols: list[str] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper() if isinstance(row, dict) else ""
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def build_universe(nasdaq_text: str, other_text: str) -> list[UniverseSymbol]:
    symbols: dict[str, UniverseSymbol] = {}
    for row in parse_pipe_rows(nasdaq_text):
        symbol = clean_symbol(row.get("Symbol", ""))
        name = str(row.get("Security Name") or "").strip()
        if include_nasdaq_row(row, symbol, name):
            symbols[symbol] = UniverseSymbol(symbol=symbol, name=name, exchange="NASDAQ", source="nasdaqlisted")

    for row in parse_pipe_rows(other_text):
        symbol = clean_symbol(row.get("ACT Symbol", ""))
        name = str(row.get("Security Name") or "").strip()
        if include_other_row(row, symbol, name):
            exchange = str(row.get("Exchange") or "").strip() or "OTHER"
            symbols[symbol] = UniverseSymbol(symbol=symbol, name=name, exchange=exchange, source="otherlisted")

    return [symbols[symbol] for symbol in sorted(symbols)]


def fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_pipe_rows(text: str) -> Iterable[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split("|")
    rows = []
    for line in lines[1:]:
        if line.startswith("File Creation Time"):
            continue
        values = line.split("|")
        if len(values) != len(header):
            continue
        rows.append(dict(zip(header, values)))
    return rows


def include_nasdaq_row(row: dict[str, str], symbol: str, name: str) -> bool:
    return (
        bool(symbol)
        and row.get("Test Issue") == "N"
        and row.get("ETF") == "N"
        and row.get("NextShares") == "N"
        and is_tradeable_common_symbol(symbol)
        and is_common_equity_name(name)
    )


def include_other_row(row: dict[str, str], symbol: str, name: str) -> bool:
    return (
        bool(symbol)
        and row.get("Test Issue") == "N"
        and row.get("ETF") == "N"
        and is_tradeable_common_symbol(symbol)
        and is_common_equity_name(name)
    )


def clean_symbol(value: str) -> str:
    return value.strip().upper()


def is_tradeable_common_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    if any(char in symbol for char in ("$", "^", "+", "=")):
        return False
    return True


def is_common_equity_name(name: str) -> bool:
    normalized = f" {name.lower()} "
    blocked_terms = (
        " warrant",
        " warrants",
        " wt ",
        " right",
        " rights",
        " unit",
        " units",
        " preferred",
        " preference",
        " depositary share",
        " note",
        " notes",
        " bond",
        " debenture",
        " etf",
        " etn",
        " fund",
        " trust",
        " acquisition corp",
        " spac",
    )
    return not any(term in normalized for term in blocked_terms)
