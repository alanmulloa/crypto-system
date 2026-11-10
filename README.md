# Crypto System

Evolución incremental del Crypto Tracker v4.7.1 hacia un agente de trading autónomo con límites duros de riesgo.

## Estado actual

**Phase 1 - Market Intelligence implementada.** El tracker original se conserva en `tracker/`. El nuevo agente puede consultar exclusivamente datos públicos de Binance Spot, filtrar universo líquido, descargar velas 15m/1h/4h/1d, calcular indicadores simples y clasificar régimen de mercado. No genera señales de compra/venta y no puede operar.

Seguridad por defecto:

- `TRADING_MODE=PAPER`
- `BINANCE_TESTNET=true`
- `KILL_SWITCH=true`
- no Futures, Margin ni apalancamiento
- no withdrawals
- ninguna API key necesaria para Phase 1
- la fuente de mercado pública (`BINANCE_MARKET_BASE_URL`) está separada del entorno de ejecución futuro

## Arquitectura

- GitHub: código, ramas, PRs y CI.
- Tracker actual: dashboard, cartera, reconstrucción histórica, operaciones manuales y conciliación on-chain.
- Trading Agent (Python/FastAPI): Market Intelligence y futuras fases.
- Supabase: almacenamiento compartido progresivo. En Phase 1 es opcional.
- Binance Spot public REST: `exchangeInfo`, `ticker/24hr`, `klines`.

Documentación oficial usada para los contratos de Binance:

- https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/general
- https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market

## Arranque local en macOS

```bash
cd agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest -q
ruff check app tests
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Ejecutar Market Scanner

No necesita API key:

```bash
cd agent
source .venv/bin/activate
python -m app.market.cli --limit 10 --prefilter 30
```

El scanner no devuelve BUY/SELL. Devuelve candidatos para investigación posterior con score técnico de interés, régimen por timeframe, EMA, RSI, ATR, volumen y estructura.

Ejemplo de forma de salida:

```json
{
  "symbol": "BTCUSDT",
  "ranking_score": 54.0,
  "analyses": [
    {"interval": "15m", "regime": "ranging"},
    {"interval": "1h", "regime": "bullish"},
    {"interval": "4h", "regime": "bullish"},
    {"interval": "1d", "regime": "ranging"}
  ]
}
```

Los valores anteriores son ilustrativos de formato, no una señal ni un resultado live guardado.

## Persistencia Supabase

`supabase/migrations/001_initial.sql` conserva el esquema base. `002_market_intelligence.sql` agrega observaciones append-only de candidatos. El scanner funciona sin Supabase mediante `NullMarketRepository`; no requiere credenciales para tests ni ejecución local.

## Tests

La suite CI ejecuta:

```bash
ruff check app tests
pytest -q
```

Los módulos puros de Market Intelligence también son compatibles con `unittest`, lo que permite validar lógica sin dependencias de red.

## Próximo paso

Phase 2 agregará estrategias normalizadas (trend, pullback, breakout, mean reversion, momentum) sobre estos datos. Ninguna estrategia ejecutará órdenes directamente.
