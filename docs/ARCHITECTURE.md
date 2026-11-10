# Architecture

## Principle

El Crypto Tracker v4.7.1 existente se conserva. El Trading Agent no reemplaza la cartera ni la historia: las consume y las enriquecerá progresivamente. Phase 1 añade Market Intelligence sin crear un segundo portfolio ni habilitar ejecución.

## Components

### Tracker

Responsable de dashboard, visibilidad de cartera, reconstrucción histórica, operaciones manuales y conciliación on-chain. Se mantiene sin cambios funcionales en Phase 1.

### Trading Agent

`agent/app/market/` contiene la primera capacidad real del agente:

- `binance_public.py`: cliente REST solo para endpoints públicos.
- `types.py`: contratos internos inmutables de mercado.
- `indicators.py`: EMA, RSI, ATR, ratio de volumen y estructura de máximos/mínimos.
- `regime.py`: clasificación determinista de régimen.
- `scanner.py`: filtros, análisis multi-timeframe y ranking de candidatos.
- `service.py`: orquestación y persistencia opcional.
- `cli.py`: ejecución manual del scanner.

No existe aún strategy engine ni execution engine funcional.

### Public market vs execution environment

Market data y ejecución son conceptos separados.

- Public market source: `https://api.binance.com`, sin API key.
- Future execution: Testnet primero y únicamente con credenciales separadas.

Esto evita que `BINANCE_TESTNET=true` fuerce al scanner a analizar un mercado de prueba poco representativo, y evita que leer mercado implique capacidad de operar.

### Supabase

Supabase será fuente compartida progresiva, no requisito para ejecutar Phase 1. `NullMarketRepository` permite scans/tests sin credenciales. `SupabaseMarketRepository` es opt-in y backend-only.

La service-role key nunca debe aparecer en GitHub Pages, Apps Script público, logs ni respuestas API al navegador.

## Scanner flow

```text
exchangeInfo
    ↓
SPOT + TRADING + USDT
    ↓
exclude stable / leveraged / wrapped duplicates
    ↓
24h liquidity + trade-count filter
    ↓
Top liquid prefilter
    ↓
15m + 1h + 4h + 1d candles
    ↓
EMA / RSI / ATR / volume / structure
    ↓
regime detection per timeframe
    ↓
ranking of research candidates
```

The ranking is not a trade signal. It exists only to reduce the universe for Phase 2.

## Indicators

Indicators are intentionally limited. Phase 1 avoids indicator soup and external TA libraries. Implementations are deterministic pure Python to keep behavior auditable and testable.

### EMA

20 and 50 periods by default.

### RSI

Wilder-style 14-period smoothed RSI.

### ATR

Wilder-style 14-period ATR. ATR percentage is used to detect extreme volatility.

### Volume ratio

Latest candle volume divided by the prior 20-candle average.

### Market structure

Compares recent and previous halves of a 20-candle window to classify higher-high/higher-low, lower-high/lower-low, or mixed structure.

## Market regime

Phase 1 regimes:

- `bullish`
- `bearish`
- `ranging`
- `high_volatility`

High volatility has priority. Trend regimes require EMA alignment, RSI confirmation and market-structure confirmation. Otherwise the state is ranging.

These thresholds are heuristics, not learned parameters. Phase 5 will evaluate them historically before any production use.

## Safety boundary

Hard risk limits remain configuration outside strategy output. No Phase 1 module imports or calls execution code. No private Binance endpoint is used. No API key is required.

## Rate limits / operational note

A full scan can request four kline series for each prefiltered asset. The initial default prefilter is 30 symbols. Continuous scheduling must respect Binance request weights and should add caching/concurrency controls before increasing universe size or cadence.
