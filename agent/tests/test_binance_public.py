import unittest

from app.market.binance_public import BinancePublicClient


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


if __name__ == "__main__":
    unittest.main()
