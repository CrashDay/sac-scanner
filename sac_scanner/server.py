from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .day_trader import DayTraderConfig, approve_entry, close_position, status as day_trader_status
from .live import build_live_scan
from .models import RiskPlan
from .schwab import SchwabError


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "public"
SCAN_CACHE_TTL = timedelta(minutes=3)
SCAN_CACHE: dict[tuple[float, float, float, float, int], tuple[datetime, dict]] = {}


class ScannerHandler(BaseHTTPRequestHandler):
    server_version = "SACScanner/0.1"

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        rel_path = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        file_path = (PUBLIC_DIR / rel_path).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(file_path))
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scan":
            self.handle_scan(parsed.query)
            return
        if parsed.path == "/api/day-trader/status":
            self.send_json(day_trader_status(config=day_trader_config_from_query(parsed.query)))
            return
        if parsed.path == "/api/config":
            self.send_json(
                {
                    "ok": True,
                    "source": "schwab_universe_active_cached_watchlist_closed",
                    "universe_path": "data/universe/equities.json",
                    "cache_path": "config/watchlist.txt",
                    "scan_cache_ttl_seconds": int(SCAN_CACHE_TTL.total_seconds()),
                }
            )
            return

        rel_path = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        file_path = (PUBLIC_DIR / rel_path).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(file_path))
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self.read_json_body()
        if parsed.path == "/api/day-trader/approve-entry":
            result = approve_entry(
                payload.get("candidate", {}),
                config=day_trader_config_from_payload(payload),
            )
            self.send_json(result, status=HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/day-trader/close-position":
            result = close_position(
                str(payload.get("position_id") or ""),
                float_value(payload.get("exit_price"), 0),
                config=day_trader_config_from_payload(payload),
            )
            self.send_json(result, status=HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_scan(self, query: str) -> None:
        params = parse_qs(query)
        risk = RiskPlan(
            account_size=float_param(params, "account_size", 10_000),
            risk_per_trade=float_param(params, "risk_per_trade", 150),
            reward_target=float_param(params, "reward_target", 300),
            daily_max_loss=float_param(params, "daily_max_loss", 500),
            max_consecutive_losers=int(float_param(params, "max_consecutive_losers", 3)),
        )
        cache_key = risk_cache_key(risk)
        cached = SCAN_CACHE.get(cache_key)
        now = datetime.now(timezone.utc)
        if cached and now - cached[0] <= SCAN_CACHE_TTL:
            self.send_json({**cached[1], "cached": True})
            return
        try:
            payload = build_live_scan(risk=risk)
        except (OSError, SchwabError, ValueError) as exc:
            message = str(exc)
            self.send_json(
                {
                    "ok": False,
                    "needs_auth": is_auth_error(message),
                    "error": message,
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return
        SCAN_CACHE[cache_key] = (now, payload)
        self.send_json(payload)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def float_param(params: dict[str, list[str]], key: str, default: float) -> float:
    try:
        return float(params.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def risk_cache_key(risk: RiskPlan) -> tuple[float, float, float, float, int]:
    return (
        risk.account_size,
        risk.risk_per_trade,
        risk.reward_target,
        risk.daily_max_loss,
        risk.max_consecutive_losers,
    )


def day_trader_config_from_query(query: str) -> DayTraderConfig:
    params = parse_qs(query)
    return DayTraderConfig(
        account_size=float_param(params, "account_size", 10_000),
        risk_per_trade=float_param(params, "risk_per_trade", 150),
        reward_target=float_param(params, "reward_target", 300),
        daily_max_loss=float_param(params, "daily_max_loss", 500),
    )


def day_trader_config_from_payload(payload: dict) -> DayTraderConfig:
    risk = payload.get("risk") if isinstance(payload.get("risk"), dict) else {}
    return DayTraderConfig(
        account_size=float_value(risk.get("account_size"), 10_000),
        risk_per_trade=float_value(risk.get("risk_per_trade"), 150),
        reward_target=float_value(risk.get("reward_target"), 300),
        daily_max_loss=float_value(risk.get("daily_max_loss"), 500),
    )


def float_value(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def content_type_for(file_path: Path) -> str:
    if file_path.suffix == ".html":
        return "text/html; charset=utf-8"
    if file_path.suffix == ".css":
        return "text/css; charset=utf-8"
    if file_path.suffix == ".js":
        return "text/javascript; charset=utf-8"
    return "text/plain; charset=utf-8"


def is_auth_error(message: str) -> bool:
    return any(
        token in message.lower()
        for token in (
            "invalid_grant",
            "refresh token is invalid",
            "expired or revoked",
            "no schwab refresh token",
            "no schwab refresh token available",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SAC scanner dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ScannerHandler)
    print(f"SAC scanner dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
