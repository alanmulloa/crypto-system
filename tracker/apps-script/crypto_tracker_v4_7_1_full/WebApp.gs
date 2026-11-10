function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Crypto Tracker')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getFrontData() {
  const ss = SpreadsheetApp.getActive();
  const cartera = readSheetObjectsFront_(ss, 'Cartera');
  const decisiones = readSheetObjectsFront_(ss, 'Decisiones');
  const mercado = readSheetObjectsFront_(ss, 'Mercado');
  const alertas = readSheetObjectsFront_(ss, 'Alertas');
  const asignacion = readSheetObjectsFront_(ss, 'Asignación');
  const rendimiento = readSheetObjectsFront_(ss, 'Rendimiento motor');
  const radarRows = readSheetObjectsFront_(ss, 'Radar');
  const walletsRows = readSheetObjectsFront_(ss, 'Wallets');
  const onchainRows = readSheetObjectsFront_(ss, 'On-chain balances');
  const reconciliationRows = readSheetObjectsFront_(ss, 'Conciliacion on-chain');
  const calibrationRows = readSheetObjectsFront_(ss, 'Calibracion pronosticos');
  const historicalReconRows = readSheetObjectsFront_(ss, 'Conciliacion historica');
  const operations = (typeof getRecentOperationsV47_ === 'function') ? getRecentOperationsV47_(20) : [];

  const marketByAsset = indexByAssetFront_(mercado);
  const allocByAsset = indexByAssetFront_(asignacion);
  const decisionByAsset = indexByAssetFront_(decisiones);

  const assets = cartera.map(row => {
    const asset = String(getFirstFront_(row, ['Activo','Asset','Símbolo','Simbolo']) || '').trim();
    if (!asset) return null;
    const m = marketByAsset[asset] || {};
    const d = decisionByAsset[asset] || {};
    const a = allocByAsset[asset] || {};

    const valueUsd = numFront_(getFirstFront_(d, ['Valor USD','Valor actual USD','Valor'])) || numFront_(getFirstFront_(row, ['Valor actual USD','Valor USD','Valor']));
    const weight = pctFront_(getFirstFront_(d, ['% cartera','Peso cartera','Peso'])) || pctFront_(getFirstFront_(row, ['% cartera','Peso cartera','Peso']));
    const avgCost = numFront_(getFirstFront_(d, ['Precio medio reconstruido'])) || numFront_(getFirstFront_(row, ['Precio medio compra reconstruido USD','Precio medio reconstruido']));
    const marketPrice = numFront_(getFirstFront_(d, ['Precio mercado'])) || numFront_(getFirstFront_(m, ['Precio mercado USD','Precio','Precio actual']));
    const pnlPct = (avgCost > 0 && marketPrice > 0) ? (marketPrice / avgCost - 1) : 0;

    return {
      asset,
      quantity: numFront_(getFirstFront_(row, ['Cantidad actual','Cantidad','Total','Holdings'])),
      valueUsd,
      weight,
      price: marketPrice,
      change24h: pctFront_(getFirstFront_(m, ['Cambio 24h %','Cambio 24h','24h %'])),
      action: String(getFirstFront_(d, ['Acción','Accion','Recomendación','Recomendacion']) || 'SIN DATOS'),
      engineAction: String(getFirstFront_(d, ['Acción motor','Accion motor']) || ''),
      confidence: pctFront_(getFirstFront_(d, ['Confianza %','Confianza'])),
      entry: String(getFirstFront_(d, ['Entrada objetivo','Entrada','Zona entrada']) || ''),
      tp1: getFirstFront_(d, ['TP1','Objetivo 1']) || '',
      tp2: getFirstFront_(d, ['TP2','Objetivo 2']) || '',
      stop: getFirstFront_(d, ['Invalidación/Stop','Invalidación','Invalidacion','Stop']) || '',
      horizon: String(getFirstFront_(d, ['Horizonte']) || ''),
      thesis: String(getFirstFront_(d, ['Tesis / motivo','Tesis','Motivo','Comentario motor']) || ''),
      capitalSuggested: numFront_(getFirstFront_(d, ['Capital sugerido USD','Capital sugerido','Capital USD'])),
      proposalPct: pctFront_(getFirstFront_(d, ['Sizing dinámico %','Propuesta %'])),
      proposalUsd: numFront_(getFirstFront_(d, ['Sizing dinámico USD','Propuesta USD'])),
      proposalUnits: numFront_(getFirstFront_(d, ['Sizing dinámico unidades','Propuesta unidades'])),
      sizingReason: String(getFirstFront_(d, ['Sizing motivo']) || ''),
      proposalType: String(getFirstFront_(d, ['Tipo propuesta']) || ''),
      proposalText: String(getFirstFront_(d, ['Propuesta operativa']) || ''),
      operationalTrigger: String(getFirstFront_(d, ['Condición operativa','Condicion operativa']) || ''),
      operationalPlan: String(getFirstFront_(d, ['Plan operativo']) || ''),
      scoreTechnical: numFront_(getFirstFront_(d, ['Score técnico','Score tecnico'])),
      scorePortfolio: numFront_(getFirstFront_(d, ['Score cartera'])),
      scoreOpportunity: numFront_(getFirstFront_(d, ['Score oportunidad'])),
      scoreFinal: numFront_(getFirstFront_(d, ['Score final'])),
      dataStatus: String(getFirstFront_(d, ['Estado dato','Frescura']) || ''),
      marketDate: String(getFirstFront_(d, ['Fecha mercado','Última revisión','Ultima revisión']) || getFirstFront_(m, ['Fecha actualización']) || ''),
      forecast24Base: numFront_(getFirstFront_(d,['Proy 24h base'])),
      forecast24Min: numFront_(getFirstFront_(d,['Proy 24h min'])),
      forecast24Max: numFront_(getFirstFront_(d,['Proy 24h max'])),
      forecast7Base: numFront_(getFirstFront_(d,['Proy 7d base'])),
      forecast7Min: numFront_(getFirstFront_(d,['Proy 7d min'])),
      forecast7Max: numFront_(getFirstFront_(d,['Proy 7d max'])),
      forecast30Base: numFront_(getFirstFront_(d,['Proy 30d base'])),
      forecast30Min: numFront_(getFirstFront_(d,['Proy 30d min'])),
      forecast30Max: numFront_(getFirstFront_(d,['Proy 30d max'])),
      forecastBullProb: pctFront_(getFirstFront_(d,['Prob alcista'])),
      forecastConfidence: pctFront_(getFirstFront_(d,['Confianza pronóstico'])),
      forecastScenario: String(getFirstFront_(d,['Escenario futuro'])||''),
      forecastReason: String(getFirstFront_(d,['Motivo pronóstico'])||''),

      rsi4h: numFront_(getFirstFront_(d, ['RSI 4H'])) || numFront_(getFirstFront_(m, ['RSI 4H'])),
      rsi1d: numFront_(getFirstFront_(d, ['RSI 1D'])) || numFront_(getFirstFront_(m, ['RSI 1D'])),
      rsi1w: numFront_(getFirstFront_(d, ['RSI 1W'])) || numFront_(getFirstFront_(m, ['RSI 1W'])),
      trend4h: String(getFirstFront_(d, ['Tend. 4H']) || getFirstFront_(m, ['Tendencia 4H']) || ''),
      trend1d: String(getFirstFront_(d, ['Tend. 1D']) || getFirstFront_(m, ['Tendencia 1D']) || ''),
      trend1w: String(getFirstFront_(d, ['Tend. 1W']) || getFirstFront_(m, ['Tendencia 1W']) || ''),
      support: getFirstFront_(d, ['Soporte']) || getFirstFront_(m, ['Soporte']) || '',
      resistance: getFirstFront_(d, ['Resistencia']) || getFirstFront_(m, ['Resistencia']) || '',
      fib382: getFirstFront_(d, ['Fib 38,2']) || getFirstFront_(m, ['Fib 38,2%']) || '',
      fib50: getFirstFront_(d, ['Fib 50']) || getFirstFront_(m, ['Fib 50%']) || '',
      fib618: getFirstFront_(d, ['Fib 61,8']) || getFirstFront_(m, ['Fib 61,8%']) || '',

      avgCost,
      pnlPct,
      capitalPending: numFront_(getFirstFront_(row, ['Capital pendiente recuperar USD'])),
      capitalState: String(getFirstFront_(row, ['Estado capital']) || ''),
      costConfidence: String(getFirstFront_(row, ['Confianza coste']) || ''),
      purchasesCost: numFront_(getFirstFront_(row, ['Coste compras identificado USD'])),
      salesProceeds: numFront_(getFirstFront_(row, ['Ingresos ventas identificados USD'])),
      rewards: numFront_(getFirstFront_(row, ['Rewards/intereses identificados'])),
      rewardsPct: pctFront_(getFirstFront_(row, ['% unidades por rewards'])),
      location: String(getFirstFront_(row, ['Ubicación actual','Ubicacion actual']) || ''),
      availability: String(getFirstFront_(row, ['Disponibilidad']) || ''),
      positionType: String(getFirstFront_(row, ['Tipo posición','Tipo posicion']) || ''),
      sourceCost: String(getFirstFront_(row, ['Fuente coste']) || ''),
      reconstructionNotes: String(getFirstFront_(row, ['Notas reconstrucción','Notas reconstruccion']) || ''),

      targetWeight: pctFront_(getFirstFront_(a, ['Peso objetivo %','Peso objetivo','Objetivo','Objetivo %'])),
      maxWeight: pctFront_(getFirstFront_(a, ['Peso máximo %','Peso maximo %','Peso máximo','Peso maximo','Máximo','Maximo'])),
      priority: String(getFirstFront_(a, ['Prioridad']) || '')
    };
  }).filter(Boolean);

  assets.forEach(x => { enrichForecastV44_(x); enrichPlanV44_(x); enrichDualDecisionV45_(x); });
  assets.sort((x,y) => y.valueUsd - x.valueUsd);
  const total = assets.reduce((s,x) => s + (x.valueUsd || 0), 0);
  const usdc = assets.find(x => x.asset === 'USDC');
  const reserveTarget = usdc?.targetWeight || 0.50;
  const investable = Math.max(0, (usdc?.valueUsd || 0) - total * reserveTarget);
  const soloGainsValue = assets.filter(x => /SOLO GANANCIAS/i.test(x.capitalState)).reduce((s,x) => s + x.valueUsd, 0);
  const capitalPending = assets.reduce((s,x) => s + (x.capitalPending || 0), 0);
  const rewardsValueApprox = assets.reduce((s,x) => s + ((x.rewardsPct || 0) * (x.valueUsd || 0)), 0);
  const actionableActions = ['AUMENTAR','ESPERAR ENTRADA','ASEGURAR BENEFICIO','REDUCIR EN REBOTE','VENDER','REVISAR DATOS'];

  const nowActions = assets
    .filter(x => actionableActions.includes(x.action))
    .sort((a,b) => ((b.confidence||0) - (a.confidence||0)) || ((b.valueUsd||0) - (a.valueUsd||0)))
    .slice(0, 8);

  const opportunities = assets
    .filter(x => ['AUMENTAR','ESPERAR ENTRADA','MANTENER'].includes(x.action) && x.asset !== 'USDC')
    .sort((a,b) => ((b.scoreFinal||0)-(a.scoreFinal||0)) || ((b.confidence||0)-(a.confidence||0)))
    .slice(0, 8);

  const alerts = alertas.slice(-120).reverse().map(r => ({
    date: String(getFirstFront_(r, ['Fecha','Timestamp','Fecha alerta']) || ''),
    asset: String(getFirstFront_(r, ['Activo','Asset']) || ''),
    type: String(getFirstFront_(r, ['Tipo alerta','Tipo']) || ''),
    message: String(getFirstFront_(r, ['Mensaje','Detalle','Descripción','Descripcion']) || ''),
    action: String(getFirstFront_(r, ['Acción','Accion']) || ''),
    price: numFront_(getFirstFront_(r, ['Precio'])),
    confidence: pctFront_(getFirstFront_(r, ['Confianza %','Confianza'])),
    status: String(getFirstFront_(r, ['Estado']) || ''),
    capitalSuggested: numFront_(getFirstFront_(r,['Capital sugerido USD'])),
    firstDetected: String(getFirstFront_(r,['Primera detección','Primera deteccion']) || ''),
    lastConfirmed: String(getFirstFront_(r,['Última confirmación','Ultima confirmacion']) || ''),
    repeats: numFront_(getFirstFront_(r,['Repeticiones'])) || 1
  })).filter(x => !x.status || /ABIERTA|OPEN|ACTIVA/i.test(x.status));

  const radar = radarRows.map(r => ({
    asset: String(getFirstFront_(r,['Activo'])||''),
    pair: String(getFirstFront_(r,['Par'])||''),
    price: numFront_(getFirstFront_(r,['Precio'])),
    change24h: pctFront_(getFirstFront_(r,['Cambio 24h %'])),
    volume24h: numFront_(getFirstFront_(r,['Volumen 24h USD'])),
    rsi4h: numFront_(getFirstFront_(r,['RSI 4H'])),
    rsi1d: numFront_(getFirstFront_(r,['RSI 1D'])),
    rsi1w: numFront_(getFirstFront_(r,['RSI 1W'])),
    trend4h: String(getFirstFront_(r,['Tend. 4H'])||''),
    trend1d: String(getFirstFront_(r,['Tend. 1D'])||''),
    trend1w: String(getFirstFront_(r,['Tend. 1W'])||''),
    support: numFront_(getFirstFront_(r,['Soporte'])),
    resistance: numFront_(getFirstFront_(r,['Resistencia'])),
    entry: String(getFirstFront_(r,['Entrada objetivo'])||''),
    scoreTechnical: numFront_(getFirstFront_(r,['Score técnico'])),
    scoreOpportunity: numFront_(getFirstFront_(r,['Score oportunidad'])),
    scoreFinal: numFront_(getFirstFront_(r,['Score final'])),
    action: String(getFirstFront_(r,['Acción'])||''),
    capitalSuggested: numFront_(getFirstFront_(r,['Capital sugerido USD'])),
    unitsSuggested: numFront_(getFirstFront_(r,['Unidades sugeridas'])),
    tp1: numFront_(getFirstFront_(r,['TP1'])),
    tp2: numFront_(getFirstFront_(r,['TP2'])),
    stop: numFront_(getFirstFront_(r,['Stop'])),
    date: String(getFirstFront_(r,['Fecha'])||''),
    sector: String(getFirstFront_(r,['Sector'])||''),
    risk: String(getFirstFront_(r,['Riesgo'])||''),
    portfolioFit: String(getFirstFront_(r,['Aporte a cartera'])||''),
    radarReason: String(getFirstFront_(r,['Motivo radar'])||''),
    forecast24Base: numFront_(getFirstFront_(r,['Proy 24h base'])),
    forecast24Min: numFront_(getFirstFront_(r,['Proy 24h min'])),
    forecast24Max: numFront_(getFirstFront_(r,['Proy 24h max'])),
    forecast7Base: numFront_(getFirstFront_(r,['Proy 7d base'])),
    forecast7Min: numFront_(getFirstFront_(r,['Proy 7d min'])),
    forecast7Max: numFront_(getFirstFront_(r,['Proy 7d max'])),
    forecast30Base: numFront_(getFirstFront_(r,['Proy 30d base'])),
    forecast30Min: numFront_(getFirstFront_(r,['Proy 30d min'])),
    forecast30Max: numFront_(getFirstFront_(r,['Proy 30d max'])),
    forecastBullProb: pctFront_(getFirstFront_(r,['Prob alcista'])),
    forecastConfidence: pctFront_(getFirstFront_(r,['Confianza pronóstico'])),
    forecastScenario: String(getFirstFront_(r,['Escenario futuro'])||''),
    forecastReason: String(getFirstFront_(r,['Motivo pronóstico'])||'')
  })).filter(x=>x.asset);

  radar.forEach(x => enrichForecastV44_(x));

  const wallets = walletsRows.map(r => ({
    wallet: String(getFirstFront_(r,['Wallet'])||''),
    network: String(getFirstFront_(r,['Red'])||''),
    address: String(getFirstFront_(r,['Direccion publica','Dirección pública'])||''),
    endpoint: String(getFirstFront_(r,['Endpoint'])||''),
    active: String(getFirstFront_(r,['Activa'])||''),
    lastSync: String(getFirstFront_(r,['Ultima sync','Última sync'])||''),
    status: String(getFirstFront_(r,['Estado'])||''),
    notes: String(getFirstFront_(r,['Notas'])||'')
  })).filter(x=>x.wallet);

  const onchain = onchainRows.map(r => {
    const asset=String(getFirstFront_(r,['Activo'])||'');
    const a=assets.find(x=>x.asset===asset);
    const totalChain=numFront_(getFirstFront_(r,['Total on-chain']));
    return {
      wallet:String(getFirstFront_(r,['Wallet'])||''),
      network:String(getFirstFront_(r,['Red'])||''),
      asset,
      available:numFront_(getFirstFront_(r,['Disponible'])),
      staking:numFront_(getFirstFront_(r,['Staking'])),
      rewards:numFront_(getFirstFront_(r,['Rewards pendientes'])),
      total:totalChain,
      valueUsd:a ? totalChain*(a.price||0) : 0,
      source:String(getFirstFront_(r,['Fuente'])||''),
      sync:String(getFirstFront_(r,['Fecha sync'])||''),
      note:String(getFirstFront_(r,['Estado / notas'])||'')
    };
  }).filter(x=>x.asset);

  const reconciliation = reconciliationRows.map(r => ({
    asset:String(getFirstFront_(r,['Activo'])||''),
    walletNetwork:String(getFirstFront_(r,['Wallet/red'])||''),
    onchain:numFront_(getFirstFront_(r,['Total on-chain'])),
    registered:numFront_(getFirstFront_(r,['Cantidad registrada ubicacion','Cantidad registrada ubicación'])),
    delta:numFront_(getFirstFront_(r,['Delta'])),
    autoApply:String(getFirstFront_(r,['Auto-aplicar'])||''),
    status:String(getFirstFront_(r,['Estado'])||''),
    sync:String(getFirstFront_(r,['Ultima sync','Última sync'])||''),
    notes:String(getFirstFront_(r,['Notas'])||'')
  })).filter(x=>x.asset);

  const forecastCalibration = calibrationRows.map(r => ({
    horizon:String(getFirstFront_(r,['Horizonte'])||''), samples:numFront_(getFirstFront_(r,['Muestras'])),
    rangeCoverage:pctFront_(getFirstFront_(r,['Cobertura rango'])), directionHit:pctFront_(getFirstFront_(r,['Acierto dirección'])),
    avgError:pctFront_(getFirstFront_(r,['Error medio abs %'])), status:String(getFirstFront_(r,['Estado'])||''), factor:numFront_(getFirstFront_(r,['Factor sizing']))
  })).filter(x=>x.horizon);

  const historicalReconciliation = historicalReconRows.map(r => ({
    asset:String(getFirstFront_(r,['Activo'])||''), avgCost:numFront_(getFirstFront_(r,['Precio medio reconstruido'])),
    purchases:numFront_(getFirstFront_(r,['Compras identificadas USD'])), sales:numFront_(getFirstFront_(r,['Ventas identificadas USD'])),
    capitalPending:numFront_(getFirstFront_(r,['Capital pendiente USD'])), state:String(getFirstFront_(r,['Estado capital'])||''),
    confidence:String(getFirstFront_(r,['Confianza'])||''), sources:String(getFirstFront_(r,['Fuentes conciliadas'])||''), notes:String(getFirstFront_(r,['Notas'])||'')
  })).filter(x=>x.asset);

  const performance = rendimiento.map(r => ({
    action: String(getFirstFront_(r, ['Acción','Accion']) || ''),
    samples24h: numFront_(getFirstFront_(r, ['Muestras 24h'])),
    hits24h: numFront_(getFirstFront_(r, ['Aciertos 24h'])),
    hitRate24h: pctFront_(getFirstFront_(r, ['Tasa acierto 24h'])),
    avgReturn24h: pctFront_(getFirstFront_(r, ['Retorno medio 24h'])),
    samples7d: numFront_(getFirstFront_(r, ['Muestras 7d'])),
    hits7d: numFront_(getFirstFront_(r, ['Aciertos 7d'])),
    hitRate7d: pctFront_(getFirstFront_(r, ['Tasa acierto 7d'])),
    avgReturn7d: pctFront_(getFirstFront_(r, ['Retorno medio 7d']))
  })).filter(x => x.action);

  return {
    generatedAt: new Date().toISOString(),
    versions: { front: 'v4.7.1', backend: 'v2.9.0' },
    summary: {
      total,
      usdc: usdc?.valueUsd || 0,
      usdcWeight: total ? (usdc?.valueUsd || 0) / total : 0,
      investable,
      reserveTarget,
      positions: assets.length,
      actionable: assets.filter(x => actionableActions.includes(x.action)).length,
      soloGainsValue,
      soloGainsWeight: total ? soloGainsValue / total : 0,
      capitalPending,
      rewardsValueApprox
    },
    assets,
    nowActions,
    opportunities,
    alerts,
    performance,
    forecastCalibration,
    historicalReconciliation,
    radar,
    wallets,
    onchain,
    reconciliation,
    operations
  };
}

function frontUpdateNow() {
  if (typeof updateCryptoMarket !== 'function') throw new Error('No existe updateCryptoMarket() en el proyecto.');
  updateCryptoMarket();
  return getFrontData();
}

function readSheetObjectsFront_(ss, name) {
  const sh = ss.getSheetByName(name);
  if (!sh) return [];
  const values = sh.getDataRange().getDisplayValues();
  if (values.length < 2) return [];
  const headers = values[0].map(h => String(h).trim());
  return values.slice(1).filter(r => r.some(v => String(v).trim() !== '')).map(r => {
    const o = {};
    headers.forEach((h,i) => { if (h) o[h] = r[i]; });
    return o;
  });
}

function indexByAssetFront_(rows) {
  const out = {};
  rows.forEach(r => {
    const a = String(getFirstFront_(r, ['Activo','Asset','Símbolo','Simbolo']) || '').trim();
    if (a) out[a] = r;
  });
  return out;
}

function getFirstFront_(obj, keys) {
  for (const k of keys) if (obj && obj[k] !== undefined && obj[k] !== '') return obj[k];
  return '';
}

function numFront_(v) {
  if (typeof v === 'number') return v;
  if (v === null || v === undefined || v === '') return 0;
  let s = String(v).replace(/\s/g,'').replace(/\$/g,'').replace(/USD/gi,'').replace(/€/g,'');
  if (s.includes(',') && s.includes('.')) {
    if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g,'').replace(',','.');
    else s = s.replace(/,/g,'');
  } else if (s.includes(',')) s = s.replace(',','.');
  const n = Number(s.replace(/[^0-9+\-.]/g,''));
  return Number.isFinite(n) ? n : 0;
}

function pctFront_(v) {
  if (v === null || v === undefined || v === '') return 0;
  const s = String(v).trim();
  const n = numFront_(s);
  return s.includes('%') ? n / 100 : (Math.abs(n) > 1 ? n / 100 : n);
}


// ===== Front v4.4 helpers: pronóstico y plan simplificado con fallback =====
function clampFrontV44_(v,lo,hi){ return Math.max(lo,Math.min(hi,v)); }
function trendScoreFrontV44_(v){
  const s=String(v||'').toUpperCase();
  if(/ALCISTA|BULL/.test(s)) return 1;
  if(/BAJISTA|BEAR/.test(s)) return -1;
  return 0;
}
function enrichForecastV44_(x){
  if(!x || !(Number(x.price)>0)) return x;
  if(x.forecast24Base && x.forecast7Base && x.forecast30Base) return x;
  const price=Number(x.price)||0;
  let bias=.20*trendScoreFrontV44_(x.trend4h)+.45*trendScoreFrontV44_(x.trend1d)+.35*trendScoreFrontV44_(x.trend1w);
  const r1d=Number(x.rsi1d)||0, r1w=Number(x.rsi1w)||0;
  if(r1d>0&&r1d<35) bias+=.16; else if(r1d>65) bias-=.16;
  if(r1w>0&&r1w<40) bias+=.08; else if(r1w>65) bias-=.08;
  const support=Number(x.support)||0, resistance=Number(x.resistance)||0;
  if(support>0 && price/support<=1.04) bias+=.10;
  if(resistance>0 && resistance/price<=1.04) bias-=.10;
  bias=clampFrontV44_(bias,-1,1);
  let rangePct=0;
  if(support>0&&resistance>support) rangePct=(resistance-support)/price;
  const vol=clampFrontV44_(Math.max(Math.abs(Number(x.change24h)||0),rangePct>0?rangePct/6:0,.018),.018,.12);
  const align=Math.abs(.20*trendScoreFrontV44_(x.trend4h)+.45*trendScoreFrontV44_(x.trend1d)+.35*trendScoreFrontV44_(x.trend1w));
  const baseConf=clampFrontV44_(Number(x.confidence||x.scoreFinal/100||.6),.4,.9);
  const conf=clampFrontV44_(.42+align*.22+baseConf*.32,.45,.86);
  const bull=clampFrontV44_(.50+bias*.30,.20,.80);
  const scenario=bias>.22?'ALCISTA':(bias<-.22?'BAJISTA':'NEUTRAL');
  function h(days,capBase,capBand){
    const scale=Math.sqrt(days);
    const baseRet=clampFrontV44_(bias*vol*scale*.46,-capBase,capBase);
    const band=clampFrontV44_(vol*scale*.95,.015,capBand);
    return {base:price*(1+baseRet),min:Math.max(price*.05,price*(1+baseRet-band)),max:price*(1+baseRet+band)};
  }
  const a=h(1,.12,.15), b=h(7,.28,.35), c=h(30,.55,.65);
  x.forecast24Base=a.base; x.forecast24Min=a.min; x.forecast24Max=a.max;
  x.forecast7Base=b.base; x.forecast7Min=b.min; x.forecast7Max=b.max;
  x.forecast30Base=c.base; x.forecast30Min=c.min; x.forecast30Max=c.max;
  x.forecastBullProb=bull; x.forecastConfidence=conf; x.forecastScenario=scenario;
  x.forecastReason='Estimación técnica por tendencia 4H/1D/1W, RSI y cercanía a soporte/resistencia. Es un rango probabilístico, no una garantía.';
  return x;
}

function enrichDualDecisionV45_(x){
  if(!x) return x;
  const action=String(x.action||'').toUpperCase();
  const qty=Number(x.quantity)||0, value=Number(x.valueUsd)||0, price=Number(x.price)||0;
  let pAct='MANTENER', pText='Mantener la posición actual.', pPct=0, pUsd=0, pUnits=0, pTrigger='';
  let nAct='NO COMPRAR', nText='No agregar capital nuevo ahora.', nUsd=0, nUnits=0, nTrigger='';

  if(action==='ASEGURAR BENEFICIO'){
    pPct=Number(x.proposalPct)||.10; pUsd=Number(x.proposalUsd)||value*pPct; pUnits=Number(x.proposalUnits)||qty*pPct;
    pAct='VENDER '+Math.round(pPct*100)+' %';
    pText='Asegurar una parte de la ganancia y mantener el resto.';
    pTrigger=x.operationalTrigger||'Ahora o cerca de resistencia si pierde fuerza.';
    nAct='NO COMPRAR'; nText='No aumentar mientras siga cerca de resistencia.';
  } else if(action==='REDUCIR EN REBOTE'){
    pPct=Number(x.proposalPct)||(x.asset==='CAKE'?.25:(x.asset==='ADA'?.15:.20));
    pUsd=Number(x.proposalUsd)||value*pPct; pUnits=Number(x.proposalUnits)||qty*pPct;
    pAct='MANTENER AHORA';
    pText='No vender en mínimos. Preparar una reducción de '+Math.round(pPct*100)+' % solo si rebota.';
    pTrigger=x.operationalTrigger||x.resistance?('Reducir en recuperación hacia '+(x.resistance||'resistencia')):'Reducir solo con recuperación clara.';
    nAct='NO COMPRAR'; nText='No añadir capital mientras la estructura siga débil.';
  } else if(action==='VENDER'){
    pPct=1; pUsd=value; pUnits=qty; pAct='VENDER'; pText='Cerrar la posición si se confirma la señal de salida.'; pTrigger=x.operationalTrigger||'Confirmar deterioro antes de ejecutar.';
    nAct='NO COMPRAR'; nText='No abrir nueva exposición.';
  } else if(action==='AUMENTAR' || action==='COMPRAR'){
    pAct='MANTENER'; pText='Mantener lo que ya tenés.';
    nUsd=Number(x.capitalSuggested)||Number(x.proposalUsd)||300; nUnits=price>0?nUsd/price:0; nAct='COMPRAR AHORA';
    nText='Agregar un primer tramo de '+Math.round(nUsd)+' USD.'; nTrigger=x.entry?('Comprar solo en '+x.entry):'Comprar solo mientras la señal siga favorable.';
  } else if(action==='ESPERAR ENTRADA'){
    pAct='MANTENER'; pText='Mantener la posición actual; no vender por esta señal.';
    nUsd=Number(x.capitalSuggested)||Number(x.proposalUsd)||300; nUnits=price>0?nUsd/price:0; nAct='ESPERAR PARA COMPRAR';
    nText='No comprar a mercado. Preparar '+Math.round(nUsd)+' USD si entra en la zona objetivo.'; nTrigger=x.entry?('Zona '+x.entry):'Esperar mejor precio.';
  } else if(action==='NO AUMENTAR'){
    pAct='MANTENER'; pText='Mantener la posición actual.'; nAct='NO COMPRAR'; nText='No agregar capital nuevo por ahora.'; nTrigger='Esperar mejora técnica o mejor precio.';
  } else if(action==='MANTENER RESIDUAL'){
    pAct='MANTENER RESIDUAL'; pText='Mantener sin operar por su bajo impacto.'; nAct='NO COMPRAR'; nText='No destinar capital nuevo a esta posición.';
  } else if(action==='MANTENER RESERVA'){
    pAct='RESERVA'; pText='Mantener como liquidez disponible.'; nAct='DESPLEGAR SOLO CON SEÑAL'; nText='Usar por tramos únicamente cuando aparezca una oportunidad válida.';
  } else if(action==='REVISAR DATOS'){
    pAct='NO OPERAR'; pText='Esperar actualización de datos antes de decidir.'; nAct='NO COMPRAR'; nText='No invertir con datos obsoletos.';
  } else {
    pAct='MANTENER'; pText='Mantener la posición actual.'; nAct='NO COMPRAR AHORA'; nText='No hay señal suficiente para agregar capital.';
  }

  x.positionAction=pAct; x.positionText=pText; x.positionPct=pPct; x.positionUsd=pUsd; x.positionUnits=pUnits; x.positionTrigger=pTrigger;
  x.newMoneyAction=nAct; x.newMoneyText=nText; x.newMoneyUsd=nUsd; x.newMoneyUnits=nUnits; x.newMoneyTrigger=nTrigger;
  return x;
}

function enrichPlanV44_(x){
  if(!x) return x;
  const action=String(x.action||'').toUpperCase();
  const qty=Number(x.quantity)||0, value=Number(x.valueUsd)||0, price=Number(x.price)||0;
  if(x.proposalText && (x.proposalUsd||x.capitalSuggested||x.proposalUnits||x.proposalPct)) return x;
  let pct=0, usd=0, units=0, text='', trigger='';
  if(action==='ASEGURAR BENEFICIO'){
    pct=.10; units=qty*pct; usd=value*pct; text='Vender 10 % de la posición para asegurar una parte de la ganancia.'; trigger='Ahora o cerca de resistencia si el precio pierde fuerza.';
  } else if(action==='REDUCIR EN REBOTE'){
    pct=x.asset==='CAKE'?.25:(x.asset==='ADA'?.15:.20); units=qty*pct; usd=value*pct; text='No vender en mínimos. Reducir '+Math.round(pct*100)+' % de la posición si aparece un rebote.'; trigger=x.resistance?('En rebote hacia '+x.resistance):'Solo con recuperación clara del precio.';
  } else if(action==='VENDER'){
    pct=1; units=qty; usd=value; text='Cerrar la posición completa si se confirma la señal de salida.'; trigger='Confirmación de deterioro o pérdida del nivel de invalidación.';
  } else if(action==='AUMENTAR' || action==='COMPRAR'){
    usd=Number(x.capitalSuggested)||Math.min(300,Math.max(100,value*.25)); units=price>0?usd/price:0; text='Comprar un primer tramo de '+Math.round(usd)+' USD.'; trigger=x.entry?('Solo dentro de la zona '+x.entry):'Solo con señal técnica favorable.';
  } else if(action==='ESPERAR ENTRADA'){
    usd=Number(x.capitalSuggested)||300; units=price>0?usd/price:0; text='No comprar ahora. Preparar un primer tramo de '+Math.round(usd)+' USD si entra en la zona objetivo.'; trigger=x.entry?('Entrada '+x.entry):'Esperar mejor precio.';
  } else if(action==='NO AUMENTAR'){
    text='No agregar capital nuevo por ahora.'; trigger='Revisar cuando mejore la tendencia o vuelva a una zona de entrada.';
  } else if(action==='MANTENER' || action==='MANTENER RESIDUAL' || action==='MANTENER RESERVA'){
    text='Mantener. No hay operación necesaria ahora.'; trigger='Actuar solo si cambia la señal.';
  }
  if(text){
    x.proposalPct=x.proposalPct||pct; x.proposalUsd=x.proposalUsd||usd; x.proposalUnits=x.proposalUnits||units;
    x.proposalText=x.proposalText||text; x.operationalTrigger=x.operationalTrigger||trigger; x.operationalPlan=x.operationalPlan||action;
  }
  return x;
}

function frontRegisterOperationV47(payload){const result=registerOperationV47(payload||{});try{recalculateDecisionEngineV23_();}catch(e){console.log(e.message)}try{augmentTradingProposalsV25_();}catch(e){console.log(e.message)}return {result:result,data:getFrontData()};}
