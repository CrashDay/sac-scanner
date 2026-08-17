from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_TRADER_WATCHLIST = Path("/Users/tonyday/Trader/data/watchlists/latest.json")


def import_trader_watchlist(
    source_path: Path = DEFAULT_TRADER_WATCHLIST,
    watchlist_path: Path = Path("config/watchlist.txt"),
    annotations_path: Path = Path("config/annotations.json"),
    *,
    limit: int = 30,
) -> dict[str, Any]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates") if isinstance(payload, dict) else []
    generated_at = str(payload.get("generated_at") or "") if isinstance(payload, dict) else ""
    if not isinstance(candidates, list):
        candidates = []

    symbols: list[str] = []
    annotations: dict[str, dict[str, Any]] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or symbol in symbols:
            continue
        symbols.append(symbol)
        annotations[symbol] = {
            "has_news": bool(item.get("catalyst")),
            "news_headline": str(item.get("catalyst") or "")[:280],
            "news_timestamp": generated_at if item.get("catalyst") else "",
            "float_millions": item.get("float_millions", ""),
            "target_potential_percent": item.get("target_potential_percent", ""),
            "setup": item.get("setup_type") or "pullback candidate",
            "entry_price": item.get("entry_price", ""),
            "stop_price": item.get("stop_price", ""),
        }
        if len(symbols) >= limit:
            break

    watchlist_path.parent.mkdir(parents=True, exist_ok=True)
    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    watchlist_path.write_text("\n".join(symbols) + "\n", encoding="utf-8")
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")

    return {
        "source": str(source_path),
        "watchlist_path": str(watchlist_path),
        "annotations_path": str(annotations_path),
        "symbol_count": len(symbols),
        "symbols": symbols,
    }
