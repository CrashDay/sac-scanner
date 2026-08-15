from __future__ import annotations

from .models import Candidate, RiskPlan, ScanResult


PRICE_MIN = 1.0
PRICE_MAX = 20.0
REL_VOLUME_MIN = 5.0
FLOAT_MAX_MILLIONS = 20.0
STRONG_CHANGE_PERCENT = 10.0
IDEAL_POTENTIAL_PERCENT = 20.0


def evaluate(candidate: Candidate, risk: RiskPlan) -> ScanResult:
    pass_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []
    score = 0

    if PRICE_MIN <= candidate.price <= PRICE_MAX:
        score += 20
        pass_reasons.append("price is within the $1-$20 small-account range")
    else:
        fail_reasons.append("price is outside the $1-$20 range")

    change = candidate.effective_change_percent
    if change >= STRONG_CHANGE_PERCENT:
        score += 20
        pass_reasons.append(f"strong percent move at {change:.1f}%")
    elif change > 0:
        score += 8
        warnings.append(f"positive move is modest at {change:.1f}%")
    else:
        fail_reasons.append("not currently gapping or moving up")

    if candidate.relative_volume >= REL_VOLUME_MIN:
        score += 25
        pass_reasons.append(f"relative volume is {candidate.relative_volume:.1f}x")
    else:
        fail_reasons.append(f"relative volume is below {REL_VOLUME_MIN:.1f}x")

    if candidate.has_news:
        score += 15
        pass_reasons.append("has a news catalyst")
    else:
        fail_reasons.append("no news catalyst")

    if candidate.float_millions <= FLOAT_MAX_MILLIONS:
        score += 15
        pass_reasons.append(f"float is under 20M at {candidate.float_millions:.1f}M")
    else:
        fail_reasons.append(f"float is above 20M at {candidate.float_millions:.1f}M")

    if candidate.target_potential_percent is not None:
        if candidate.target_potential_percent >= IDEAL_POTENTIAL_PERCENT:
            score += 5
            pass_reasons.append(
                f"potential move is {candidate.target_potential_percent:.1f}%+"
            )
        else:
            warnings.append(
                f"potential move is only {candidate.target_potential_percent:.1f}%"
            )

    setup = (candidate.setup or "").strip().lower()
    if setup:
        if "pullback" in setup:
            score += 5
            pass_reasons.append("entry context mentions a pullback setup")
        else:
            warnings.append(f"setup is '{candidate.setup}', not a pullback")

    hard_pass = (
        PRICE_MIN <= candidate.price <= PRICE_MAX
        and change > 0
        and candidate.relative_volume >= REL_VOLUME_MIN
        and candidate.has_news
        and candidate.float_millions <= FLOAT_MAX_MILLIONS
    )

    hard_reject = (
        not (PRICE_MIN <= candidate.price <= PRICE_MAX)
        or change <= 0
        or candidate.relative_volume < REL_VOLUME_MIN
    )

    if hard_reject:
        grade = "Reject"
    elif hard_pass and score >= 90:
        grade = "A"
    elif hard_pass and score >= 75:
        grade = "B"
    elif score >= 55:
        grade = "C"
    else:
        grade = "Reject"

    max_shares_by_cash = int(risk.account_size // candidate.price) if candidate.price > 0 else 0
    max_shares_by_risk = None
    target_profit_price = None

    if candidate.risk_per_share:
        max_shares_by_risk = int(risk.risk_per_trade // candidate.risk_per_share)
        if max_shares_by_risk <= 0:
            warnings.append("stop is too wide for the configured risk per trade")
        shares = min(max_shares_by_cash, max_shares_by_risk)
        if shares > 0:
            target_profit_price = candidate.entry_price + (risk.reward_target / shares)
    else:
        warnings.append("entry_price and stop_price are needed for risk sizing")

    return ScanResult(
        candidate=candidate,
        grade=grade,
        score=min(score, 100),
        pass_reasons=tuple(pass_reasons),
        fail_reasons=tuple(fail_reasons),
        warnings=tuple(warnings),
        max_shares_by_cash=max_shares_by_cash,
        max_shares_by_risk=max_shares_by_risk,
        target_profit_price=target_profit_price,
    )


def grade_rank(grade: str) -> int:
    return {"A": 0, "B": 1, "C": 2, "Reject": 3}.get(grade, 4)
