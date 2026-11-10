from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.market.types import Candle, SymbolInfo, Ticker24h


BINANCE_PUBLIC_BASE_URL = "https://api.binance.com"


class BinancePublicError(RuntimeError):
    pass


Transport = Callable[[str, dict[str, str | int | None]], Any]
Sleep = Callable[[float], None]
ClockMs = Callable[[], int]


def _unix_time_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class BinancePublicClient:
    base_url: str = BINANCE_PUBLIC_BASE_URL
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_seconds: float = 0.5
    transport: Transport | None = None
    sleep_func: Sleep = time.sleep
    now_ms: ClockMs = _unix_time_ms

    def _get(self, path: str, params: dict[str, str | int | None] | None = None) -> Any:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        if self.transport is not None:
            return self.transport(path, clean_params)

        query = urlencode(clean_params)
        url = f"{self.base_url.rstrip('/')}{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"User-Agent": "crypto-system-market-intelligence/0.2"})

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - operator-configured Binance base URL
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                retryable = exc.code in {418, 429} or 500 <= exc.code <= 599
                if not retryable or attempt >= self.max_retries:
                    raise BinancePublicError(
                        f"Binance public request failed for {path} with HTTP {exc.code}"
                    ) from exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after and retry_after.isdigit() else self.backoff_seconds * (2**attempt)
                self.sleep_func(delay)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt >= self.max_retries:
                    raise BinancePublicError(f"Binance public request failed for {path}: {exc}") from exc
                self.sleep_func(self.backoff_seconds * (2**attempt))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise BinancePublicError(f"Invalid Binance response for {path}: {exc}") from exc

        raise BinancePublicError(f"Binance public request failed for {path}")

    def exchange_info(self) -> list[SymbolInfo]:
        payload = self._get("/api/v3/exchangeInfo", {"symbolStatus": "TRADING"})
        result: list[SymbolInfo] = []
        for item in payload.get("symbols", []):
            permissions = set(item.get("permissions") or [])
            permission_sets = item.get("permissionSets") or []
            spot_allowed = bool(item.get("isSpotTradingAllowed", True))
            if permissions and "SPOT" not in permissions:
                spot_allowed = any("SPOT" in group for group in permission_sets)
            result.append(
                SymbolInfo(
                    symbol=item["symbol"],
                    base_asset=item["baseAsset"],
                    quote_asset=item["quoteAsset"],
                    status=item.get("status", ""),
                    spot_allowed=spot_allowed,
                )
            )
        return result

    def tickers_24h(self) -> dict[str, Ticker24h]:
        payload = self._get("/api/v3/ticker/24hr")
        if isinstance(payload, dict):
            payload = [payload]
        result: dict[str, Ticker24h] = {}
        for item in payload:
            symbol = item.get("symbol")
            if not symbol:
                continue
            result[symbol] = Ticker24h(
                symbol=symbol,
                last_price=float(item.get("lastPrice") or 0.0),
                quote_volume=float(item.get("quoteVolume") or 0.0),
                price_change_pct=float(item.get("priceChangePercent") or 0.0),
                trade_count=int(item.get("count") or 0),
            )
        return result

    def klines(self, symbol: str, interval: str, limit: int = 250) -> list[Candle]:
        payload = self._get(
            "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        now_ms = self.now_ms()
        candles: list[Candle] = []
        for row in payload:
            if len(row) < 9:
                continue
            close_time_ms = int(row[6])
            # Binance may include the currently forming candle. Phase 1 only exposes
            # fully closed candles so later strategies cannot accidentally look ahead.
            if close_time_ms > now_ms:
                continue
            candles.append(
                Candle(
                    open_time_ms=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    close_time_ms=close_time_ms,
                    quote_volume=float(row[7]),
                    trades=int(row[8]),
                )
            )
        return candles
