from app.market.binance_public import BinancePublicClient, INTERVAL_MS


def row(open_time, interval="1h", close=100.0):
    step = INTERVAL_MS[interval]
    return [
        open_time,
        str(close - 1),
        str(close + 1),
        str(close - 2),
        str(close),
        "10",
        open_time + step - 1,
        "1000",
        20,
        "0",
        "0",
        "0",
    ]


def test_historical_klines_paginates_and_deduplicates():
    step = INTERVAL_MS["1h"]
    calls = []

    def transport(path, params):
        calls.append((path, dict(params)))
        start = int(params["startTime"])
        if start == 0:
            return [row(0), row(step)]
        if start == 2 * step:
            return [row(2 * step), row(2 * step)]
        return []

    client = BinancePublicClient(
        transport=transport,
        now_ms=lambda: 10 * step,
    )
    candles = client.historical_klines(
        "BTCUSDT",
        "1h",
        start_time_ms=0,
        end_time_ms=5 * step,
        page_limit=2,
    )
    assert [item.open_time_ms for item in candles] == [0, step, 2 * step]
    assert len(calls) == 3


def test_historical_klines_excludes_unclosed_candle():
    step = INTERVAL_MS["1h"]

    def transport(path, params):
        return [row(0), row(step), row(2 * step)]

    client = BinancePublicClient(
        transport=transport,
        now_ms=lambda: 2 * step + step // 2,
    )
    candles = client.historical_klines(
        "BTCUSDT",
        "1h",
        start_time_ms=0,
        end_time_ms=10 * step,
    )
    assert [item.open_time_ms for item in candles] == [0, step]


def test_historical_klines_rejects_unsupported_interval():
    client = BinancePublicClient(transport=lambda path, params: [])
    try:
        client.historical_klines(
            "BTCUSDT",
            "2h",
            start_time_ms=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected unsupported interval to fail")
