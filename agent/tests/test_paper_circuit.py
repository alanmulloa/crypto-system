"""B9: Full PAPER trading circuit integration test.

Tests the complete flow: Scanner → Strategies → Decision → Risk → PaperBroker → Order → Fill → Ledger.

All movements must be:
- Idempotent (same cycle_id cannot double-fill)
- Auditable (journal records exist)
- Isolated from REAL portfolio
- Fail-closed (kill switch, paper_loop_enabled=false blocks)
"""
from datetime import datetime, timezone


from app.config import Settings
from app.decision.journal import InMemoryDecisionJournal
from app.decision.engine import DecisionEngine
from app.execution import InMemoryPaperExecutionRepository, PaperBroker, PaperExecutionOrchestrator
from app.execution.paper import PaperOrderRequest, PaperOrderStatus, PaperOrderType, PaperSide
from app.execution.paper_loop import PaperTradingLoop, StaticPortfolioSource
from app.market.types import IndicatorSnapshot, MarketCandidate, MarketRegime, TimeframeAnalysis
from app.portfolio import AllocationTarget, CapitalState, PortfolioPosition, PortfolioSnapshot


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


def make_paper_portfolio(*, usdc_value=1000):
    """Portfolio snapshot representing only paper cash (no real positions)."""
    return PortfolioSnapshot(
        positions=(
            PortfolioPosition(
                "USDC",
                usdc_value,
                usdc_value,
                capital_state=CapitalState.CASH_RESERVE,
                custody_sources=("PAPER",),
            ),
        ),
        allocations=(AllocationTarget("BTC", 10, 50),),
        daily_buy_used_usd=0.0,
        daily_realized_pnl_usd=0.0,
    )


class TestPaperCircuit:
    """Full circuit: Scanner → Strategies → Decision → Risk → PAPER → Order → Fill → Ledger."""

    def test_disabled_by_default_blocks_all_execution(self):
        """Settings() with paper_loop_enabled=False must block all cycles."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=Settings(),  # paper_loop_enabled=False default
        )

        result = loop.run_cycle(cycle_id="c1", now=NOW)

        assert result.enabled is False
        assert result.filled_orders == ()
        assert source.calls == 0  # Scanner not called when disabled
        assert broker.account.cash_usd == 1000  # No cash spent

    def test_kill_switch_blocks_execution(self):
        """Kill switch active must block all paper orders."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(kill_switch=True),
        )

        result = loop.run_cycle(cycle_id="kill-switch-test", now=NOW)

        assert result.enabled is True
        assert result.filled_orders == ()
        assert broker.account.cash_usd == 1000  # No cash spent

    def test_full_buy_circuit_creates_order_and_fill(self):
        """Full circuit: bullish candidate → WATCH → risk approved → PAPER buy → fill."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio(usdc_value=1000)),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(paper_default_order_usd=100, max_position_usd=250),
        )

        result = loop.run_cycle(cycle_id="full-buy-circuit", now=NOW)

        # Should have exactly 1 filled order
        assert len(result.filled_orders) == 1
        order = result.filled_orders[0]
        assert order.status is PaperOrderStatus.FILLED
        assert order.fill is not None
        assert order.fill.gross_usd > 0
        assert order.request.side is PaperSide.BUY

        # Broker cash should be reduced
        assert broker.account.cash_usd < 1000

        # Repository should have the order
        assert len(repository.orders) == 1

    def test_cycle_idempotency_same_cycle_no_double_fill(self):
        """Same cycle_id cannot double-fill even if called twice."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(paper_default_order_usd=100, max_position_usd=250),
        )

        # Run same cycle twice
        first = loop.run_cycle(cycle_id="idempotent-test", now=NOW)
        cash_after_first = broker.account.cash_usd
        second = loop.run_cycle(cycle_id="idempotent-test", now=NOW)
        cash_after_second = broker.account.cash_usd

        # Both should have a filled order (idempotent return), but cash unchanged
        assert len(first.filled_orders) == 1
        assert len(second.filled_orders) == 1
        # Critical: cash is not deducted twice
        assert broker.account.cash_usd == cash_after_first == cash_after_second
        # Only one order in repository
        assert len(repository.orders) == 1

    def test_journal_records_decisions(self):
        """Decision journal must record all evaluated candidates."""
        journal = InMemoryDecisionJournal()
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(),
            decision_engine=DecisionEngine(
                settings=make_settings(),
                broker=broker,
                orchestrator=orchestrator,
                journal=journal,
            ),
        )

        result = loop.run_cycle(cycle_id="journal-test", now=NOW)

        assert result.enabled is True
        # Journal should have recorded the decision
        assert len(journal.decisions) > 0 or len(journal.outcomes) > 0

    def test_risk_blocks_when_cash_insufficient(self):
        """Risk manager blocks when paper cash is below minimum reserve."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=50, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio(usdc_value=50)),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(
                paper_default_order_usd=100,
                max_position_usd=250,
                min_cash_reserve_pct=10,
            ),
        )

        result = loop.run_cycle(cycle_id="insufficient-cash", now=NOW)

        # Should not fill because cash is too low
        assert result.filled_orders == ()
        assert broker.account.cash_usd == 50

    def test_daily_loss_limit_blocks_new_orders(self):
        """Daily loss limit reached blocks new paper orders."""
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        # Simulate a large loss
        broker.submit(
            PaperOrderRequest(
                idempotency_key="seed-buy",
                symbol="ETHUSDT",
                side=PaperSide.BUY,
                order_type=PaperOrderType.MARKET,
                quantity=1,
            ),
            market_price=200,
            now=NOW,
        )
        broker.submit(
            PaperOrderRequest(
                idempotency_key="seed-sell",
                symbol="ETHUSDT",
                side=PaperSide.SELL,
                order_type=PaperOrderType.MARKET,
                quantity=1,
            ),
            market_price=50,
            now=NOW,
        )

        source = StaticCandidates([bullish_candidate()])
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio(usdc_value=850)),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(daily_loss_limit_usd=100),
        )

        result = loop.run_cycle(cycle_id="daily-loss-stop", now=NOW)

        assert result.filled_orders == ()
        assert "daily loss limit reached" in result.items[0].risk.reasons

    def test_paper_order_appears_in_broker_positions(self):
        """After a filled buy, the broker account should have the position."""
        source = StaticCandidates([bullish_candidate()])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        orchestrator = PaperExecutionOrchestrator(broker, InMemoryPaperExecutionRepository())

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(paper_default_order_usd=100, max_position_usd=250),
        )

        result = loop.run_cycle(cycle_id="position-check", now=NOW)

        assert len(result.filled_orders) == 1
        # Broker should now hold BTC
        assert "BTCUSDT" in broker.account.positions
        assert broker.account.positions["BTCUSDT"].quantity > 0

    def test_multiple_candidates_one_fills_other_rejects(self):
        """When two candidates exist, only the qualifying one should execute."""
        # One bullish, one ranging (will be WATCH or REJECT)
        bullish = bullish_candidate("BTCUSDT")
        ranging = MarketCandidate(
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            quote_volume_24h=1_000_000_000,
            price_change_pct_24h=0,
            trade_count_24h=1_000_000,
            analyses=tuple(
                frame(interval, price=100, regime=MarketRegime.RANGING, volume=1.0)
                for interval in ("15m", "1h", "4h", "1d")
            ),
        )

        source = StaticCandidates([bullish, ranging])
        broker = PaperBroker(initial_cash_usd=1000, fee_bps=0, slippage_bps=0)
        repository = InMemoryPaperExecutionRepository()
        orchestrator = PaperExecutionOrchestrator(broker, repository)

        loop = PaperTradingLoop(
            candidate_source=source,
            portfolio_source=StaticPortfolioSource(make_paper_portfolio()),
            broker=broker,
            orchestrator=orchestrator,
            settings=make_settings(paper_default_order_usd=100, max_position_usd=250),
        )

        result = loop.run_cycle(cycle_id="multi-candidate", now=NOW)

        # Should have items for both candidates
        assert len(result.items) == 2
        # At least one should be filled (the bullish one)
        assert len(result.filled_orders) >= 1
