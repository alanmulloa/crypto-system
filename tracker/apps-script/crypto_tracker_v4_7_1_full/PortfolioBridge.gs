/**
 * Crypto Tracker -> Trading Agent portfolio bridge.
 *
 * One-way by design: the tracker exports a read-only snapshot to the agent.
 * The agent has no code path here to update Cartera/Asignacion/Conciliacion.
 *
 * Script Properties required to push:
 *   CRYPTO_AGENT_SYNC_URL   e.g. https://agent.example.com/portfolio/sync
 *   CRYPTO_AGENT_SYNC_TOKEN strong random bearer token
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

function buildPortfolioSyncPayloadV48_() {
  const ss = SpreadsheetApp.getActive();
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
    daily_buy_used_usd: 0,
    daily_realized_pnl_usd: 0
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
