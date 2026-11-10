from app.config import Settings
from app.models import Direction, StrategySignal
from app.risk.manager import evaluate_risk


def make_signal():
    return StrategySignal(symbol="BTCUSDT", strategy="trend", direction=Direction.BUY, score=80, confidence=75)


def test_kill_switch_blocks_trade():
    settings = Settings(kill_switch=True)
    result = evaluate_risk(make_signal(), settings, cash_usd=1000, open_positions=0)
    assert result.approved is False


def test_trade_allowed_when_limits_ok():
    settings = Settings(kill_switch=False, max_position_usd=250, min_cash_reserve_pct=25)
    result = evaluate_risk(make_signal(), settings, cash_usd=1000, open_positions=0)
    assert result.approved is True
    assert result.max_notional_usd == 250
