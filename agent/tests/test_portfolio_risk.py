from app.config import Settings
from app.portfolio import AllocationTarget, CapitalState, PortfolioPosition, PortfolioSnapshot
from app.risk import RiskState, evaluate_portfolio_risk
from app.strategies import AggregatedAssessment, HypothesisDirection, StrategyState


def aggregate(
    *,
    state=StrategyState.WATCH,
    direction=HypothesisDirection.BUY,
):
    return AggregatedAssessment(
        symbol="BTCUSDT",
        state=state,
        direction=direction,
        score=80,
        confidence=75,
        supporting_strategies=("trend_following", "momentum"),
    )


def portfolio(
    *,
    btc_value=1000,
    usdc_value=5000,
    daily_buy_used=0,
    daily_pnl=0,
    max_btc_pct=40,
):
    return PortfolioSnapshot(
        positions=(
            PortfolioPosition("BTC", 0.02, btc_value, capital_state=CapitalState.PROFITS_ONLY),
            PortfolioPosition("USDC", usdc_value, usdc_value, capital_state=CapitalState.CASH_RESERVE),
        ),
        allocations=(AllocationTarget("BTC", 20, max_btc_pct, "Alta"),),
        daily_buy_used_usd=daily_buy_used,
        daily_realized_pnl_usd=daily_pnl,
    )


def test_watch_buy_is_capped_by_hard_max_position():
    settings = Settings(
        kill_switch=False,
        max_position_usd=250,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=25,
    )
    result = evaluate_portfolio_risk(aggregate(), portfolio(), settings)
    assert result.state is RiskState.APPROVED
    assert result.approved is True
    assert result.max_notional_usd == 250


def test_unknown_daily_realized_pnl_blocks_new_buy():
    settings = Settings(kill_switch=False)
    result = evaluate_portfolio_risk(
        aggregate(),
        portfolio(daily_pnl=None),
        settings,
    )
    assert result.approved is False
    assert "daily realized PnL is unavailable" in " ".join(result.reasons)


def test_wait_never_approves_even_if_portfolio_has_capacity():
    settings = Settings(kill_switch=False)
    result = evaluate_portfolio_risk(
        aggregate(state=StrategyState.WAIT),
        portfolio(),
        settings,
    )
    assert result.approved is False
    assert result.state is RiskState.BLOCKED


def test_kill_switch_blocks_portfolio_risk():
    result = evaluate_portfolio_risk(aggregate(), portfolio(), Settings(kill_switch=True))
    assert result.approved is False
    assert "kill switch is active" in result.reasons


def test_cash_reserve_can_reduce_notional_below_hard_limit():
    settings = Settings(
        kill_switch=False,
        max_position_usd=1000,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=80,
    )
    result = evaluate_portfolio_risk(
        aggregate(),
        portfolio(btc_value=1000, usdc_value=5000, max_btc_pct=100),
        settings,
    )
    assert result.approved is True
    assert result.max_notional_usd == 200


def test_asset_max_weight_blocks_further_buying():
    settings = Settings(
        kill_switch=False,
        max_position_usd=500,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=10,
    )
    result = evaluate_portfolio_risk(
        aggregate(),
        portfolio(btc_value=3000, usdc_value=3000, max_btc_pct=40),
        settings,
    )
    assert result.approved is False
    assert "asset is already at or above its maximum portfolio weight" in result.reasons


def test_daily_buy_limit_is_enforced():
    settings = Settings(
        kill_switch=False,
        max_position_usd=500,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=10,
    )
    result = evaluate_portfolio_risk(
        aggregate(),
        portfolio(daily_buy_used=1000),
        settings,
    )
    assert result.approved is False
    assert "daily buy limit reached" in result.reasons


def test_daily_loss_limit_is_enforced():
    settings = Settings(
        kill_switch=False,
        daily_loss_limit_usd=100,
    )
    result = evaluate_portfolio_risk(
        aggregate(),
        portfolio(daily_pnl=-100),
        settings,
    )
    assert result.approved is False
    assert "daily loss limit reached" in result.reasons


def test_sell_hypothesis_never_creates_short_or_execution():
    settings = Settings(kill_switch=False)
    result = evaluate_portfolio_risk(
        aggregate(direction=HypothesisDirection.SELL),
        portfolio(),
        settings,
    )
    assert result.state is RiskState.NO_ACTION
    assert result.approved is False
    assert result.max_notional_usd == 0
