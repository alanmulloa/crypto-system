from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.market.types import Candle, SymbolInfo, Ticker24h


BINANCE_PUBLIC_BASE_URL = "https://api.binance.com"


class BinancePublicError(RuntimeError):
    pass


Transport = Callable[[str, dict[str, str | int | None]], Any]


@dataclass
class BinancePublicClient:
    base_url: str = BINANCE_PUBLIC_BASE_URL
    timeout_seconds: float = 10.0
    transport: Transport | None = None

    def _get(self, path: str, params: dict[str, str | int | None] | None = None) -> Any:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        if self.transport is not None:
            return self.transport(path, clean_params)

        query = urlencode(clean_params)
        url = f"{self.base_url.rstrip('/')}{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"User-Agent": "crypto-system-market-intelligence/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed Binance base URL
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - exercised by integration/runtime
            raise BinancePublicError(f"Binance public request failed for {path}: {exc}") from exc

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
        candles: list[Candle] = []
        for row in payload:
            if len(row) < 9:
                continue
            candles.append(
                Candle(
                    open_time_ms=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    close_time_ms=int(row[6]),
                    quote_volume=float(row[7]),
                    trades=int(row[8]),
                )
            )
        return candles
