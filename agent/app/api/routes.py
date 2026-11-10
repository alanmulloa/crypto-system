from fastapi import APIRouter

from app.api.portfolio_routes import router as portfolio_router
from app.config import get_settings


router = APIRouter()
router.include_router(portfolio_router)


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "mode": settings.trading_mode,
        "testnet": settings.binance_testnet,
        "kill_switch": settings.kill_switch,
        "real_trading_enabled": False,
        "portfolio_sync_enabled": bool(settings.portfolio_sync_token),
    }
