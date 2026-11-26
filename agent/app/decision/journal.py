"""Decision Journal persistence layer.

Phase 2: Idempotent, auditable journal for all trading decisions.
Uses Supabase REST API for storage with deduplication via decision_id.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.decision.models import DecisionJournalEntry, DecisionOutcome, DecisionRecord


class DecisionJournal:
    """Persistent, idempotent decision journal."""

    TABLE_DECISIONS = "decision_journal"
    TABLE_OUTCOMES = "decision_outcomes"

    def __init__(self, settings: Settings):
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase URL and service role key required for DecisionJournal")
        self.url = settings.supabase_url.rstrip("/")
        self.key = settings.supabase_service_role_key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        self.timeout = 10.0

    def _request(self, method: str, path: str, data: dict | None = None) -> dict | list | None:
        """Make HTTP request to Supabase REST API."""
        import urllib.request

        url = f"{self.url}/rest/v1/{path}"
        req_data = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(
            url,
            data=req_data,
            headers=self.headers,
            method=method,
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
            content = response.read().decode("utf-8")
            return json.loads(content) if content else None

    def _decision_id_hash(self, cycle_id: str, record: DecisionRecord) -> str:
        """Generate deterministic hash for decision_id based on record content.

        Uses SHA-1 of the record's essential fields to ensure:
        - Same logical decision always produces same decision_id (idempotent)
        - Different actions/symbols/eligibility produce different IDs
        - Timestamp-independent for retry/restart scenarios
        """
        import hashlib

        # Create a deterministic snapshot of the record's identity
        # Fields that define the logical decision (not timestamp-dependent)
        hash_input = f"{cycle_id}:{record.symbol}:{record.action.value}:{record.eligibility.value}:{record.confidence_score}:{record.heuristic_score}:{record.max_notional_usd}"
        if record.entry_plan:
            hash_input += f":{record.entry_plan.side.value}:{record.entry_plan.symbol}:{record.entry_plan.entry_price}"
        if record.sizing_details_json:
            hash_input += f":{record.sizing_details_json}"

        return hashlib.sha1(hash_input.encode("utf-8")).hexdigest()[:16]


    def record_decision(self, record: DecisionRecord, cycle_id: str) -> str:
        """Record a decision with idempotency (dedup by decision_id).

        Args:
            record: Decision record to store
            cycle_id: Cycle identifier for grouping

        Returns:
            decision_id (generated or existing)
        """
        decision_id = f"dec_{cycle_id}_{record.symbol}_{self._decision_id_hash(cycle_id, record)}"

        entry = DecisionJournalEntry(
            decision_id=decision_id,
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc),
            symbol=record.symbol,
            action=record.action,
            eligibility=record.eligibility,
            confidence_score=record.confidence_score,
            entry_plan_json=json.dumps(record.entry_plan.to_dict()) if record.entry_plan else None,
            reasons_json=json.dumps(list(record.reasons)),
            warnings_json=json.dumps(list(record.warnings)),
            risk_state=record.risk_state,
            aggregate_state=record.aggregate_state if hasattr(record, 'aggregate_state') else None,
            direction=record.direction if hasattr(record, 'direction') else None,
            heuristic_score=record.heuristic_score,
            max_notional_usd=record.max_notional_usd if hasattr(record, 'max_notional_usd') else 0.0,
            sizing_details_json=record.sizing_details_json if hasattr(record, 'sizing_details_json') else None,
        )

        # Upsert: use on_conflict for idempotency
        payload = entry.to_dict()

        # Check if exists first (idempotent write)
        existing = self._request(
            "GET",
            f"{self.TABLE_DECISIONS}?decision_id=eq.{decision_id}&select=decision_id",
        )

        if existing:
            return decision_id  # Already recorded

        self._request("POST", self.TABLE_DECISIONS, payload)
        return decision_id

    def record_outcome(self, outcome: DecisionOutcome) -> None:
        """Record decision outcome (fill result).

        Idempotent by decision_id + order_id combination.
        """
        payload = outcome.to_dict()

        # Check if exists
        filters = f"decision_id=eq.{outcome.decision_id}"
        if outcome.order_id:
            filters += f"&order_id=eq.{outcome.order_id}"

        existing = self._request("GET", f"{self.TABLE_OUTCOMES}?{filters}&select=decision_id")

        if not existing:
            self._request("POST", self.TABLE_OUTCOMES, payload)

    def get_decision(self, decision_id: str) -> DecisionJournalEntry | None:
        """Retrieve a single decision by ID."""
        rows = self._request("GET", f"{self.TABLE_DECISIONS}?decision_id=eq.{decision_id}&select=*")
        if not rows:
            return None
        return self._row_to_entry(rows[0])

    def get_decisions_for_cycle(self, cycle_id: str) -> list[DecisionJournalEntry]:
        """Retrieve all decisions for a cycle."""
        rows = self._request(
            "GET",
            f"{self.TABLE_DECISIONS}?cycle_id=eq.{cycle_id}&select=*&order=timestamp.asc",
        )
        return [self._row_to_entry(r) for r in rows] if rows else []

    def get_recent_decisions(
        self,
        limit: int = 100,
        symbol: str | None = None,
        action: str | None = None,
    ) -> list[DecisionJournalEntry]:
        """Retrieve recent decisions with optional filters."""
        from urllib.parse import urlencode

        params = {"select": "*", "order": "timestamp.desc", "limit": str(limit)}
        if symbol:
            params["symbol"] = f"eq.{symbol}"
        if action:
            params["action"] = f"eq.{action}"

        query = urlencode(params)
        rows = self._request("GET", f"{self.TABLE_DECISIONS}?{query}")
        return [self._row_to_entry(r) for r in rows] if rows else []

    def get_outcomes_for_decision(self, decision_id: str) -> list[DecisionOutcome]:
        """Retrieve outcomes for a decision."""
        rows = self._request(
            "GET",
            f"{self.TABLE_OUTCOMES}?decision_id=eq.{decision_id}&select=*&order=timestamp.asc",
        )
        if not rows:
            return []
        return [self._row_to_outcome(r) for r in rows]

    def get_performance_stats(
        self,
        since_hours: int = 168,  # Default 7 days
    ) -> dict[str, Any]:
        """Get aggregated performance statistics."""
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        since_str = since.isoformat()

        rows = self._request(
            "GET",
            f"{self.TABLE_DECISIONS}?timestamp=gte.{since_str}&select=*",
        )

        if not rows:
            return {
                "total_decisions": 0,
                "by_action": {},
                "by_eligibility": {},
                "avg_confidence": 0.0,
            }

        decisions = [self._row_to_entry(r) for r in rows]

        stats = {
            "total_decisions": len(decisions),
            "by_action": {},
            "by_eligibility": {},
            "avg_confidence": sum(d.confidence_score for d in decisions) / len(decisions),
        }

        for d in decisions:
            stats["by_action"][d.action.value] = stats["by_action"].get(d.action.value, 0) + 1
            stats["by_eligibility"][d.eligibility.value] = stats["by_eligibility"].get(d.eligibility.value, 0) + 1

        return stats

    def _row_to_entry(self, row: dict) -> DecisionJournalEntry:
        """Convert database row to DecisionJournalEntry."""
        return DecisionJournalEntry(
            decision_id=row["decision_id"],
            cycle_id=row["cycle_id"],
            timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
            symbol=row["symbol"],
            action=row["action"],
            eligibility=row["eligibility"],
            confidence_score=row["confidence_score"],
            entry_plan_json=row.get("entry_plan_json"),
            reasons_json=row["reasons_json"],
            warnings_json=row["warnings_json"],
            risk_state=row["risk_state"],
            aggregate_state=row.get("aggregate_state"),
            direction=row.get("direction"),
            heuristic_score=row["heuristic_score"],
            max_notional_usd=row["max_notional_usd"],
            sizing_details_json=row.get("sizing_details_json"),
        )

    def _row_to_outcome(self, row: dict) -> DecisionOutcome:
        """Convert database row to DecisionOutcome."""
        return DecisionOutcome(
            decision_id=row["decision_id"],
            order_id=row.get("order_id"),
            filled=row["filled"],
            fill_price=row.get("fill_price"),
            quantity=row.get("quantity"),
            notional=row.get("notional"),
            fees_usd=row["fees_usd"],
            slippage_usd=row["slippage_usd"],
            pnl_usd=row.get("pnl_usd"),
            timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
        )


class InMemoryDecisionJournal:
    """In-memory journal for testing without Supabase."""

    def __init__(self):
        self.decisions: dict[str, DecisionJournalEntry] = {}
        self.outcomes: dict[str, list[DecisionOutcome]] = {}

    def _decision_id_hash(self, cycle_id: str, record: DecisionRecord) -> str:
        """Generate deterministic hash for decision_id based on record content.

        Uses SHA-1 of the record's essential fields to ensure:
        - Same logical decision always produces same decision_id (idempotent)
        - Different actions/symbols/eligibility produce different IDs
        - Timestamp-independent for retry/restart scenarios
        """
        import hashlib

        # Create a deterministic snapshot of the record's identity
        # Fields that define the logical decision (not timestamp-dependent)
        hash_input = f"{cycle_id}:{record.symbol}:{record.action.value}:{record.eligibility.value}:{record.confidence_score}:{record.heuristic_score}:{record.max_notional_usd}"
        if record.entry_plan:
            hash_input += f":{record.entry_plan.side.value}:{record.entry_plan.symbol}:{record.entry_plan.entry_price}"
        if record.sizing_details_json:
            hash_input += f":{record.sizing_details_json}"

        return hashlib.sha1(hash_input.encode("utf-8")).hexdigest()[:16]

    def record_decision(self, record: DecisionRecord, cycle_id: str) -> str:
        decision_id = f"dec_{cycle_id}_{record.symbol}_{self._decision_id_hash(cycle_id, record)}"
        if decision_id in self.decisions:
            return decision_id

        entry = DecisionJournalEntry(
            decision_id=decision_id,
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc),
            symbol=record.symbol,
            action=record.action,
            eligibility=record.eligibility,
            confidence_score=record.confidence_score,
            entry_plan_json=json.dumps(record.entry_plan.to_dict()) if record.entry_plan else None,
            reasons_json=json.dumps(list(record.reasons)),
            warnings_json=json.dumps(list(record.warnings)),
            risk_state=record.risk_state,
            aggregate_state=record.aggregate_state if hasattr(record, 'aggregate_state') else None,
            direction=record.direction if hasattr(record, 'direction') else None,
            heuristic_score=record.heuristic_score,
            max_notional_usd=record.max_notional_usd if hasattr(record, 'max_notional_usd') else 0.0,
            sizing_details_json=record.sizing_details_json if hasattr(record, 'sizing_details_json') else None,
        )
        self.decisions[decision_id] = entry
        return decision_id

    def record_outcome(self, outcome: DecisionOutcome) -> None:
        if outcome.decision_id not in self.outcomes:
            self.outcomes[outcome.decision_id] = []
        # Idempotent: check if same outcome (by order_id) already exists
        existing_order_ids = {o.order_id for o in self.outcomes[outcome.decision_id]}
        if outcome.order_id not in existing_order_ids:
            self.outcomes[outcome.decision_id].append(outcome)

    def get_decision(self, decision_id: str) -> DecisionJournalEntry | None:
        return self.decisions.get(decision_id)

    def get_decisions_for_cycle(self, cycle_id: str) -> list[DecisionJournalEntry]:
        return [d for d in self.decisions.values() if d.cycle_id == cycle_id]

    def get_recent_decisions(
        self,
        limit: int = 100,
        symbol: str | None = None,
        action: str | None = None,
    ) -> list[DecisionJournalEntry]:
        decisions = list(self.decisions.values())
        decisions.sort(key=lambda d: d.timestamp, reverse=True)

        if symbol:
            decisions = [d for d in decisions if d.symbol == symbol]
        if action:
            decisions = [d for d in decisions if d.action.value == action]

        return decisions[:limit]

    def get_outcomes_for_decision(self, decision_id: str) -> list[DecisionOutcome]:
        return self.outcomes.get(decision_id, [])

    def get_performance_stats(self, since_hours: int = 168) -> dict[str, Any]:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        decisions = [d for d in self.decisions.values() if d.timestamp >= since]

        if not decisions:
            return {"total_decisions": 0, "by_action": {}, "by_eligibility": {}, "avg_confidence": 0.0}

        stats = {
            "total_decisions": len(decisions),
            "by_action": {},
            "by_eligibility": {},
            "avg_confidence": sum(d.confidence_score for d in decisions) / len(decisions),
        }

        for d in decisions:
            stats["by_action"][d.action.value] = stats["by_action"].get(d.action.value, 0) + 1
            stats["by_eligibility"][d.eligibility.value] = stats["by_eligibility"].get(d.eligibility.value, 0) + 1

        return stats