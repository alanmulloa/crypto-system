from __future__ import annotations

from app.market.binance_public import BinancePublicClient
from app.market.scanner import MarketScanner, ScannerConfig
from app.market.types import MarketCandidate
from app.storage.market_repository import MarketRepository, NullMarketRepository


class MarketIntelligenceService:
    def __init__(
        self,
        client: BinancePublicClient | None = None,
        repository: MarketRepository | None = None,
        scanner_config: ScannerConfig | None = None,
    ):
        self.scanner = MarketScanner(client or BinancePublicClient(), scanner_config)
        self.repository = repository or NullMarketRepository()

    def run_scan(self) -> list[MarketCandidate]:
        candidates = self.scanner.scan()
        self.repository.save_candidates(candidates)
        return candidates
