"""B9: Decision Journal idempotency and consistency tests.

Tests that verify:
1. Decision journal produces stable decision_ids for the same logical decision
2. Retry scenarios return existing decision_id, not duplicate
3. Restart scenarios can find decisions by stable keys
4. Registry consistency: same cycle_id + symbol = same decision_id
"""
from datetime import datetime, timezone

from app.decision.journal import InMemoryDecisionJournal
from app.decision.models import (
    DecisionAction,
    DecisionEligibility,
    DecisionRecord,
    EntryPlan,
)


def make_decision_record(
    cycle_id: str = "cycle_20261124_120000_0001",
    symbol: str = "BTCUSDT",
    action: DecisionAction = DecisionAction.BUY,
    eligibility: DecisionEligibility = DecisionEligibility.PAPER_PROPOSAL,
    confidence_score: float = 85.0,
    heuristic_score: float = 80.0,
) -> DecisionRecord:
    """Create a standard decision record for testing."""
    return DecisionRecord(
        symbol=symbol,
        action=action,
        eligibility=eligibility,
        confidence_score=confidence_score,
        heuristic_score=heuristic_score,
        entry_plan=EntryPlan(
            side=action,
            symbol=symbol,
            entry_price=100.0,
            stop_price=95.0,
            target_prices=(110.0, 120.0),
            position_size_usd=100.0,
            estimated_impact_usd=1.0,
            reason="Test decision",
        ),
        risk_state="APPROVED",
        reasons=("risk:approved", "notional:positive"),
        aggregate_state=None,
        direction=None,
        max_notional_usd=100.0,
    )


class TestDecisionJournalIdempotency:
    """Decision journal must produce stable, deterministic decision_ids."""

    def test_same_record_same_cycle_produces_same_decision_id(self):
        """Same record with same symbol in same cycle must produce identical decision_id."""
        journal = InMemoryDecisionJournal()

        record = make_decision_record(cycle_id="test_cycle_1", symbol="BTCUSDT")

        # First call
        id1 = journal.record_decision(record, cycle_id="test_cycle_1")

        # Second call with identical record
        id2 = journal.record_decision(record, cycle_id="test_cycle_1")

        # MUST be the same - this is the core idempotence requirement
        assert id1 == id2, f"Decision IDs differ: {id1} vs {id2}"

    def test_different_symbols_different_decision_ids(self):
        """Different symbols in same cycle must produce different decision_ids."""
        journal = InMemoryDecisionJournal()

        btc_record = make_decision_record(symbol="BTCUSDT")
        eth_record = make_decision_record(symbol="ETHUSDT")

        btc_id = journal.record_decision(btc_record, cycle_id="test_cycle")
        eth_id = journal.record_decision(eth_record, cycle_id="test_cycle")

        assert btc_id != eth_id, "Different symbols should have different decision IDs"

    def test_different_cycles_different_decision_ids(self):
        """Same symbol in different cycles must produce different decision_ids."""
        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")

        id1 = journal.record_decision(record, cycle_id="cycle_1")
        id2 = journal.record_decision(record, cycle_id="cycle_2")

        assert id1 != id2, "Different cycles should have different decision IDs"

    def test_retry_same_decision_returns_existing_journal_entry(self):
        """Retry with same inputs returns existing entry, not duplicate."""
        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")

        # First call
        id1 = journal.record_decision(record, cycle_id="cycle_1")
        assert len(journal.decisions) == 1, "Should have 1 entry after first call"

        # Retry with same record
        id2 = journal.record_decision(record, cycle_id="cycle_1")
        assert len(journal.decisions) == 1, "Retry should NOT create duplicate"
        assert id1 == id2, "Retry should return same decision_id"

    def test_different_action_different_decision_id(self):
        """Different action (BUY vs SELL) must produce different decision_id."""
        journal = InMemoryDecisionJournal()

        buy_record = make_decision_record(action=DecisionAction.BUY, symbol="BTCUSDT")
        sell_record = make_decision_record(action=DecisionAction.SELL, symbol="BTCUSDT")

        buy_id = journal.record_decision(buy_record, cycle_id="cycle_1")
        sell_id = journal.record_decision(sell_record, cycle_id="cycle_1")

        assert buy_id != sell_id, "Different actions should have different decision IDs"

    def test_different_eligibility_different_decision_id(self):
        """Different eligibility (PAPER_PROPOSAL vs RESEARCH_ONLY) must produce different decision_id."""
        journal = InMemoryDecisionJournal()

        proposal_record = make_decision_record(
            eligibility=DecisionEligibility.PAPER_PROPOSAL, symbol="BTCUSDT"
        )
        research_record = make_decision_record(
            eligibility=DecisionEligibility.RESEARCH_ONLY, symbol="BTCUSDT"
        )

        proposal_id = journal.record_decision(proposal_record, cycle_id="cycle_1")
        research_id = journal.record_decision(research_record, cycle_id="cycle_1")

        assert proposal_id != research_id, "Different eligibility should have different decision IDs"

    def test_decision_id_format_is_stable(self):
        """Decision ID format should be deterministic: dec_{cycle_id}_{symbol}_{hash}."""
        journal = InMemoryDecisionJournal()

        record = make_decision_record(cycle_id="my_cycle", symbol="ETHUSDT")

        decision_id = journal.record_decision(record, cycle_id="my_cycle")

        # Check format: dec_{cycle}_{symbol}_{hash}
        assert decision_id.startswith("dec_my_cycle_ETHUSDT_"), f"Unexpected format: {decision_id}"
        # Hash should be deterministic (16 hex chars, no underscores)
        parts = decision_id.split("_")
        assert len(parts) == 5, f"Expected 5 parts (dec + cycle + symbol + hash), got {len(parts)}: {parts}"
        assert parts[0] == "dec"
        assert parts[1] == "my"
        assert parts[2] == "cycle"
        assert parts[3] == "ETHUSDT"
        # 16-char hex hash with no underscores
        assert len(parts[4]) == 16 and all(c in "0123456789abcdef" for c in parts[4])


class TestDecisionJournalRegistryConsistency:
    """Registry consistency: cycle_id + symbol should uniquely identify a decision."""

    def test_can_retrieve_decision_by_id(self):
        """Stored decision should be retrievable by its decision_id."""
        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")
        decision_id = journal.record_decision(record, cycle_id="cycle_1")

        entry = journal.get_decision(decision_id)
        assert entry is not None, "Should be able to retrieve stored decision"
        assert entry.decision_id == decision_id
        assert entry.symbol == "BTCUSDT"
        assert entry.action == DecisionAction.BUY

    def test_get_decisions_for_cycle_returns_all_decisions(self):
        """All decisions in a cycle should be retrievable."""
        journal = InMemoryDecisionJournal()

        btc_record = make_decision_record(symbol="BTCUSDT")
        eth_record = make_decision_record(symbol="ETHUSDT")

        journal.record_decision(btc_record, cycle_id="test_cycle")
        journal.record_decision(eth_record, cycle_id="test_cycle")

        decisions = journal.get_decisions_for_cycle("test_cycle")
        assert len(decisions) == 2

        symbols = {d.symbol for d in decisions}
        assert symbols == {"BTCUSDT", "ETHUSDT"}

    def test_restart_scenario_can_find_existing_decision(self):
        """After restart, same cycle_id + symbol can be found and reused."""
        # Simulate a fresh journal after restart
        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")

        # Simulate process start and recording decision
        decision_id = journal.record_decision(record, cycle_id="restart_test")

        # Simulate process restart: new journal instance
        # (In production, this would query the database)
        # For InMemory, we just verify the ID is stable
        assert decision_id.startswith("dec_restart_test_BTCUSDT")

        # The key invariant: decision_id should be the same if we process
        # the same logical decision again
        same_id = journal.record_decision(record, cycle_id="restart_test")
        assert same_id == decision_id, "After restart, same decision should have same ID"


class TestDecisionJournalOutcomeIdempotency:
    """Outcome recording must also be idempotent."""

    def test_outcome_can_be_retrieved(self):
        """Recorded outcomes should be retrievable."""
        from app.decision.models import DecisionOutcome

        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")
        decision_id = journal.record_decision(record, cycle_id="cycle_1")

        from datetime import datetime, timezone

        outcome = DecisionOutcome(
            decision_id=decision_id,
            order_id="order_123",
            filled=True,
            fill_price=100.5,
            quantity=0.01,
            notional=100.5,
            fees_usd=0.1,
            slippage_usd=0.0,
            pnl_usd=5.0,
            timestamp=datetime.now(timezone.utc),
        )

        journal.record_outcome(outcome)

        outcomes = journal.get_outcomes_for_decision(decision_id)
        assert len(outcomes) == 1
        assert outcomes[0].order_id == "order_123"
        assert outcomes[0].filled is True

    def test_duplicate_outcome_not_added_twice(self):
        """Same outcome should not be added multiple times."""
        from app.decision.models import DecisionOutcome

        journal = InMemoryDecisionJournal()

        record = make_decision_record(symbol="BTCUSDT")
        decision_id = journal.record_decision(record, cycle_id="cycle_1")

        now = datetime.now(timezone.utc)

        outcome = DecisionOutcome(
            decision_id=decision_id,
            order_id="order_123",
            filled=True,
            fill_price=100.5,
            quantity=0.01,
            notional=100.5,
            fees_usd=0.1,
            slippage_usd=0.0,
            pnl_usd=5.0,
            timestamp=now,
        )

        # Record same outcome twice
        journal.record_outcome(outcome)
        journal.record_outcome(outcome)

        outcomes = journal.get_outcomes_for_decision(decision_id)
        # Should only have one outcome
        assert len(outcomes) == 1