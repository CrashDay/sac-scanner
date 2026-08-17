from __future__ import annotations

import base64
import gzip
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ENV_PATH = Path("/Users/tonyday/Trader/config/schwab.env")
DEFAULT_TOKEN_PATH = Path("/Users/tonyday/Trader/data/schwab_tokens.json")
DEFAULT_AUTH_BASE_URL = "https://api.schwabapi.com"
DEFAULT_API_BASE_URL = "https://api.schwabapi.com"
TOKEN_EXPIRY_BUFFER = timedelta(seconds=60)


class SchwabError(RuntimeError):
    pass


@dataclass(frozen=True)
class SchwabConfig:
    app_key: str
    app_secret: str
    refresh_token: str
    auth_base_url: str
    api_base_url: str
    token_path: Path

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "SchwabConfig":
        env_path = env_path or Path(os.environ.get("SAC_SCHWAB_ENV", DEFAULT_ENV_PATH))
        values = load_env_file(env_path)

        def get(name: str, default: str = "") -> str:
            return os.environ.get(name) or values.get(name) or default

        token_path = Path(get("SCHWAB_TOKEN_PATH", str(DEFAULT_TOKEN_PATH))).expanduser()
        if not token_path.is_absolute() and env_path.exists():
            token_path = (env_path.parent.parent / token_path).resolve()

        config = cls(
            app_key=get("SCHWAB_APP_KEY") or get("SCHWAB_CLIENT_ID"),
            app_secret=get("SCHWAB_APP_SECRET") or get("SCHWAB_CLIENT_SECRET"),
            refresh_token=get("SCHWAB_REFRESH_TOKEN"),
            auth_base_url=get("SCHWAB_AUTH_BASE_URL", DEFAULT_AUTH_BASE_URL),
            api_base_url=get("SCHWAB_API_BASE_URL", DEFAULT_API_BASE_URL),
            token_path=token_path,
        )

        missing = [
            name
            for name, value in {
                "SCHWAB_APP_KEY": config.app_key,
                "SCHWAB_APP_SECRET": config.app_secret,
            }.items()
            if not value
        ]
        if missing:
            raise SchwabError(f"Missing Schwab config value(s): {', '.join(missing)}")
        return config


class SchwabMarketDataClient:
    def __init__(self, config: SchwabConfig):
        self.config = config
        self._access_token: str | None = None

    def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        if not symbols:
            return {}
        return self._request_json(
            "/marketdata/v1/quotes",
            {"symbols": ",".join(symbols)},
        )

    def get_movers(self, symbol_id: str, *, sort: str = "PERCENT_CHANGE_UP", frequency: int = 0) -> dict[str, Any]:
        return self._request_json(
            f"/marketdata/v1/movers/{symbol_id}",
            {"sort": sort, "frequency": frequency},
        )

    def get_price_history(
        self,
        symbol: str,
        *,
        period_type: str = "month",
        period: int = 1,
        frequency_type: str = "daily",
        frequency: int = 1,
        need_extended_hours_data: bool = True,
        need_previous_close: bool = True,
    ) -> dict[str, Any]:
        return self._request_json(
            "/marketdata/v1/pricehistory",
            {
                "symbol": symbol,
                "periodType": period_type,
                "period": period,
                "frequencyType": frequency_type,
                "frequency": frequency,
                "needExtendedHoursData": str(need_extended_hours_data).lower(),
                "needPreviousClose": str(need_previous_close).lower(),
            },
        )

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token

        cached = self._read_token_cache()
        token = token_value(cached)
        expiry = token_expiry(cached)
        if token and expiry and expiry > datetime.now(timezone.utc) + TOKEN_EXPIRY_BUFFER:
            self._access_token = token
            return token

        refresh_token = self.config.refresh_token or str(cached.get("refresh_token") or cached.get("refreshToken") or "")
        if not refresh_token:
            raise SchwabError("No Schwab refresh token available. Reconnect Schwab before running the live scanner.")

        refreshed = self._refresh_access_token(refresh_token)
        merged = {
            **cached,
            "access_token": refreshed["access_token"],
            "expires_at": refreshed["expires_at"],
            "refresh_token": refreshed.get("refresh_token") or refresh_token,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_token_cache(merged)
        self._access_token = refreshed["access_token"]
        return self._access_token

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params or {})}" if params else ""
        request = Request(
            f"{self.config.api_base_url.rstrip('/')}{path}{query}",
            headers={
                "Authorization": f"Bearer {self.access_token()}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = http_error_detail(exc)
            raise SchwabError(f"Schwab request failed for {path}: {exc.code} {detail}") from exc
        except URLError as exc:
            raise SchwabError(f"Schwab request failed for {path}: {exc}") from exc

    def _refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        basic = base64.b64encode(f"{self.config.app_key}:{self.config.app_secret}".encode("utf-8")).decode("utf-8")
        body = urlencode({"grant_type": "refresh_token", "refresh_token": refresh_token}).encode("utf-8")
        request = Request(
            f"{self.config.auth_base_url.rstrip('/')}/v1/oauth/token",
            data=body,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = http_error_detail(exc)
            raise SchwabError(f"Schwab token refresh failed: {exc.code} {detail}") from exc
        except URLError as exc:
            raise SchwabError(f"Schwab token refresh failed: {exc}") from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise SchwabError("Schwab token refresh returned no access token.")

        expires_in = int(payload.get("expires_in") or 1800)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 60))
        return {
            "access_token": access_token,
            "expires_at": expires_at.isoformat(),
            "refresh_token": payload.get("refresh_token") or refresh_token,
        }

    def _read_token_cache(self) -> dict[str, Any]:
        try:
            return json.loads(self.config.token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_token_cache(self, payload: dict[str, Any]) -> None:
        self.config.token_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config.token_path.with_suffix(self.config.token_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.config.token_path)


def load_env_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def token_value(payload: dict[str, Any]) -> str:
    return str(payload.get("access_token") or payload.get("accessToken") or "")


def token_expiry(payload: dict[str, Any]) -> datetime | None:
    raw = payload.get("expires_at") or payload.get("accessTokenExpiresAt")
    if not raw:
        return None
    try:
        expiry = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if expiry.tzinfo is None:
        return expiry.replace(tzinfo=timezone.utc)
    return expiry.astimezone(timezone.utc)


def http_error_detail(exc: HTTPError) -> str:
    raw = exc.read()
    if exc.headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw.decode("utf-8", errors="replace")
