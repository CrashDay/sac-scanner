from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .models import Candidate, RiskPlan, parse_bool
from .scoring import evaluate, grade_rank
from .trader_import import DEFAULT_TRADER_WATCHLIST, import_trader_watchlist


GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "Reject": 3}


def parse_optional_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "").strip()
    return float(value) if value else None


def parse_optional_int(row: dict[str, str], key: str) -> int | None:
    value = row.get(key, "").strip()
    return int(float(value)) if value else None


def candidate_from_row(row: dict[str, str]) -> Candidate:
    return Candidate(
        symbol=row["symbol"].strip().upper(),
        price=float(row["price"]),
        previous_close=float(row["previous_close"]),
        relative_volume=float(row["relative_volume"]),
        has_news=parse_bool(row.get("has_news", "")),
        float_millions=float(row["float_millions"]),
        volume=parse_optional_int(row, "volume"),
        gap_percent=parse_optional_float(row, "gap_percent"),
        change_percent=parse_optional_float(row, "change_percent"),
        target_potential_percent=parse_optional_float(row, "target_potential_percent"),
        setup=row.get("setup", "").strip() or None,
        entry_price=parse_optional_float(row, "entry_price"),
        stop_price=parse_optional_float(row, "stop_price"),
    )


def load_candidates(path: Path) -> list[Candidate]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        rows: list[dict[str, Any]] = data if isinstance(data, list) else data["candidates"]
        return [candidate_from_row({key: str(value) for key, value in row.items()}) for row in rows]

    with path.open(newline="") as stream:
        return [candidate_from_row(row) for row in csv.DictReader(stream)]


def format_result(result) -> str:
    candidate = result.candidate
    lines = [
        f"{candidate.symbol:>6}  {result.grade:<6} score={result.score:>3} "
        f"price=${candidate.price:.2f} change={candidate.effective_change_percent:.1f}% "
        f"relvol={candidate.relative_volume:.1f}x float={candidate.float_millions:.1f}M",
        f"        cash shares: {result.max_shares_by_cash}",
    ]
    if result.max_shares_by_risk is not None:
        lines.append(f"        risk shares: {result.max_shares_by_risk}")
    if result.target_profit_price is not None:
        lines.append(f"        price target for configured reward: ${result.target_profit_price:.2f}")
    if result.pass_reasons:
        lines.append("        passes: " + "; ".join(result.pass_reasons))
    if result.fail_reasons:
        lines.append("        fails: " + "; ".join(result.fail_reasons))
    if result.warnings:
        lines.append("        watch: " + "; ".join(result.warnings))
    return "\n".join(lines)


def scan(args: argparse.Namespace) -> int:
    risk = RiskPlan(
        account_size=args.account_size,
        risk_per_trade=args.risk_per_trade,
        reward_target=args.reward_target,
        daily_max_loss=args.daily_max_loss,
        max_consecutive_losers=args.max_consecutive_losers,
    )
    results = [evaluate(candidate, risk) for candidate in load_candidates(args.input)]
    results.sort(
        key=lambda result: (
            grade_rank(result.grade),
            -result.score,
            -result.candidate.effective_change_percent,
            -result.candidate.relative_volume,
        )
    )

    max_grade = GRADE_ORDER[args.min_grade]
    visible = [result for result in results if GRADE_ORDER[result.grade] <= max_grade]

    print("SAC Small Account Scanner")
    print(
        f"Risk plan: ${risk.risk_per_trade:.0f} risk to target ${risk.reward_target:.0f}; "
        f"daily max loss -${risk.daily_max_loss:.0f}; stop after "
        f"{risk.max_consecutive_losers} consecutive losers"
    )
    print()

    if not visible:
        print("No candidates matched the requested grade filter.")
        return 0

    for result in visible:
        print(format_result(result))
        print()

    return 0


def import_watchlist(args: argparse.Namespace) -> int:
    summary = import_trader_watchlist(
        source_path=args.source,
        watchlist_path=args.watchlist,
        annotations_path=args.annotations,
        limit=args.limit,
    )
    print(
        f"Imported {summary['symbol_count']} symbol(s) from {summary['source']} "
        f"into {summary['watchlist_path']} and {summary['annotations_path']}."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sac-scanner",
        description="Rank stock scanner exports using small-account day-trade criteria.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan a CSV or JSON candidate list")
    scan_parser.add_argument("input", type=Path)
    scan_parser.add_argument("--min-grade", choices=GRADE_ORDER.keys(), default="C")
    scan_parser.add_argument("--account-size", type=float, default=1000.0)
    scan_parser.add_argument("--risk-per-trade", type=float, default=50.0)
    scan_parser.add_argument("--reward-target", type=float, default=100.0)
    scan_parser.add_argument("--daily-max-loss", type=float, default=100.0)
    scan_parser.add_argument("--max-consecutive-losers", type=int, default=3)
    scan_parser.set_defaults(func=scan)

    import_parser = subparsers.add_parser(
        "import-trader-watchlist",
        help="seed live scanner config from Trader's latest watchlist",
    )
    import_parser.add_argument("--source", type=Path, default=DEFAULT_TRADER_WATCHLIST)
    import_parser.add_argument("--watchlist", type=Path, default=Path("config/watchlist.txt"))
    import_parser.add_argument("--annotations", type=Path, default=Path("config/annotations.json"))
    import_parser.add_argument("--limit", type=int, default=30)
    import_parser.set_defaults(func=import_watchlist)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
