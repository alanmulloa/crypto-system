import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from app.market.binance_public import BinancePublicClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class BinancePublicClientTest(unittest.TestCase):
    def test_parses_exchange_tickers_and_klines_with_mock_transport(self):
        def transport(path, params):
            if path.endswith("exchangeInfo"):
                return {
                    "symbols": [
                        {
                            "symbol": "BTCUSDT",
                            "baseAsset": "BTC",
                            "quoteAsset": "USDT",
                            "status": "TRADING",
                            "isSpotTradingAllowed": True,
                        }
                    ]
                }
            if path.endswith("ticker/24hr"):
                return [
                    {
                        "symbol": "BTCUSDT",
                        "lastPrice": "65000.0",
                        "quoteVolume": "900000000.0",
                        "priceChangePercent": "1.5",
                        "count": 1000000,
                    }
                ]
            if path.endswith("klines"):
                self.assertEqual(params["interval"], "4h")
                return [[0, "100", "102", "99", "101", "10", 1, "1005", 50, "0", "0", "0"]]
            raise AssertionError(path)

        client = BinancePublicClient(transport=transport)
        info = client.exchange_info()[0]
        ticker = client.tickers_24h()["BTCUSDT"]
        candle = client.klines("BTCUSDT", "4h", 1)[0]
        self.assertEqual(info.base_asset, "BTC")
        self.assertTrue(info.spot_allowed)
        self.assertEqual(ticker.quote_volume, 900000000.0)
        self.assertEqual(candle.close, 101.0)
        self.assertEqual(candle.trades, 50)

    def test_excludes_currently_forming_kline(self):
        def transport(path, params):
            self.assertTrue(path.endswith("klines"))
            return [
                [0, "100", "102", "99", "101", "10", 999, "1005", 50, "0", "0", "0"],
                [1000, "101", "103", "100", "102", "11", 1001, "1122", 51, "0", "0", "0"],
            ]

        client = BinancePublicClient(transport=transport, now_ms=lambda: 1000)
        candles = client.klines("BTCUSDT", "1h", 2)
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].close_time_ms, 999)

    def test_retries_transient_network_error(self):
        payload = {"symbols": []}
        client = BinancePublicClient(max_retries=1, backoff_seconds=0, sleep_func=lambda _: None)
        with patch(
            "app.market.binance_public.urlopen",
            side_effect=[URLError("temporary"), FakeResponse(payload)],
        ) as mocked:
            self.assertEqual(client.exchange_info(), [])
        self.assertEqual(mocked.call_count, 2)


if __name__ == "__main__":
    unittest.main()
