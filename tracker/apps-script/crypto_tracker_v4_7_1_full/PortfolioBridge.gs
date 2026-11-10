/**
 * Crypto Tracker -> Trading Agent portfolio bridge.
 *
 * One-way by design: the tracker exports a read-only snapshot to the agent.
 * The agent has no code path here to update Cartera/Asignacion/Conciliacion.
 *
 * Script Properties required to push:
 *   CRYPTO_AGENT_SYNC_URL
 *   CRYPTO_AGENT_SYNC_TOKEN
 */

const CT_PORTFOLIO_SYNC_SCHEMA = '1.0';

function portfolioRowsAsObjectsV48_(sheetName) {
  const sh = SpreadsheetApp.getActive().getSheetByName(sheetName);
  if (!sh || sh.getLastRow() < 2 || sh.getLastColumn() < 1) return [];

  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getDisplayValues()[0]
    .map(h => String(h || '').trim());
  const rows = sh.getRange(2, 1, sh.getLastRow() - 1, sh.getLastColumn()).getValues();

  return rows.map(row => {
    const out = {};
    headers.forEach((header, idx) => {
      if (!header) return;
      const value = row[idx];
      out[header] = value instanceof Date ? value.toISOString() : value;
    });
    return out;
  }).filter(row => String(row['Activo'] || '').trim() !== '');
}

function dailyBuyUsedUsdV48_() {
  const sh = SpreadsheetApp.getActive().getSheetByName('Operaciones ejecutadas');
  if (!sh || sh.getLastRow() < 2) return 0;

  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getDisplayValues()[0];
  const rows = sh.getRange(2, 1, sh.getLastRow() - 1, sh.getLastColumn()).getValues();
  const idx = name => headers.indexOf(name);
  const dateIdx = idx('Fecha ejecución');
  const typeIdx = idx('Tipo');
  const usdIdx = idx('Ejecutado USD');
  if (dateIdx < 0 || typeIdx < 0 || usdIdx < 0) return 0;

  const tz = Session.getScriptTimeZone();
  const today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');

  return rows.reduce((sum, row) => {
    const date = row[dateIdx];
    if (!(date instanceof Date)) return sum;
    const day = Utilities.formatDate(date, tz, 'yyyy-MM-dd');
    const type = String(row[typeIdx] || '').trim().toUpperCase();
    const usd = Number(row[usdIdx]) || 0;
    return day === today && type === 'COMPRA' ? sum + Math.max(usd, 0) : sum;
  }, 0);
}

function buildPortfolioSyncPayloadV48_() {
  return {
    schema_version: CT_PORTFOLIO_SYNC_SCHEMA,
    source_id: 'crypto_tracker',
    source_revision: typeof CRYPTO_TRACKER_BACKEND_VERSION !== 'undefined'
      ? CRYPTO_TRACKER_BACKEND_VERSION
      : 'unknown',
    generated_at: new Date().toISOString(),
    cartera_rows: portfolioRowsAsObjectsV48_('Cartera'),
    allocation_rows: portfolioRowsAsObjectsV48_('Asignación'),
    reconciliation_rows: portfolioRowsAsObjectsV48_('Conciliación histórica'),
    daily_buy_used_usd: dailyBuyUsedUsdV48_(),

    // Deliberately unknown. The current v4.7 operation journal does not preserve
    // enough realized-cost-basis detail to calculate daily realized PnL safely.
    daily_realized_pnl_usd: null
  };
}

function previewPortfolioSyncV48() {
  const payload = buildPortfolioSyncPayloadV48_();
  console.log(JSON.stringify(payload, null, 2));
  return payload;
}

function pushPortfolioSnapshotV48() {
  const props = PropertiesService.getScriptProperties();
  const url = String(props.getProperty('CRYPTO_AGENT_SYNC_URL') || '').trim();
  const token = String(props.getProperty('CRYPTO_AGENT_SYNC_TOKEN') || '').trim();

  if (!url) throw new Error('Falta Script Property CRYPTO_AGENT_SYNC_URL.');
  if (!token) throw new Error('Falta Script Property CRYPTO_AGENT_SYNC_TOKEN.');

  const payload = buildPortfolioSyncPayloadV48_();
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token
    }
  });

  const code = response.getResponseCode();
  const body = response.getContentText();
  if (code < 200 || code >= 300) {
    throw new Error('Portfolio sync HTTP ' + code + ': ' + body.slice(0, 500));
  }

  const result = JSON.parse(body || '{}');
  SpreadsheetApp.getActive().toast(
    'Portfolio sync: ' + String(result.state || 'OK'),
    'Crypto Tracker',
    5
  );
  return result;
}
