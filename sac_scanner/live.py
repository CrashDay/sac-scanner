from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Candidate, RiskPlan
from .scoring import evaluate, grade_rank
from .schwab import SchwabConfig, SchwabMarketDataClient


DEFAULT_WATCHLIST_PATH = Path("config/watchlist.txt")
DEFAULT_ANNOTATIONS_PATH = Path("config/annotations.json")


def load_watchlist(path: Path = DEFAULT_WATCHLIST_PATH) -> list[str]:
    symbols: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.split("#", 1)[0].strip().upper()
        if clean:
            symbols.append(clean)
    return sorted(dict.fromkeys(symbols))


def load_annotations(path: Path = DEFAULT_ANNOTATIONS_PATH) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(symbol).upper(): value for symbol, value in data.items() if isinstance(value, dict)}


def build_live_scan(
    *,
    watchlist_path: Path = DEFAULT_WATCHLIST_PATH,
    annotations_path: Path = DEFAULT_ANNOTATIONS_PATH,
    risk: RiskPlan = RiskPlan(),
    client: SchwabMarketDataClient | None = None,
) -> dict[str, Any]:
    symbols = load_watchlist(watchlist_path)
    annotations = load_annotations(annotations_path)
    client = client or SchwabMarketDataClient(SchwabConfig.from_env())

    quotes = client.get_quotes(symbols)
    histories = {symbol: safe_history(client, symbol) for symbol in symbols}
    results = []

    for symbol in symbols:
        quote_payload = quotes.get(symbol) or quotes.get(symbol.upper()) or {}
        quote = quote_payload.get("quote") if isinstance(quote_payload.get("quote"), dict) else quote_payload
        annotation = annotations.get(symbol, {})
        candidate = candidate_from_schwab(symbol, quote, histories.get(symbol, {}), annotation)
        result = evaluate(candidate, risk)
        results.append(result_to_dict(result, annotation, quote_payload))

    results.sort(
        key=lambda item: (
            grade_rank(item["grade"]),
            -item["score"],
            -item["change_percent"],
            -item["relative_volume"],
        )
    )

    return {
        "ok": True,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "schwab",
        "symbols": symbols,
        "risk": {
            "account_size": risk.account_size,
            "risk_per_trade": risk.risk_per_trade,
            "reward_target": risk.reward_target,
            "daily_max_loss": risk.daily_max_loss,
            "max_consecutive_losers": risk.max_consecutive_losers,
        },
        "results": results,
    }


def candidate_from_schwab(
    symbol: str,
    quote: dict[str, Any],
    history: dict[str, Any],
    annotation: dict[str, Any],
) -> Candidate:
    price = first_number(quote, "lastPrice", "mark", "regularMarketLastPrice", "bidPrice", "askPrice")
    previous_close = first_number(quote, "closePrice", "regularMarketPreviousClose", "priorClose") or previous_close_from_history(history)
    total_volume = first_number(quote, "totalVolume", "regularMarketTradeVolume")
    average_volume = average_daily_volume(history)
    relative_volume = (total_volume / average_volume) if total_volume and average_volume else float(annotation.get("relative_volume") or 0)

    return Candidate(
        symbol=symbol,
        price=price or 0,
        previous_close=previous_close or price or 0,
        relative_volume=relative_volume,
        has_news=bool(annotation.get("has_news", False)),
        float_millions=float(annotation.get("float_millions") or 999999),
        volume=int(total_volume) if total_volume else None,
        gap_percent=number_or_none(annotation.get("gap_percent")),
        change_percent=number_or_none(quote.get("netPercentChange")) or number_or_none(quote.get("markPercentChange")),
        target_potential_percent=number_or_none(annotation.get("target_potential_percent")),
        setup=str(annotation.get("setup") or "") or None,
        entry_price=number_or_none(annotation.get("entry_price")),
        stop_price=number_or_none(annotation.get("stop_price")),
    )


def result_to_dict(result, annotation: dict[str, Any], raw_quote: dict[str, Any]) -> dict[str, Any]:
    candidate = result.candidate
    return {
        "symbol": candidate.symbol,
        "grade": result.grade,
        "score": result.score,
        "price": round(candidate.price, 4),
        "previous_close": round(candidate.previous_close, 4),
        "change_percent": round(candidate.effective_change_percent, 2),
        "relative_volume": round(candidate.relative_volume, 2),
        "has_news": candidate.has_news,
        "news_headline": str(annotation.get("news_headline") or ""),
        "float_millions": candidate.float_millions,
        "volume": candidate.volume,
        "setup": candidate.setup or "",
        "max_shares_by_cash": result.max_shares_by_cash,
        "max_shares_by_risk": result.max_shares_by_risk,
        "target_profit_price": round(result.target_profit_price, 4) if result.target_profit_price else None,
        "passes": list(result.pass_reasons),
        "fails": list(result.fail_reasons),
        "warnings": list(result.warnings),
        "realtime": bool(raw_quote.get("realtime")) if isinstance(raw_quote, dict) else False,
    }


def safe_history(client: SchwabMarketDataClient, symbol: str) -> dict[str, Any]:
    try:
        return client.get_price_history(symbol)
    except Exception:
        return {}


def first_number(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = number_or_none(data.get(key))
        if value is not None:
            return value
    return None


def number_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def average_daily_volume(history: dict[str, Any], lookback: int = 20) -> float | None:
    candles = history.get("candles") if isinstance(history, dict) else None
    if not isinstance(candles, list):
        return None
    volumes = [number_or_none(candle.get("volume")) for candle in candles[-lookback - 1 : -1] if isinstance(candle, dict)]
    usable = [volume for volume in volumes if volume and volume > 0]
    if not usable:
        return None
    return sum(usable) / len(usable)


def previous_close_from_history(history: dict[str, Any]) -> float | None:
    value = number_or_none(history.get("previousClose")) if isinstance(history, dict) else None
    if value is not None:
        return value
    candles = history.get("candles") if isinstance(history, dict) else None
    if isinstance(candles, list) and len(candles) >= 2:
        prior = candles[-2]
        if isinstance(prior, dict):
            return number_or_none(prior.get("close"))
    return None
