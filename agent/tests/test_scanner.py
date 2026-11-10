import unittest

from app.market.scanner import MarketScanner, ScannerConfig, is_allowed_symbol
from app.market.types import SymbolInfo, Ticker24h
from tests.helpers import make_candles


class FakeClient:
    def __init__(self):
        self.kline_calls = []

    def exchange_info(self):
        return [
            SymbolInfo("BTCUSDT", "BTC", "USDT", "TRADING", True),
            SymbolInfo("USDCUSDT", "USDC", "USDT", "TRADING", True),
            SymbolInfo("BTCUPUSDT", "BTCUP", "USDT", "TRADING", True),
            SymbolInfo("LOWUSDT", "LOW", "USDT", "TRADING", True),
        ]

    def tickers_24h(self):
        return {
            "BTCUSDT": Ticker24h("BTCUSDT", 65000, 900_000_000, 2.0, 1_000_000),
            "USDCUSDT": Ticker24h("USDCUSDT", 1, 800_000_000, 0.0, 500_000),
            "BTCUPUSDT": Ticker24h("BTCUPUSDT", 10, 50_000_000, 10.0, 50_000),
            "LOWUSDT": Ticker24h("LOWUSDT", 1, 100_000, 1.0, 100),
        }

    def klines(self, symbol, interval, limit=250):
        self.kline_calls.append((symbol, interval, limit))
        return make_candles(limit, volatility=0.25)


class MarketScannerTest(unittest.TestCase):
    def test_symbol_filter(self):
        self.assertTrue(is_allowed_symbol(SymbolInfo("BTCUSDT", "BTC", "USDT", "TRADING", True)))
        self.assertFalse(is_allowed_symbol(SymbolInfo("USDCUSDT", "USDC", "USDT", "TRADING", True)))
        self.assertFalse(is_allowed_symbol(SymbolInfo("BTCUPUSDT", "BTCUP", "USDT", "TRADING", True)))
        self.assertFalse(is_allowed_symbol(SymbolInfo("WBTCUSDT", "WBTC", "USDT", "TRADING", True)))

    def test_scanner_filters_and_analyzes_all_required_timeframes(self):
        client = FakeClient()
        scanner = MarketScanner(client, ScannerConfig(prefilter_limit=10, candidate_limit=5))
        results = scanner.scan()
        self.assertEqual([item.symbol for item in results], ["BTCUSDT"])
        self.assertEqual({item.interval for item in results[0].analyses}, {"15m", "1h", "4h", "1d"})
        self.assertEqual(len(client.kline_calls), 4)
        self.assertGreater(results[0].ranking_score, 0)

    def test_insufficient_history_is_rejected(self):
        client = FakeClient()

        def short_klines(symbol, interval, limit=250):
            return make_candles(60)

        client.klines = short_klines
        scanner = MarketScanner(client, ScannerConfig(min_candles=120))
        self.assertEqual(scanner.scan(), [])


if __name__ == "__main__":
    unittest.main()
