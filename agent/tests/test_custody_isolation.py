"""B9: Real/PAPER custody isolation tests.

Tests that:
1. Real portfolio positions and PAPER positions are NEVER merged in _paper_overlay.
2. Risk evaluation filters by custody_sources correctly.
3. PAPER execution cannot see or use REAL positions.
4. The overlay marks real positions with ("REAL",) and paper with ("PAPER",).
"""
from datetime import datetime, timezone


from app.config import Settings
from app.execution import InMemoryPaperExecutionRepository, PaperBroker, PaperExecutionOrchestrator
from app.execution.paper import PaperOrderRequest, PaperOrderType, PaperSide
from app.execution.paper_loop import PaperTradingLoop, StaticPortfolioSource
from app.market.types import IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.portfolio import AllocationTarget, CapitalState, PortfolioPosition, PortfolioSnapshot
from app.risk.portfolio import evaluate_portfolio_risk
from app.strategies.aggregator import AggregatedAssessment
from app.strategies.base import HypothesisDirection, StrategyState


NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def frame(interval, *, price=100, regime=MarketRegime.BULLISH, volume=1.5):
    return TimeframeAnalysis(
        interval=interval,
        candles=200,
        last_price=price,
        indicators=IndicatorSnapshot(
            ema_fast=102,
            ema_slow=98,
            rsi=58,
            atr=2,
            atr_pct=2,
            volume_ratio=volume,
            structure="higher_highs_higher_lows",
        ),
        regime=regime,
    )


def bullish_candidate(symbol="BTCUSDT", price=100):
    return MarketCandidate(
        symbol=symbol,
        base_asset=symbol.replace("USDT", ""),
        quote_asset="USDT",
        quote_volume_24h=1_000_000_000,
        price_change_pct_24h=2,
        trade_count_24h=1_000_000,
        analyses=(
            frame("15m", price=price),
            frame("1h", price=price),
            frame("4h", price=price),
            frame("1d", price=price),
        ),
    )


class StaticCandidates:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def run_scan(self):
        self.calls += 1
        return list(self.candidates)


def make_settings(**overrides):
    values = dict(
        paper_loop_enabled=True,
        kill_switch=False,
        paper_default_order_usd=100,
        max_position_usd=250,
        max_daily_buy_usd=1000,
        min_cash_reserve_pct=10,
        max_open_positions=5,
        daily_loss_limit_usd=100,
    )
    values.update(overrides)
    return Settings(**values)


def make_real_portfolio_with_btc(*, btc_value=5000, usdc_value=1000):
    """Real portfolio with BTC held in real custody and some cash."""
    return PortfolioSnapshot(
        positions=(
            PortfolioPosition(
                "BTC",
                0.05,
                btc_value,
                capital_state=CapitalState.CAPITAL_AT_RISK,
                custody_sources=("REAL",),
            ),
            PortfolioPosition(
                "USDC",
                usdc_value,
                usdc_value,
                capital_state=CapitalState.CASH_RESERVE,
                custody_sources=("REAL",),
            ),
        ),
        allocations=(AllocationTarget("BTC", 20, 60, "Alta"),),
        daily_buy_used_usd=0.0,
        daily_realized_pnl_usd=0.0,
    )


class TestCustodyIsolationOverlay:
    """Test that _paper_overlay separates REAL and PAPER positions."""

    def test_overlay_marks_real_positions_with_real_custody(self):
        """Real portfolio positions get custody_sources=("REAL",) in overlay."""
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())
        real_portfolio = make_real_portfolio_with_btc()
        loop = PaperTradingLoop(
            candidate_source=StaticCandidates([]),
            portfolio_source=StaticPortfolioSource(real_portfolio),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(),
        )

        overlay = loop._paper_overlay(real_portfolio, {}, NOW)

        # Find the real BTC position in the overlay
        real_btc = None
        for pos in overlay.positions:
            if pos.asset == "BTC":
                real_btc = pos
                break

        assert real_btc is not None
        assert "REAL" in real_btc.custody_sources

    def test_overlay_marks_paper_positions_with_paper_custody(self):
        """Paper positions from broker get custody_sources=("PAPER",) in overlay."""
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        # Create a paper position
        broker.submit(
            PaperOrderRequest(
                idempotency_key="paper-btc-buy",
                symbol="BTCUSDT",
                side=PaperSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=0.005,
            ),
            market_price=100.0,
            now=NOW,
        )

        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())
        real_portfolio = make_real_portfolio_with_btc()
        loop = PaperTradingLoop(
            candidate_source=StaticCandidates([]),
            portfolio_source=StaticPortfolioSource(real_portfolio),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(),
        )

        overlay = loop._paper_overlay(real_portfolio, {"BTCUSDT": 100.0}, NOW)

        # Find paper BTC positions (custody PAPER)
        paper_btc = [p for p in overlay.positions if p.asset == "BTC" and "PAPER" in p.custody_sources]
        real_btc = [p for p in overlay.positions if p.asset == "BTC" and "REAL" in p.custody_sources]

        assert len(paper_btc) >= 1, "Expected at least one PAPER BTC position"
        assert len(real_btc) >= 1, "Expected at least one REAL BTC position"

    def test_real_and_paper_btc_are_never_merged(self):
        """REAL and PAPER BTC positions must NOT be merged into one position."""
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        broker.submit(
            PaperOrderRequest(
                idempotency_key="paper-btc-buy",
                symbol="BTCUSDT",
                side=PaperSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=0.005,
            ),
            market_price=100.0,
            now=NOW,
        )

        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())
        real_portfolio = make_real_portfolio_with_btc()
        loop = PaperTradingLoop(
            candidate_source=StaticCandidates([]),
            portfolio_source=StaticPortfolioSource(real_portfolio),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(),
        )

        overlay = loop._paper_overlay(real_portfolio, {"BTCUSDT": 100.0}, NOW)

        # There should be exactly 2 BTC positions: one REAL, one PAPER
        btc_positions = [p for p in overlay.positions if p.asset == "BTC"]
        real_btc = [p for p in btc_positions if "REAL" in p.custody_sources]
        paper_btc = [p for p in btc_positions if "PAPER" in p.custody_sources]

        # The key invariant: they are separate entries
        assert len(real_btc) == 1
        assert len(paper_btc) == 1
        # And their quantities are NOT added together
        assert real_btc[0].quantity != paper_btc[0].quantity

    def test_cash_is_separate_for_real_and_paper(self):
        """REAL USDC and PAPER USDC are separate positions."""
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())
        real_portfolio = make_real_portfolio_with_btc(usdc_value=5000)
        loop = PaperTradingLoop(
            candidate_source=StaticCandidates([]),
            portfolio_source=StaticPortfolioSource(real_portfolio),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(),
        )

        overlay = loop._paper_overlay(real_portfolio, {}, NOW)

        real_usdc = [p for p in overlay.positions if p.asset == "USDC" and "REAL" in p.custody_sources]
        paper_usdc = [p for p in overlay.positions if p.asset == "USDC" and "PAPER" in p.custody_sources]

        assert len(real_usdc) == 1
        assert len(paper_usdc) == 1
        assert real_usdc[0].market_value_usd == 5000.0
        assert paper_usdc[0].market_value_usd == 1000.0  # broker cash


class TestCustodyFilteredRisk:
    """Test that risk evaluation respects custody_sources filter."""

    def test_paper_cash_does_not_include_real_cash(self):
        """cash_value_usd with ("PAPER",) filter excludes REAL cash."""
        real_portfolio = make_real_portfolio_with_btc(usdc_value=5000)
        paper_cash = real_portfolio.cash_value_usd(custody_sources=("PAPER",))
        real_cash = real_portfolio.cash_value_usd(custody_sources=("REAL",))
        assert paper_cash == 0.0
        assert real_cash == 5000.0

    def test_paper_total_excludes_real_positions(self):
        """total_value_usd with ("PAPER",) filter excludes REAL positions."""
        real_portfolio = make_real_portfolio_with_btc(btc_value=5000, usdc_value=1000)
        paper_total = real_portfolio.total_value_usd(custody_sources=("PAPER",))
        real_total = real_portfolio.total_value_usd(custody_sources=("REAL",))
        assert paper_total == 0.0
        assert real_total == 6000.0

    def test_risk_evaluation_with_paper_custody_sees_zero_cash(self):
        """Risk evaluation with ("PAPER",) custody sees zero cash from real portfolio."""
        real_portfolio = make_real_portfolio_with_btc()
        aggregate = AggregatedAssessment(
            symbol="BTCUSDT",
            state=StrategyState.WATCH,
            direction=HypothesisDirection.BUY,
            score=80.0,
            confidence=75.0,
            supporting_strategies=("momentum",),
        )
        risk = evaluate_portfolio_risk(
            aggregate,
            real_portfolio,
            make_settings(),
            custody_sources=("PAPER",),
        )
        # Should be BLOCKED because there's no PAPER cash in the real portfolio
        assert risk.approved is False
        assert risk.max_notional_usd == 0.0
        assert "no cash reserve available" in risk.reasons


class TestCustodyFilteredPosition:
    """Test that position_for filters by custody_sources."""

    def test_position_for_paper_custody_returns_none_for_real_only(self):
        """position_for with PAPER filter returns None when only REAL position exists."""
        real_portfolio = make_real_portfolio_with_btc()
        position = real_portfolio.position_for("BTC", custody_sources=("PAPER",))
        assert position is None

    def test_position_for_real_custody_returns_real_position(self):
        """position_for with REAL filter returns the real position."""
        real_portfolio = make_real_portfolio_with_btc()
        position = real_portfolio.position_for("BTC", custody_sources=("REAL",))
        assert position is not None
        assert position.market_value_usd == 5000.0

    def test_position_for_no_filter_returns_first_match(self):
        """position_for without filter returns first matching position."""
        real_portfolio = make_real_portfolio_with_btc()
        position = real_portfolio.position_for("BTC")
        assert position is not None
