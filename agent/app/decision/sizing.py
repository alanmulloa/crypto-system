"""Deterministic position sizing for paper trading.

Phase 2: Calculates position sizes with explicit constraints including
position, exposure, liquidity, cash reserve, and daily loss limits.
"""
from __future__ import annotations

from app.decision.models import SizingConstraints, EntryPlan, DecisionAction
from app.strategies.base import HypothesisDirection


def calculate_position_size(
    constraints: SizingConstraints,
    direction: HypothesisDirection,
    current_position_usd: float,
    market_price: float,
    requested_notional_usd: float = 0.0,
    atr: float | None = None,  # Average True Range for volatility
) -> tuple[float, str, tuple[str, ...]]:
    """Calculate deterministic position size based on constraints.

    Returns:
        Tuple of (size_usd, primary_reason, warnings)
    """
    warnings: list[str] = []

    # max_position_usd is a hard limit - do not reduce by volatility
    base_size = constraints.max_position_usd

    # Apply volatility adjustment to requested size (if provided) or base size
    if requested_notional_usd > 0:
        volatility_adjusted_requested = requested_notional_usd * constraints.volatility_adjustment
        if volatility_adjusted_requested < 10.0:
            warnings.append("volatility adjustment reduces requested size below minimum")
            volatility_adjusted_requested = 10.0
        base_size = min(base_size, volatility_adjusted_requested)

    # Cap by exposure limit (portfolio-level)
    exposure_cap = min(base_size, constraints.max_exposure_usd)

    # Cap by liquidity (cash available after reserve)
    liquidity_cap = min(exposure_cap, constraints.max_cash_drawdown_usd)

    # Cap by daily loss guard (remaining daily loss budget)
    loss_cap = min(liquidity_cap, constraints.max_daily_loss_usd)

    # Final size is the minimum of all caps
    max_allowed = loss_cap

    if direction is HypothesisDirection.BUY:
        # BUY: Use requested notional capped by all constraints
        if requested_notional_usd > 0:
            size = min(requested_notional_usd, max_allowed)
        else:
            size = max_allowed

        if size < 10.0:
            warnings.append(f"calculated BUY size ${size:.2f} below minimum $10")
            size = 0.0

        reason = "deterministic BUY sizing with risk constraints"
        return (size, reason, tuple(warnings))

    elif direction is HypothesisDirection.SELL:
        # SELL/REDUCE: Limited by current position size
        max_sell = current_position_usd

        if requested_notional_usd > 0:
            size = min(requested_notional_usd, max_sell, max_allowed)
        else:
            size = min(max_sell, max_allowed)

        if size < 10.0:
            warnings.append(f"calculated SELL size ${size:.2f} below minimum $10")
            size = 0.0

        action = "REDUCE" if size < current_position_usd * 0.9 else "SELL"
        reason = f"deterministic {action} sizing limited by position and risk"
        return (size, reason, tuple(warnings))

    return (0.0, "no actionable direction", tuple(warnings))


def build_entry_plan(
    symbol: str,
    action: DecisionAction,
    market_price: float,
    size_usd: float,
    atr: float | None = None,
    current_entry_price: float | None = None,  # Average cost basis for REDUCE
) -> EntryPlan:
    """Build entry/exit plan with stop loss and take profit levels.

    Uses ATR-based stops when available, otherwise percentage-based.
    """
    warnings: list[str] = []

    if size_usd <= 0:
        return EntryPlan(
            side=action,
            symbol=symbol,
            entry_price=None,
            stop_price=None,
            target_prices=(),
            position_size_usd=0.0,
            estimated_impact_usd=0.0,
            reason="zero position size",
            warnings=("position size is zero or negative",),
        )

    # Default risk parameters
    risk_pct = 0.02  # 2% risk per trade
    reward_ratio = 2.0  # 2:1 reward:risk

    # Use ATR for stop/target if available
    if atr and atr > 0:
        stop_distance = atr * 1.5  # 1.5x ATR for stop
        target_distance = stop_distance * reward_ratio
    else:
        # Percentage-based fallback
        stop_distance = market_price * risk_pct
        target_distance = market_price * risk_pct * reward_ratio

    if action == DecisionAction.BUY:
        entry_price = market_price
        stop_price = max(entry_price - stop_distance, entry_price * 0.90)  # Max 10% stop
        target1 = entry_price + target_distance
        target2 = entry_price + target_distance * 1.5
        reason = "ATR-based entry plan" if atr else "percentage-based entry plan"

    elif action in (DecisionAction.SELL, DecisionAction.REDUCE):
        entry_price = market_price
        # For sell/reduce, stop is above entry (trailing stop for short or protect gains)
        stop_price = min(entry_price + stop_distance, entry_price * 1.10)  # Max 10% stop
        target1 = max(entry_price - target_distance, entry_price * 0.80)
        target2 = max(entry_price - target_distance * 1.5, entry_price * 0.70)
        reason = f"ATR-based {action.value} plan" if atr else f"percentage-based {action.value} plan"

        if current_entry_price and current_entry_price > 0:
            # Add breakeven reference
            warnings.append(f"average cost basis: ${current_entry_price:.4f}")
    else:
        entry_price = market_price
        stop_price = None
        target1 = None
        target2 = None
        reason = "no action"

    # Estimate slippage impact (default 5 bps)
    estimated_impact = size_usd * 0.0005

    if stop_price is None or target1 is None:
        warnings.append("stop/target levels unavailable - manual management required")
        targets = ()
    else:
        targets = (target1, target2) if target2 else (target1,)

    return EntryPlan(
        side=action,
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=targets,
        position_size_usd=size_usd,
        estimated_impact_usd=estimated_impact,
        reason=reason,
        warnings=tuple(warnings),
    )


def calculate_sizing_details(
    constraints: SizingConstraints,
    direction: HypothesisDirection,
    current_position_usd: float,
    requested_notional_usd: float,
    final_size_usd: float,
) -> dict:
    """Generate detailed sizing breakdown for audit trail."""
    return {
        "constraints": {
            "max_position_usd": constraints.max_position_usd,
            "max_exposure_usd": constraints.max_exposure_usd,
            "min_liquidity_usd": constraints.min_liquidity_usd,
            "max_cash_drawdown_usd": constraints.max_cash_drawdown_usd,
            "max_daily_loss_usd": constraints.max_daily_loss_usd,
            "volatility_adjustment": constraints.volatility_adjustment,
        },
        "direction": direction.value,
        "current_position_usd": current_position_usd,
        "requested_notional_usd": requested_notional_usd,
        "base_size_usd": constraints.max_position_usd * constraints.volatility_adjustment,
        "exposure_cap_usd": min(constraints.max_position_usd * constraints.volatility_adjustment, constraints.max_exposure_usd),
        "liquidity_cap_usd": min(
            constraints.max_position_usd * constraints.volatility_adjustment,
            constraints.max_exposure_usd,
            constraints.max_cash_drawdown_usd,
        ),
        "final_size_usd": final_size_usd,
        "utilization_pct": (final_size_usd / constraints.max_position_usd * 100) if constraints.max_position_usd > 0 else 0,
    }