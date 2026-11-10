from app.config import Settings
from app.models import RiskDecision, StrategySignal


def evaluate_risk(signal: StrategySignal, settings: Settings, cash_usd: float, open_positions: int) -> RiskDecision:
    reasons: list[str] = []

    if settings.kill_switch:
        reasons.append("Kill switch activo")
    if open_positions >= settings.max_open_positions:
        reasons.append("Máximo de posiciones abiertas alcanzado")
    if cash_usd <= 0:
        reasons.append("Sin liquidez disponible")

    approved = not reasons
    max_notional = min(settings.max_position_usd, max(cash_usd * (1 - settings.min_cash_reserve_pct / 100), 0))

    if max_notional <= 0:
        approved = False
        reasons.append("La reserva mínima de liquidez impide abrir una nueva posición")

    return RiskDecision(approved=approved, max_notional_usd=max_notional if approved else 0, reasons=reasons)
