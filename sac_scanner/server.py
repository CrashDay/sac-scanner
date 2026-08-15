from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .live import build_live_scan
from .models import RiskPlan
from .schwab import SchwabError


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "public"


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
        if parsed.path == "/api/config":
            self.send_json({"ok": True, "watchlist_path": "config/watchlist.txt", "annotations_path": "config/annotations.json"})
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

    def handle_scan(self, query: str) -> None:
        params = parse_qs(query)
        risk = RiskPlan(
            account_size=float_param(params, "account_size", 1000),
            risk_per_trade=float_param(params, "risk_per_trade", 50),
            reward_target=float_param(params, "reward_target", 100),
            daily_max_loss=float_param(params, "daily_max_loss", 100),
            max_consecutive_losers=int(float_param(params, "max_consecutive_losers", 3)),
        )
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
        self.send_json(payload)

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
