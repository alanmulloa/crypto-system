from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, status

from app.config import get_settings
from app.portfolio.sync import PortfolioSyncService, TrackerPortfolioExport
from app.storage.portfolio_repository import SupabasePortfolioSyncRepository


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


@router.post("/sync")
def sync_portfolio(
    payload: TrackerPortfolioExport,
    authorization: str | None = Header(default=None),
):
    settings = get_settings()
    if not settings.portfolio_sync_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="portfolio sync is disabled",
        )

    token = _bearer_token(authorization)
    if not token or not hmac.compare_digest(token, settings.portfolio_sync_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid sync token",
        )

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="portfolio sync storage is not configured",
        )

    repository = SupabasePortfolioSyncRepository(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
    service = PortfolioSyncService(
        repository,
        cash_asset=settings.portfolio_cash_asset,
        max_age_minutes=settings.portfolio_sync_max_age_minutes,
    )
    result = service.sync(payload)
    return {
        "state": result.state,
        "content_hash": result.content_hash,
        "generated_at": result.generated_at,
        "total_value_usd": result.total_value_usd,
        "cash_value_usd": result.cash_value_usd,
        "capital_at_risk_usd": result.capital_at_risk_usd,
        "reason": result.reason,
    }
