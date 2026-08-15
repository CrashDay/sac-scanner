from __future__ import annotations

from dataclasses import dataclass


TRUE_VALUES = {"1", "true", "yes", "y", "news", "catalyst"}


@dataclass(frozen=True)
class Candidate:
    symbol: str
    price: float
    previous_close: float
    relative_volume: float
    has_news: bool
    float_millions: float
    volume: int | None = None
    gap_percent: float | None = None
    change_percent: float | None = None
    target_potential_percent: float | None = None
    setup: str | None = None
    entry_price: float | None = None
    stop_price: float | None = None

    @property
    def effective_change_percent(self) -> float:
        if self.change_percent is not None:
            return self.change_percent
        if self.gap_percent is not None:
            return self.gap_percent
        if self.previous_close <= 0:
            return 0.0
        return ((self.price - self.previous_close) / self.previous_close) * 100

    @property
    def risk_per_share(self) -> float | None:
        if self.entry_price is None or self.stop_price is None:
            return None
        risk = self.entry_price - self.stop_price
        return risk if risk > 0 else None


@dataclass(frozen=True)
class RiskPlan:
    account_size: float = 1000.0
    risk_per_trade: float = 50.0
    reward_target: float = 100.0
    daily_max_loss: float = 100.0
    max_consecutive_losers: int = 3


@dataclass(frozen=True)
class ScanResult:
    candidate: Candidate
    grade: str
    score: int
    pass_reasons: tuple[str, ...]
    fail_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    max_shares_by_cash: int
    max_shares_by_risk: int | None
    target_profit_price: float | None


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in TRUE_VALUES
