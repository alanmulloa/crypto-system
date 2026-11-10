from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "mode": settings.trading_mode,
        "testnet": settings.binance_testnet,
        "kill_switch": settings.kill_switch,
        "real_trading_enabled": False,
    }
