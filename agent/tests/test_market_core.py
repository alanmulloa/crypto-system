import unittest

from app.market.indicators import atr, ema, market_structure, rsi, snapshot, volume_ratio
from app.market.regime import detect_regime
from app.market.types import MarketRegime
from tests.helpers import make_candles


class MarketIndicatorsTest(unittest.TestCase):
    def test_indicators_are_deterministic(self):
        candles = make_candles()
        values = [c.close for c in candles]
        self.assertGreater(ema(values, 20), ema(values, 50))
        self.assertGreaterEqual(rsi(values), 50)
        self.assertGreater(atr(candles), 0)
        self.assertGreater(volume_ratio(candles), 1)
        self.assertEqual(market_structure(candles), "higher_highs_higher_lows")

    def test_regime_detects_bullish_trend(self):
        result = detect_regime(snapshot(make_candles(volatility=0.25)))
        self.assertEqual(result, MarketRegime.BULLISH)

    def test_regime_prioritizes_extreme_volatility(self):
        result = detect_regime(snapshot(make_candles(start=10.0, step=0.01, volatility=2.0)))
        self.assertEqual(result, MarketRegime.HIGH_VOLATILITY)


if __name__ == "__main__":
    unittest.main()
