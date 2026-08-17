from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .models import Candidate, RiskPlan
from .scoring import evaluate, grade_rank
from .schwab import SchwabConfig, SchwabMarketDataClient
from .universe import DEFAULT_UNIVERSE_PATH, load_universe_symbols


WATCHLIST_CACHE_PATH = Path("config/watchlist.txt")
CACHE_HEADER_PREFIX = "# sac_scanner_cache=1"
EASTERN = ZoneInfo("America/New_York")
SCAN_START_ET = time(4, 0)
SCAN_END_ET = time(20, 0)
DISPLAY_PRICE_MIN = 0.75
DISPLAY_PRICE_MAX = 25.0
UNKNOWN_FLOAT_MILLIONS = 999999.0
DISCOVERY_UNIVERSES = ("EQUITY_ALL", "NASDAQ", "NYSE", "OTCBB")
DISCOVERY_SORTS = ("PERCENT_CHANGE_UP", "AVERAGE_PERCENT_VOLUME", "VOLUME")
QUOTE_BATCH_SIZE = 250
ACTIVE_HISTORY_LIMIT = 300
DISCOVERY_VOLUME_MIN = 100_000


def build_live_scan(
    *,
    risk: RiskPlan = RiskPlan(),
    client: SchwabMarketDataClient | None = None,
    now: datetime | None = None,
    watchlist_path: Path = WATCHLIST_CACHE_PATH,
    universe_path: Path = DEFAULT_UNIVERSE_PATH,
) -> dict[str, Any]:
    client = client or SchwabMarketDataClient(SchwabConfig.from_env())
    now = now or datetime.now(timezone.utc)
    scan_active = is_scan_window(now)
    universe_symbols = load_universe_symbols(universe_path) if scan_active else []
    source = active_source(universe_symbols) if scan_active else "cached_watchlist"
    discovered_symbols = discover_symbols(client, universe_symbols) if scan_active else load_watchlist(watchlist_path)

    quotes = get_quotes_for_symbols(client, discovered_symbols)
    symbols = active_candidate_symbols(quotes, discovered_symbols) if scan_active else discovered_symbols
    histories = {symbol: safe_history(client, symbol) for symbol in symbols[:ACTIVE_HISTORY_LIMIT]}
    results = []

    for symbol in symbols:
        quote_payload = quotes.get(symbol) or quotes.get(symbol.upper()) or {}
        quote = quote_payload.get("quote") if isinstance(quote_payload.get("quote"), dict) else quote_payload
        candidate = candidate_from_schwab(symbol, quote, histories.get(symbol, {}), quote_payload)
        if candidate.price < DISPLAY_PRICE_MIN or candidate.price > DISPLAY_PRICE_MAX:
            continue
        result = evaluate(candidate, risk)
        results.append(result_to_dict(result, quote_payload))

    results.sort(
        key=lambda item: (
            grade_rank(item["grade"]),
            -item["score"],
            -item["change_percent"],
            -item["relative_volume"],
        )
    )

    if scan_active and results:
        save_watchlist([item["symbol"] for item in results], watchlist_path)

    return {
        "ok": True,
        "as_of": now.astimezone(timezone.utc).isoformat(),
        "source": source,
        "discovery": {
            "scan_active": scan_active,
            "universes": list(DISCOVERY_UNIVERSES),
            "sorts": list(DISCOVERY_SORTS),
            "symbol_count": len(symbols),
            "discovered_symbol_count": len(discovered_symbols),
            "universe_symbol_count": len(universe_symbols),
            "cache_path": str(watchlist_path),
            "universe_path": str(universe_path),
        },
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


def active_source(universe_symbols: list[str]) -> str:
    return "schwab_universe" if universe_symbols else "schwab_movers"


def is_scan_window(now: datetime) -> bool:
    local = now.astimezone(EASTERN)
    if local.weekday() >= 5:
        return False
    current_time = local.time()
    return SCAN_START_ET <= current_time <= SCAN_END_ET


def load_watchlist(path: Path = WATCHLIST_CACHE_PATH) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if not lines or lines[0].strip() != CACHE_HEADER_PREFIX:
        return []
    symbols: list[str] = []
    for line in lines[1:]:
        symbol = line.split("#", 1)[0].strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def save_watchlist(symbols: list[str], path: Path = WATCHLIST_CACHE_PATH) -> None:
    unique = [symbol for index, symbol in enumerate(symbols) if symbol and symbol not in symbols[:index]]
    if not unique:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [CACHE_HEADER_PREFIX, f"# generated_at={generated_at}", *unique]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover_symbols(client: SchwabMarketDataClient, universe_symbols: list[str] | None = None) -> list[str]:
    if universe_symbols:
        return universe_symbols
    symbols: list[str] = []
    for universe in DISCOVERY_UNIVERSES:
        for sort in DISCOVERY_SORTS:
            payload = safe_movers(client, universe, sort)
            for item in mover_items(payload):
                symbol = str(item.get("symbol") or "").strip().upper()
                if symbol and symbol not in symbols:
                    symbols.append(symbol)
    return symbols


def get_quotes_for_symbols(client: SchwabMarketDataClient, symbols: list[str]) -> dict[str, Any]:
    quotes: dict[str, Any] = {}
    for batch in batches(symbols, QUOTE_BATCH_SIZE):
        try:
            quotes.update(client.get_quotes(batch))
        except Exception:
            continue
    return quotes


def batches(symbols: list[str], size: int) -> list[list[str]]:
    return [symbols[index : index + size] for index in range(0, len(symbols), size)]


def active_candidate_symbols(quotes: dict[str, Any], symbols: list[str]) -> list[str]:
    candidates = []
    for symbol in symbols:
        quote_payload = quotes.get(symbol) or quotes.get(symbol.upper()) or {}
        quote = quote_payload.get("quote") if isinstance(quote_payload.get("quote"), dict) else quote_payload
        price = first_number(quote, "lastPrice", "mark", "regularMarketLastPrice", "bidPrice", "askPrice") or 0
        change = number_or_none(quote.get("netPercentChange")) or number_or_none(quote.get("markPercentChange")) or 0
        volume = first_number(quote, "totalVolume", "regularMarketTradeVolume") or 0
        if DISPLAY_PRICE_MIN <= price <= DISPLAY_PRICE_MAX and change > 0 and volume >= DISCOVERY_VOLUME_MIN:
            candidates.append((symbol, change, volume))
    candidates.sort(key=lambda item: (-item[1], -item[2], item[0]))
    return [symbol for symbol, _change, _volume in candidates[:ACTIVE_HISTORY_LIMIT]]


def safe_movers(client: SchwabMarketDataClient, universe: str, sort: str) -> dict[str, Any]:
    try:
        return client.get_movers(universe, sort=sort, frequency=0)
    except Exception:
        return {}


def mover_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    screeners = payload.get("screeners") if isinstance(payload, dict) else None
    if not isinstance(screeners, list):
        return []
    return [item for item in screeners if isinstance(item, dict)]


def candidate_from_schwab(
    symbol: str,
    quote: dict[str, Any],
    history: dict[str, Any],
    raw_quote: dict[str, Any] | None = None,
) -> Candidate:
    price = first_number(quote, "lastPrice", "mark", "regularMarketLastPrice", "bidPrice", "askPrice")
    previous_close = first_number(quote, "closePrice", "regularMarketPreviousClose", "priorClose") or previous_close_from_history(history)
    total_volume = first_number(quote, "totalVolume", "regularMarketTradeVolume")
    average_volume = average_daily_volume(history)
    relative_volume = (total_volume / average_volume) if total_volume and average_volume else 0
    float_millions = schwab_float_millions(raw_quote or {}, price) or UNKNOWN_FLOAT_MILLIONS

    return Candidate(
        symbol=symbol,
        price=price or 0,
        previous_close=previous_close or price or 0,
        relative_volume=relative_volume,
        has_news=False,
        float_millions=float_millions,
        volume=int(total_volume) if total_volume else None,
        change_percent=number_or_none(quote.get("netPercentChange")) or number_or_none(quote.get("markPercentChange")),
    )


def result_to_dict(result, raw_quote: dict[str, Any]) -> dict[str, Any]:
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
        "news_headline": "",
        "float_millions": candidate.float_millions,
        "float_source": float_source(candidate, raw_quote),
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


def schwab_float_millions(raw_quote: dict[str, Any], price: float | None) -> float | None:
    fundamental = raw_quote.get("fundamental") if isinstance(raw_quote, dict) else None
    if not isinstance(fundamental, dict):
        return None

    market_cap_float = number_or_none(fundamental.get("marketCapFloat"))
    if market_cap_float and price and price > 0:
        return market_cap_float / price

    shares_outstanding = number_or_none(fundamental.get("sharesOutstanding"))
    if shares_outstanding:
        return shares_outstanding / 1_000_000

    return None


def float_source(candidate: Candidate, raw_quote: dict[str, Any]) -> str:
    if candidate.float_millions != UNKNOWN_FLOAT_MILLIONS:
        fundamental = raw_quote.get("fundamental") if isinstance(raw_quote, dict) else None
        if isinstance(fundamental, dict) and number_or_none(fundamental.get("marketCapFloat")) is not None:
            return "schwab_market_cap_float"
        return "schwab_shares_outstanding"
    return "unknown"


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
