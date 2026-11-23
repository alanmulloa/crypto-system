/**
 * Phase 8 Web + Agent integration.
 *
 * Script Properties:
 *   CRYPTO_AGENT_BASE_URL
 *   CRYPTO_AGENT_SYNC_TOKEN
 *   CRYPTO_BOT_API_TOKEN
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

/**
 * Fetches bot activity trace from the new /bot/activity endpoint.
 * Returns complete trace: Opportunity → Decision → Order → Fill → Trade
 */
function fetchBotActivity_(params) {
  const props = PropertiesService.getScriptProperties();
  const base = String(props.getProperty('CRYPTO_AGENT_BASE_URL') || '').trim().replace(/\/$/, '');
  const token = String(props.getProperty('CRYPTO_BOT_API_TOKEN') || '').trim();

  if (!base || !token) {
    return {
      available: false,
      state: 'NOT_CONFIGURED',
      message: 'Bot API no configurada (CRYPTO_AGENT_BASE_URL / CRYPTO_BOT_API_TOKEN).'
    };
  }

  const query = [];
  if (params?.symbol) query.push('symbol=' + encodeURIComponent(params.symbol));
  if (params?.limit) query.push('limit=' + encodeURIComponent(params.limit));
  if (params?.since_hours) query.push('since_hours=' + encodeURIComponent(params.since_hours));
  const queryString = query.length ? '?' + query.join('&') : '';

  try {
    const response = UrlFetchApp.fetch(base + '/bot/activity' + queryString, {
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
    const data = JSON.parse(body || '{}');
    return {
      available: true,
      fetchedAt: new Date().toISOString(),
      data,
      cached: false
    };
  } catch (e) {
    return {
      available: false,
      state: 'OFFLINE',
      message: String(e && e.message ? e.message : e)
    };
  }
}

/**
 * Fetches paper portfolio from the /bot/paper-portfolio endpoint.
 * Returns paper positions with unrealized/realized PnL.
 */
function fetchPaperPortfolio_() {
  const props = PropertiesService.getScriptProperties();
  const base = String(props.getProperty('CRYPTO_AGENT_BASE_URL') || '').trim().replace(/\/$/, '');
  const token = String(props.getProperty('CRYPTO_BOT_API_TOKEN') || '').trim();

  if (!base || !token) {
    return {
      available: false,
      state: 'NOT_CONFIGURED',
      message: 'Bot API no configurada.'
    };
  }

  try {
    const response = UrlFetchApp.fetch(base + '/bot/paper-portfolio', {
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
    const data = JSON.parse(body || '{}');
    return {
      available: true,
      fetchedAt: new Date().toISOString(),
      data,
      cached: false
    };
  } catch (e) {
    return {
      available: false,
      state: 'OFFLINE',
      message: String(e && e.message ? e.message : e)
    };
  }
}

/**
 * Fetches bot performance metrics from the /bot/performance endpoint.
 * Returns aggregated metrics over the specified period.
 */
function fetchBotPerformance_(params) {
  const props = PropertiesService.getScriptProperties();
  const base = String(props.getProperty('CRYPTO_AGENT_BASE_URL') || '').trim().replace(/\/$/, '');
  const token = String(props.getProperty('CRYPTO_BOT_API_TOKEN') || '').trim();

  if (!base || !token) {
    return {
      available: false,
      state: 'NOT_CONFIGURED',
      message: 'Bot API no configurada.'
    };
  }

  const query = [];
  if (params?.days) query.push('days=' + encodeURIComponent(params.days));
  const queryString = query.length ? '?' + query.join('&') : '';

  try {
    const response = UrlFetchApp.fetch(base + '/bot/performance' + queryString, {
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
    const data = JSON.parse(body || '{}');
    return {
      available: true,
      fetchedAt: new Date().toISOString(),
      data,
      cached: false
    };
  } catch (e) {
    return {
      available: false,
      state: 'OFFLINE',
      message: String(e && e.message ? e.message : e)
    };
  }
}

function previewBotActivity() {
  const result = fetchBotActivity_({ limit: 10, since_hours: 24 });
  console.log(JSON.stringify(result, null, 2));
  return result;
}

function previewPaperPortfolio() {
  const result = fetchPaperPortfolio_();
  console.log(JSON.stringify(result, null, 2));
  return result;
}

function previewBotPerformance() {
  const result = fetchBotPerformance_({ days: 30 });
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