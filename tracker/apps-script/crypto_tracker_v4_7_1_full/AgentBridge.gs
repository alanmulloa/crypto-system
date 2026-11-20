/**
 * Phase 8 Web + Agent integration.
 *
 * Script Properties:
 *   CRYPTO_AGENT_BASE_URL
 *   CRYPTO_AGENT_SYNC_TOKEN
 *
 * Read-only: this bridge never creates orders.
 */
function fetchAgentDashboardV50_() {
  const props = PropertiesService.getScriptProperties();
  const base = String(props.getProperty('CRYPTO_AGENT_BASE_URL') || '').trim().replace(/\/$/, '');
  const token = String(props.getProperty('CRYPTO_AGENT_SYNC_TOKEN') || '').trim();

  if (!base || !token) {
    return {
      available: false,
      state: 'NOT_CONFIGURED',
      message: 'Agent API no configurada todavía.'
    };
  }

  const cache = CacheService.getScriptCache();
  const cached = cache.get('agent-dashboard-v50');
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      parsed.cached = true;
      return parsed;
    } catch (e) {
      console.log('Agent cache parse: ' + e.message);
    }
  }

  try {
    const response = UrlFetchApp.fetch(base + '/portfolio/dashboard', {
      method: 'get',
      muteHttpExceptions: true,
      headers: { Authorization: 'Bearer ' + token }
    });
    const code = response.getResponseCode();
    const body = response.getContentText();
    if (code < 200 || code >= 300) {
      return {
        available: false,
        state: 'HTTP_' + code,
        message: body.slice(0, 300)
      };
    }
    const dashboard = JSON.parse(body || '{}');

    let history = null;
    try {
      const historyResponse = UrlFetchApp.fetch(base + '/portfolio/history?limit=90', {
        method: 'get',
        muteHttpExceptions: true,
        headers: { Authorization: 'Bearer ' + token }
      });
      if (historyResponse.getResponseCode() >= 200 && historyResponse.getResponseCode() < 300) {
        history = JSON.parse(historyResponse.getContentText() || '{}');
      }
    } catch (historyError) {
      console.log('Agent history fetch: ' + historyError.message);
    }

    const result = {
      available: true,
      state: (dashboard.safety || {}).operational_state || 'UNKNOWN',
      fetchedAt: new Date().toISOString(),
      dashboard,
      history,
      cached: false
    };
    cache.put('agent-dashboard-v50', JSON.stringify(result), 60);
    return result;
  } catch (e) {
    return {
      available: false,
      state: 'OFFLINE',
      message: String(e && e.message ? e.message : e)
    };
  }
}

function previewAgentDashboardV50() {
  const result = fetchAgentDashboardV50_();
  console.log(JSON.stringify(result, null, 2));
  return result;
}


function invalidateAgentDashboardCacheV52_() {
  CacheService.getScriptCache().remove('agent-dashboard-v50');
}

function syncAgentAndFetchV52() {
  const sync = pushPortfolioSnapshotV48();
  invalidateAgentDashboardCacheV52_();
  return {
    sync,
    data: getFrontData()
  };
}
