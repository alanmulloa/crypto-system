Crypto Tracker v4.7 / Backend v2.9.0

1. Reemplazar Code.gs, WebApp.gs e Index.html.
2. Ejecutar repairV47 una sola vez.
3. Ejecutar updateCryptoMarket.
4. Desplegar nueva versión.

Incluye registro de operaciones reales, recomendado vs ejecutado, monto editable, operaciones manuales y conciliación pendiente por referencia.

V4.7.1: semaforos visuales y estado global de cartera. Backend sin cambios de logica.


Phase 8 / Front v5.0.0:
- añadir AgentBridge.gs al proyecto Apps Script
- configurar Script Property CRYPTO_AGENT_BASE_URL
- reutilizar CRYPTO_AGENT_SYNC_TOKEN
- el panel Agent es read-only
- si Agent no está disponible, la web sigue funcionando con los datos Tracker
- las recomendaciones Tracker y Agent permanecen separadas hasta validación prospectiva


Phase 8I–8P / Front v5.1.0:
- Portfolio sync schema 1.1
- Wallets, On-chain balances y Conciliacion on-chain se envian al Agent
- direcciones publicas se muestran enmascaradas desde Agent
- panel Wallets & On-chain prioriza Agent y conserva fallback Tracker
- no se envian claves privadas ni seeds
- no hay escritura automatica de saldos ni conciliacion
