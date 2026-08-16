from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRADER_LEDGER_PATH = Path("/Users/tonyday/Trader/data/paper_portfolio/ledger.jsonl")
DEFAULT_STATE_PATH = ROOT / "data" / "sac_day_trader_state.json"
STARTING_CASH = 100_000.0
SOURCE = "sac_day_trader"
STRATEGY_ID = "sac_manual_day_trade"


@dataclass(frozen=True)
class DayTraderConfig:
    account_size: float = 10_000.0
    risk_per_trade: float = 150.0
    reward_target: float = 300.0
    daily_max_loss: float = 500.0
    max_trades_per_day: int = 5
    max_open_positions: int = 2


@dataclass
class DayTradePosition:
    position_id: str
    symbol: str
    qty: int
    entry_price: float
    stop_price: float
    target_price: float
    opened_at: str
    grade: str
    score: int
    status: str = "OPEN"
    closed_at: str | None = None
    exit_price: float | None = None
    realized_pnl: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DayTradeState:
    session_date: str
    positions: list[DayTradePosition] = field(default_factory=list)
    lock_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_date": self.session_date,
            "positions": [position.to_dict() for position in self.positions],
            "lock_reason": self.lock_reason,
        }


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_event_id(*parts: object) -> str:
    return str(uuid5(NAMESPACE_URL, "|".join(str(part) for part in parts)))


def load_state(path: Path = DEFAULT_STATE_PATH, session_date: str | None = None) -> DayTradeState:
    session_date = session_date or today_utc()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DayTradeState(session_date=session_date)

    if payload.get("session_date") != session_date:
        return DayTradeState(session_date=session_date)

    positions = [
        DayTradePosition(**item)
        for item in payload.get("positions", [])
        if isinstance(item, dict)
    ]
    return DayTradeState(
        session_date=session_date,
        positions=positions,
        lock_reason=str(payload.get("lock_reason") or ""),
    )


def save_state(state: DayTradeState, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_ledger_events(path: Path = DEFAULT_TRADER_LEDGER_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def append_ledger_event(path: Path, event: dict[str, Any]) -> bool:
    ensure_starting_balance(path)
    existing_ids = {item.get("event_id") for item in load_ledger_events(path)}
    if event["event_id"] in existing_ids:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(normalize_ledger_event(event), sort_keys=True) + "\n")
    return True


def ensure_starting_balance(path: Path) -> None:
    event = {
        "event_id": stable_event_id("paper_portfolio", "starting_balance", STARTING_CASH),
        "timestamp": "2026-05-27T00:00:00-06:00",
        "event_type": "STARTING_BALANCE",
        "asset_class": "cash",
        "symbol": "CASH",
        "side": "CREDIT",
        "qty": 1,
        "price": STARTING_CASH,
        "strategy_id": "paper_portfolio",
        "source": "manual_seed",
        "cash_delta": STARTING_CASH,
        "realized_pnl": 0.0,
        "commission": 0.0,
        "position_id": None,
        "order_id": None,
        "reason": "Initialize paper portfolio with play money.",
        "rationale": "",
        "flawed": False,
        "warnings": [],
        "metadata": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = {item.get("event_id") for item in load_ledger_events(path)}
    if event["event_id"] not in existing_ids:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(normalize_ledger_event(event), sort_keys=True) + "\n")


def normalize_ledger_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    normalized["qty"] = int(normalized.get("qty") or 0)
    normalized["price"] = round(float(normalized.get("price") or 0.0), 4)
    normalized["cash_delta"] = round(float(normalized.get("cash_delta") or 0.0), 2)
    normalized["realized_pnl"] = round(float(normalized.get("realized_pnl") or 0.0), 2)
    normalized["commission"] = round(float(normalized.get("commission") or 0.0), 2)
    normalized.setdefault("position_id", None)
    normalized.setdefault("order_id", None)
    normalized.setdefault("reason", "")
    normalized.setdefault("rationale", "")
    normalized.setdefault("flawed", False)
    normalized.setdefault("warnings", [])
    normalized.setdefault("metadata", {})
    return normalized


def status(
    *,
    state_path: Path = DEFAULT_STATE_PATH,
    ledger_path: Path = DEFAULT_TRADER_LEDGER_PATH,
    config: DayTraderConfig = DayTraderConfig(),
    session_date: str | None = None,
) -> dict[str, Any]:
    state = load_state(state_path, session_date=session_date)
    events = [
        event
        for event in load_ledger_events(ledger_path)
        if event.get("source") == SOURCE and str(event.get("timestamp", "")).startswith(state.session_date)
    ]
    realized_pnl = round(sum(float(event.get("realized_pnl", 0.0)) for event in events), 2)
    open_positions = [position for position in state.positions if position.status == "OPEN"]
    entry_count = len([event for event in events if event.get("event_type") == "ENTRY"])
    lock_reason = state.lock_reason or lock_reason_for(config, realized_pnl, entry_count, len(open_positions))
    return {
        "ok": True,
        "session_date": state.session_date,
        "source": SOURCE,
        "config": asdict(config),
        "locked": bool(lock_reason),
        "lock_reason": lock_reason,
        "realized_pnl": realized_pnl,
        "entry_count": entry_count,
        "open_positions": [position.to_dict() for position in open_positions],
        "closed_positions": [position.to_dict() for position in state.positions if position.status == "CLOSED"],
        "ledger_path": str(ledger_path),
    }


def lock_reason_for(config: DayTraderConfig, realized_pnl: float, entry_count: int, open_count: int) -> str:
    if realized_pnl <= -abs(config.daily_max_loss):
        return f"Daily max loss reached ({realized_pnl:.2f})."
    if entry_count >= config.max_trades_per_day:
        return f"Max SAC day trades reached ({config.max_trades_per_day})."
    if open_count >= config.max_open_positions:
        return "A SAC day trade is already open."
    return ""


def approve_entry(
    candidate: dict[str, Any],
    *,
    config: DayTraderConfig,
    state_path: Path = DEFAULT_STATE_PATH,
    ledger_path: Path = DEFAULT_TRADER_LEDGER_PATH,
    session_date: str | None = None,
) -> dict[str, Any]:
    state = load_state(state_path, session_date=session_date)
    current_status = status(
        state_path=state_path,
        ledger_path=ledger_path,
        config=config,
        session_date=state.session_date,
    )
    if current_status["locked"]:
        return {"ok": False, "error": current_status["lock_reason"], "status": current_status}

    plan = build_trade_plan(candidate, config)
    if plan["qty"] <= 0:
        return {"ok": False, "error": "Candidate cannot be sized with the configured risk/cash."}

    timestamp = now_iso()
    position = DayTradePosition(
        position_id=str(uuid4()),
        symbol=plan["symbol"],
        qty=plan["qty"],
        entry_price=plan["entry_price"],
        stop_price=plan["stop_price"],
        target_price=plan["target_price"],
        opened_at=timestamp,
        grade=str(candidate.get("grade") or ""),
        score=int(candidate.get("score") or 0),
        notes=approval_notes(candidate),
    )
    state.positions.append(position)
    event = {
        "event_id": stable_event_id(SOURCE, position.position_id, "ENTRY"),
        "timestamp": timestamp,
        "event_type": "ENTRY",
        "asset_class": "stock",
        "symbol": position.symbol,
        "side": "BUY",
        "qty": position.qty,
        "price": position.entry_price,
        "strategy_id": STRATEGY_ID,
        "source": SOURCE,
        "cash_delta": -(position.qty * position.entry_price),
        "realized_pnl": 0.0,
        "commission": 0.0,
        "position_id": position.position_id,
        "reason": "Manual SAC day-trade approval.",
        "rationale": "; ".join(approval_notes(candidate)[:4]),
        "metadata": {
            "trade_mode": "DAY",
            "grade": position.grade,
            "score": position.score,
            "stop_price": position.stop_price,
            "target_price": position.target_price,
            "risk_per_trade": config.risk_per_trade,
            "reward_target": config.reward_target,
            "news_headline": candidate.get("news_headline", ""),
            "relative_volume": candidate.get("relative_volume"),
            "change_percent": candidate.get("change_percent"),
            "float_millions": candidate.get("float_millions"),
        },
    }
    append_ledger_event(ledger_path, event)
    save_state(state, state_path)
    return {
        "ok": True,
        "position": position.to_dict(),
        "event": normalize_ledger_event(event),
        "status": status(
            state_path=state_path,
            ledger_path=ledger_path,
            config=config,
            session_date=state.session_date,
        ),
    }


def close_position(
    position_id: str,
    exit_price: float,
    *,
    state_path: Path = DEFAULT_STATE_PATH,
    ledger_path: Path = DEFAULT_TRADER_LEDGER_PATH,
    config: DayTraderConfig = DayTraderConfig(),
    session_date: str | None = None,
) -> dict[str, Any]:
    if exit_price <= 0:
        return {"ok": False, "error": "Exit price must be greater than zero."}

    state = load_state(state_path, session_date=session_date)
    position = next((item for item in state.positions if item.position_id == position_id), None)
    if position is None or position.status != "OPEN":
        return {"ok": False, "error": "Open SAC day-trade position not found."}

    timestamp = now_iso()
    position.status = "CLOSED"
    position.closed_at = timestamp
    position.exit_price = round(float(exit_price), 4)
    position.realized_pnl = round((position.exit_price - position.entry_price) * position.qty, 2)
    event = {
        "event_id": stable_event_id(SOURCE, position.position_id, "EXIT"),
        "timestamp": timestamp,
        "event_type": "EXIT",
        "asset_class": "stock",
        "symbol": position.symbol,
        "side": "SELL",
        "qty": position.qty,
        "price": position.exit_price,
        "strategy_id": STRATEGY_ID,
        "source": SOURCE,
        "cash_delta": position.qty * position.exit_price,
        "realized_pnl": position.realized_pnl,
        "commission": 0.0,
        "position_id": position.position_id,
        "reason": "Manual SAC day-trade exit.",
        "rationale": "Manual exit from SAC dashboard.",
        "metadata": {
            "trade_mode": "DAY",
            "entry_price": position.entry_price,
            "stop_price": position.stop_price,
            "target_price": position.target_price,
        },
    }
    append_ledger_event(ledger_path, event)
    save_state(state, state_path)
    return {
        "ok": True,
        "position": position.to_dict(),
        "event": normalize_ledger_event(event),
        "status": status(
            state_path=state_path,
            ledger_path=ledger_path,
            config=config,
            session_date=state.session_date,
        ),
    }


def build_trade_plan(candidate: dict[str, Any], config: DayTraderConfig) -> dict[str, Any]:
    symbol = str(candidate.get("symbol") or "").upper()
    price = float(candidate.get("price") or 0.0)
    stop = float(candidate.get("manual_stop") or candidate.get("stop_price") or 0.0)
    if stop <= 0 or stop >= price:
        stop = round(price * 0.97, 4)
    risk_per_share = max(price - stop, 0.0)
    max_by_risk = int(config.risk_per_trade // risk_per_share) if risk_per_share > 0 else 0
    max_by_cash = int(config.account_size // price) if price > 0 else 0
    qty = min(max_by_risk, max_by_cash)
    target = float(candidate.get("target_profit_price") or 0.0)
    if target <= price and qty > 0:
        target = price + (config.reward_target / qty)
    return {
        "symbol": symbol,
        "entry_price": round(price, 4),
        "stop_price": round(stop, 4),
        "target_price": round(target, 4),
        "qty": qty,
        "risk_per_share": round(risk_per_share, 4),
    }


def approval_notes(candidate: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    notes.extend(str(item) for item in candidate.get("passes", [])[:3])
    warnings = [str(item) for item in candidate.get("warnings", [])[:2]]
    if warnings:
        notes.append("Warnings: " + "; ".join(warnings))
    return notes
