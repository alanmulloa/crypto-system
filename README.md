# Crypto System

Evolución incremental del Crypto Tracker v4.7.1 hacia un agente de trading autónomo con límites duros de riesgo.

## Estado actual

El proyecto ya completó las capas de Market Intelligence, estrategias, riesgo,
paper trading y el framework de evaluación de Phase 5. La línea activa es
investigación prospectiva: Phase 5G mantiene congelada una candidata XRP y
recolecta evidencia no vista automáticamente; Phase 5H agrega infraestructura
auditable para registrar futuros experimentos sin mezclarlos con 5G.

| Fase | Estado |
| --- | --- |
| Phase 1–4 | COMPLETE |
| Phase 5 Research | COMPLETE / ACTIVE RESEARCH FRAMEWORK |
| Phase 5G.1 — automated collection | COMPLETE |
| Phase 5G.2 — monitoring/review | COMPLETE |
| Phase 5G.3 — decision protocol | COMPLETE |
| Phase 5G.4 — prospective evidence | COLLECTING PROSPECTIVE EVIDENCE |
| Phase 5H — research registry | ACTIVE INFRASTRUCTURE |
| Phase 6 | BLOCKED |

`sample_ready=true` no es aprobación. Tampoco `PASS_RESEARCH` autoriza
Testnet, órdenes o ejecución: Phase 6 exige una decisión humana separada.

Seguridad por defecto:

- `TRADING_MODE=PAPER`
- `BINANCE_TESTNET=true`
- `KILL_SWITCH=true`
- no Futures, Margin ni apalancamiento
- no withdrawals
- la investigación actual no requiere API keys privadas de Binance
- la fuente de mercado pública (`BINANCE_MARKET_BASE_URL`) está separada del entorno de ejecución futuro

## Arquitectura

- GitHub: código, ramas, PRs y CI.
- Tracker actual: dashboard, cartera, reconstrucción histórica, operaciones manuales y conciliación on-chain.
- Trading Agent (Python/FastAPI): market intelligence, estrategias, riesgo, paper trading y evaluación research-only.
- Supabase: almacenamiento compartido opcional; Phase 5G/5H no dependen de Supabase.
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

Phase 5G.4 continúa acumulando evidencia prospectiva con la definición congelada
de XRP. Phase 5H permite registrar futuras candidatas de investigación de forma
aislada y auditable. Phase 6 permanece bloqueada hasta una revisión humana
separada; no existe promoción automática desde resultados de investigación.
