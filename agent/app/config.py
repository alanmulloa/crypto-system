from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    trading_mode: Literal["PAPER", "TESTNET", "MANUAL", "AUTO_LIMITED"] = "PAPER"

    # Shared storage. Service-role keys are backend-only and must never reach the browser.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Reserved for later execution phases. Current paper trading never uses them.
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True

    # Public market data is deliberately independent from the execution environment.
    binance_market_base_url: str = "https://api.binance.com"
    market_quote_asset: str = "USDT"
    market_min_quote_volume_24h: float = 5_000_000.0
    market_min_trade_count_24h: int = 1_000
    market_prefilter_limit: int = 30
    market_candidate_limit: int = 10
    market_kline_limit: int = 250
    market_min_candles: int = 120

    # One-way tracker -> agent portfolio synchronization.
    portfolio_sync_token: str = ""
    portfolio_sync_max_age_minutes: int = 30
    portfolio_cash_asset: str = "USDC"

    # Paper Broker assumptions. These are simulation parameters only.
    paper_fee_bps: float = 10.0
    paper_slippage_bps: float = 5.0

    # Hard risk controls. Strategy code must not mutate these values.
    max_position_usd: float = 250.0
    max_daily_buy_usd: float = 1000.0
    min_cash_reserve_pct: float = 25.0
    max_open_positions: int = 5
    daily_loss_limit_usd: float = 100.0
    kill_switch: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
