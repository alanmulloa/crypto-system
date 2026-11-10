from app.market.types import Candle


def make_candles(count: int = 160, *, start: float = 100.0, step: float = 0.4, volatility: float = 1.0):
    candles = []
    price = start
    for i in range(count):
        open_price = price
        close = price + step
        high = max(open_price, close) + volatility
        low = min(open_price, close) - volatility
        candles.append(
            Candle(
                open_time_ms=i * 60_000,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000.0 + i * 5,
                close_time_ms=(i + 1) * 60_000 - 1,
                quote_volume=(1000.0 + i * 5) * close,
                trades=100 + i,
            )
        )
        price = close
    return candles
