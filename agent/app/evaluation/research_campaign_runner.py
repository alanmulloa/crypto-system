from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.evaluation.candidate_discovery import discover_from_phase5f1_payload
from app.evaluation.entry_quality import MeanReversionEntryDiagnostics
from app.evaluation.evidence import RealEvidenceRunner
from app.evaluation.research_campaign import ResearchCampaign, campaign_state


def run_campaign_screen(
    *,
    campaign: ResearchCampaign,
    as_of_ms: int,
    evidence: RealEvidenceRunner | None = None,
) -> dict[str, Any]:
    state = campaign_state(campaign, as_of_ms=as_of_ms)
    if state != "SCREENING_READY":
        raise ValueError(f"campaign is not ready for screening: {state}")

    engine = evidence or RealEvidenceRunner()
    analyzer = MeanReversionEntryDiagnostics(
        outcome_hours=campaign.outcome_hours,
        min_bucket_observations=campaign.min_bucket_observations,
    )
    reports = []
    for symbol in campaign.symbols:
        history = engine.fetch_symbol_history(
            symbol=symbol,
            start_time_ms=campaign.start_ms,
            end_time_ms=campaign.end_ms,
        )
        quote_asset = "USDT" if symbol.endswith("USDT") else ""
        base_asset = symbol[: -len(quote_asset)] if quote_asset else symbol
        points = engine.historical_runner.run(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            candles_by_interval=history,
            anchor_interval="1h",
            max_points=campaign.max_points,
        )
        reports.append(
            analyzer.run_symbol(
                strategy=campaign.strategy,
                points=points,
                candles_by_interval=history,
            )
        )

    payload = {
        "metadata": {
            "phase": "5F.1",
            "campaign_id": campaign.id,
            "campaign_fingerprint_sha256": campaign.fingerprint(),
            "created_at_ms": as_of_ms,
            "fixed_start_ms": campaign.start_ms,
            "fixed_end_ms": campaign.end_ms,
            "outcome_hours": campaign.outcome_hours,
            "min_bucket_observations": campaign.min_bucket_observations,
            "research_only": True,
            "oos_already_observed": True,
            "candidate_selection_uses_oos": False,
        },
        "results": [asdict(report) for report in reports],
        "pooled": asdict(
            analyzer.pool(reports, strategy=campaign.strategy)
        ),
    }
    proposals = discover_from_phase5f1_payload(payload)
    return {
        "phase": "5K.3",
        "campaign": campaign.to_dict(),
        "campaign_fingerprint_sha256": campaign.fingerprint(),
        "source_phase5f1": payload,
        "proposals": [asdict(item) for item in proposals],
        "selection_uses_calibration_validation_only": True,
        "oos_used_for_selection": False,
        "research_only": True,
        "auto_register": False,
        "auto_freeze": False,
        "phase6_blocked": True,
    }
