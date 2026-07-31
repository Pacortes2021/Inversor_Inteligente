/* Gráficos ECharts con tema propio — El Inversor Inteligente */

/** Colores que se adaptan al tema claro/oscuro en tiempo de ejecución */
function getChartColors() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    gold:   '#d97706', green:  '#10b981', red:    '#ef4444',
    blue:   '#3b82f6', cyan:   '#0ea5e9', violet: '#8b5cf6', amber: '#d97706',
    text:   dark ? '#f8fafc'  : '#1e293b',
    muted:  dark ? '#94a3b8'  : '#64748b',
    border: dark ? '#1e293b'  : '#e2e8f0',
    grid:   dark ? '#1a2236'  : '#f1f5f9',
    panel:  dark ? 'rgba(17,24,39,0.96)' : 'rgba(255,255,255,0.98)',
  };
}

/* Alias estático C mantenido para compat. con referencias en makeChart/hideCard */
const C = {
  gold: '#d97706', green: '#10b981', red: '#ef4444', blue: '#3b82f6',
  cyan: '#0ea5e9', violet: '#8b5cf6', amber: '#d97706',
  text: '#1e293b', muted: '#64748b', border: '#e2e8f0', grid: '#f1f5f9',
};

const charts = {};

function makeChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (charts[id]) charts[id].dispose();
  const ch = echarts.init(el, null, { renderer: 'canvas' });
  ch.setOption(option);
  charts[id] = ch;
  return ch;
}

window.addEventListener('resize', () => Object.values(charts).forEach(c => c.resize()));

/* Cuando cambie el tema, re-renderizar todos los gráficos activos */
window.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.addEventListener('click', () => {
      setTimeout(() => {
        if (window.state && window.state.data) {
          const activePane = document.querySelector('.a-tab.active');
          const pane = activePane ? activePane.dataset.pane : null;
          if (pane === 'financials') renderAllCharts(window.state.data);
          else if (pane === 'ratios') renderRatiosCharts(window.state.data, window.currentMultiplesRange || 'all');
          else if (pane === 'summary') chartPriceSummary(window.state.data);
        }
      }, 80);
    });
  }
});

function hideCard(id) {
  const el = document.getElementById(id);
  if (el) {
    const card = el.closest('.chart-card') || el.closest('.card');
    if (card) card.classList.add('hidden');
  }
}
function showCard(id) {
  const el = document.getElementById(id);
  if (el) {
    const card = el.closest('.chart-card') || el.closest('.card');
    if (card) card.classList.remove('hidden');
  }
}

/* ---------------------------------------------------------- base común */
function baseAxisStyle(cc) {
  return {
    axisLine: { lineStyle: { color: cc.border } },
    axisLabel: { color: cc.muted, fontSize: 10, fontFamily: 'Inter, sans-serif' },
    splitLine: { lineStyle: { color: cc.grid } },
  };
}

/* Retro-compatibilidad: baseAxis legacy (usa colores estáticos) */
const baseAxis = {
  axisLine: { lineStyle: { color: C.border } },
  axisLabel: { color: C.muted, fontSize: 10, fontFamily: 'Inter, sans-serif' },
  splitLine: { lineStyle: { color: C.grid } },
};

function timeOption(extra) {
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  return Object.assign({
    animationDuration: 500,
    grid: { left: 45, right: 12, top: 16, bottom: 36 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: cc.panel, borderColor: cc.border,
      borderWidth: 1, borderRadius: 8, padding: [12, 16],
      textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' },
      axisPointer: { type: 'cross', label: { backgroundColor: cc.muted, color: '#fff' }, lineStyle: { type: 'dashed', color: cc.muted } },
    },
    xAxis: Object.assign({ type: 'time' }, ba, { splitLine: { show: false } }),
    yAxis: Object.assign({ type: 'value', scale: true }, ba),
  }, extra);
}

function yearsOption(years, extra) {
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  return Object.assign({
    animationDuration: 500,
    grid: { left: 45, right: 12, top: 24, bottom: 24 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: cc.panel, borderColor: cc.border,
      borderWidth: 1, borderRadius: 8, padding: [12, 16],
      textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' },
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(128,128,128,0.05)' } }
    },
    legend: { textStyle: { color: cc.muted, fontSize: 11, fontWeight: 500 }, top: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
    xAxis: Object.assign({ type: 'category', data: years }, ba, { splitLine: { show: false } }),
    yAxis: Object.assign({ type: 'value', scale: true }, ba),
  }, extra);
}

/* ------------------------------------------------------------- precio */
const priceView = { log: false, sma: false, type: 'area' };

function sma(pts, n) {
  const out = [];
  let sum = 0;
  for (let i = 0; i < pts.length; i++) {
    sum += pts[i][1];
    if (i >= n) sum -= pts[i - n][1];
    if (i >= n - 1) out.push([pts[i][0], +(sum / n).toFixed(2)]);
  }
  return out;
}

function calculateEMA(pts, period) {
  const out = [];
  const k = 2 / (period + 1);
  let ema = pts[0][1];
  out.push([pts[0][0], ema]);
  for (let i = 1; i < pts.length; i++) {
    ema = (pts[i][1] * k) + (ema * (1 - k));
    out.push([pts[i][0], ema]);
  }
  return out;
}

function calculateMACD(pts, shortP = 12, longP = 26, sigP = 9) {
  const macdLine = [];
  const signalLine = [];
  const histogram = [];
  if (pts.length < longP) return { macdLine, signalLine, histogram };
  
  const shortEma = calculateEMA(pts, shortP);
  const longEma = calculateEMA(pts, longP);
  
  for (let i = 0; i < pts.length; i++) {
    const ts = pts[i][0];
    const macdVal = shortEma[i][1] - longEma[i][1];
    macdLine.push([ts, macdVal]);
  }
  
  const sigEma = calculateEMA(macdLine, sigP);
  for (let i = 0; i < pts.length; i++) {
    const ts = pts[i][0];
    const macdVal = macdLine[i][1];
    const sigVal = sigEma[i][1];
    signalLine.push([ts, sigVal]);
    histogram.push([ts, macdVal - sigVal]);
  }
  
  return { macdLine, signalLine, histogram };
}

function calculateRSI(pts, period = 14) {
  const out = [];
  if (pts.length < period) return out;
  
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const change = pts[i][1] - pts[i - 1][1];
    if (change > 0) gain += change;
    else loss -= change;
  }
  
  let avgGain = gain / period;
  let avgLoss = loss / period;
  
  for (let i = period; i < pts.length; i++) {
    if (i > period) {
      const change = pts[i][1] - pts[i - 1][1];
      avgGain = (avgGain * (period - 1) + (change > 0 ? change : 0)) / period;
      avgLoss = (avgLoss * (period - 1) + (change < 0 ? -change : 0)) / period;
    }
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));
    out.push([pts[i][0], rsi]);
  }
  return out;
}

function chartPrice(data, id = 'ch-price', customPts = null) {
  const pts = customPts || data.history.price;
  if (!pts || pts.length < 5) return hideCard(id);
  showCard(id);
  const cur = data.profile.currency;
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);

  // TradingView dynamic coloring based on the period trend
  const firstPrice = pts[0][1];
  const lastPrice = pts[pts.length - 1][1];
  const isUp = lastPrice >= firstPrice;
  const lineColor = isUp ? cc.green : cc.red;
  const fillStart = isUp ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)';
  const fillEnd   = isUp ? 'rgba(16, 185, 129, 0.01)' : 'rgba(239, 68, 68, 0.01)';

  const isArea = priceView.type === 'area';
  
  const hasMACD = priceView.macd && pts.length > 26;
  const hasRSI = priceView.rsi && pts.length > 14;

  let grids = [];
  let xAxes = [];
  let yAxes = [];
  
  if (hasMACD && hasRSI) {
    grids = [
      { left: 16, right: 65, top: 20, height: '42%' },
      { left: 16, right: 65, top: '53%', height: '18%' },
      { left: 16, right: 65, top: '75%', height: '18%' }
    ];
  } else if (hasMACD || hasRSI) {
    grids = [
      { left: 16, right: 65, top: 20, height: '55%' },
      { left: 16, right: 65, top: '65%', height: '22%' }
    ];
  } else {
    grids = [
      { left: 16, right: 65, top: 20, bottom: 48 }
    ];
  }

  // xAxes setup (one for each grid)
  grids.forEach((g, i) => {
    xAxes.push(Object.assign({ gridIndex: i, type: 'time' }, ba, {
      splitLine: { show: true, lineStyle: { color: cc.grid, type: 'dashed' } },
      axisLabel: { show: i === grids.length - 1, color: cc.muted, fontSize: 10 },
      axisTick: { show: i === grids.length - 1 }
    }));
  });

  // yAxes setup
  yAxes.push(Object.assign(
    priceView.log ? { type: 'log', logBase: 10, min: 'dataMin' } : { type: 'value', scale: true },
    ba,
    { 
      gridIndex: 0, position: 'right', 
      splitLine: { show: true, lineStyle: { color: cc.grid, type: 'dashed' } },
      axisLabel: { color: cc.text, fontSize: 11, fontWeight: '500', formatter: v => fmtBig(v, cur) }
    }
  ));

  let currentGrid = 1;
  const series = [];

  // 1. Price Series
  series.push({
    type: 'line', data: pts, showSymbol: false, name: 'Precio', xAxisIndex: 0, yAxisIndex: 0,
    lineStyle: { color: lineColor, width: 2 },
    areaStyle: isArea ? { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: fillStart }, { offset: 1, color: fillEnd },
    ]) } : undefined,
    tooltip: { valueFormatter: v => fmtPrice(v, cur) },
    markLine: {
      silent: true, symbol: 'none',
      data: [{ 
        yAxis: lastPrice, 
        lineStyle: { color: lineColor, type: 'dashed', width: 1.5 },
        label: { 
          color: '#ffffff', backgroundColor: lineColor, 
          padding: [4, 6], borderRadius: 4, fontSize: 11, fontWeight: 'bold', position: 'end',
          formatter: fmtPrice(lastPrice, cur)
        } 
      }],
    },
  });

  if (priceView.sma && pts.length > 50) {
    series.push({ type: 'line', name: 'SMA 50', data: sma(pts, 50), showSymbol: false, xAxisIndex: 0, yAxisIndex: 0,
      lineStyle: { color: cc.cyan, width: 1.5 }, itemStyle: { color: cc.cyan },
      tooltip: { valueFormatter: v => fmtPrice(v, cur) } });
    series.push({ type: 'line', name: 'SMA 200', data: sma(pts, 200), showSymbol: false, xAxisIndex: 0, yAxisIndex: 0,
      lineStyle: { color: cc.gold, width: 1.5 }, itemStyle: { color: cc.gold },
      tooltip: { valueFormatter: v => fmtPrice(v, cur) } });
  }

  // 2. MACD Series
  if (hasMACD) {
    const macdData = calculateMACD(pts);
    yAxes.push(Object.assign({ type: 'value', scale: true }, ba, {
      gridIndex: currentGrid, position: 'right',
      splitLine: { show: true, lineStyle: { color: cc.grid, type: 'dashed' } },
      axisLabel: { color: cc.muted, fontSize: 10 }
    }));
    
    // Histogram
    series.push({
      type: 'bar', name: 'MACD Hist', data: macdData.histogram, xAxisIndex: currentGrid, yAxisIndex: currentGrid,
      itemStyle: { color: (params) => params.value[1] >= 0 ? cc.green : cc.red },
      tooltip: { valueFormatter: v => v.toFixed(2) }
    });
    // MACD Line
    series.push({
      type: 'line', name: 'MACD', data: macdData.macdLine, showSymbol: false, xAxisIndex: currentGrid, yAxisIndex: currentGrid,
      lineStyle: { color: cc.cyan, width: 1.5 }, tooltip: { valueFormatter: v => v.toFixed(2) }
    });
    // Signal Line
    series.push({
      type: 'line', name: 'Signal', data: macdData.signalLine, showSymbol: false, xAxisIndex: currentGrid, yAxisIndex: currentGrid,
      lineStyle: { color: cc.gold, width: 1.5 }, tooltip: { valueFormatter: v => v.toFixed(2) }
    });
    
    currentGrid++;
  }

  // 3. RSI Series
  if (hasRSI) {
    const rsiData = calculateRSI(pts);
    yAxes.push(Object.assign({ type: 'value', min: 0, max: 100 }, ba, {
      gridIndex: currentGrid, position: 'right',
      splitLine: { show: true, lineStyle: { color: cc.grid, type: 'dashed' } },
      axisLabel: { color: cc.muted, fontSize: 10 }
    }));
    
    series.push({
      type: 'line', name: 'RSI 14', data: rsiData, showSymbol: false, xAxisIndex: currentGrid, yAxisIndex: currentGrid,
      lineStyle: { color: cc.violet, width: 1.5 },
      tooltip: { valueFormatter: v => v.toFixed(2) },
      markLine: {
        silent: true, symbol: 'none',
        data: [
          { yAxis: 70, lineStyle: { color: cc.red, type: 'dashed', width: 1 } },
          { yAxis: 30, lineStyle: { color: cc.green, type: 'dashed', width: 1 } }
        ]
      }
    });
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const opt = timeOption({
    legend: { textStyle: { color: cc.text, fontSize: 10 }, top: 0, right: 80 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: cc.muted, color: '#fff' }, lineStyle: { type: 'dashed', color: cc.muted } },
      backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1, padding: 12,
      textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' }
    },
    graphic: [
      {
        type: 'text', left: 'center', top: 'center', z: -1,
        style: { text: data.symbol, fontSize: 100, fontWeight: 'bold', fill: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)' }
      }
    ]
  });

  opt.grid = grids;
  opt.xAxis = xAxes;
  opt.yAxis = yAxes;
  opt.dataZoom = [
    { type: 'inside', xAxisIndex: grids.map((_, i) => i) },
    { type: 'slider', xAxisIndex: grids.map((_, i) => i), height: 20, bottom: 4, borderColor: cc.border,
      backgroundColor: 'transparent', fillerColor: isUp ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
      handleStyle: { color: lineColor }, textStyle: { color: cc.muted, fontSize: 9 } }
  ];
  opt.series = series;

  makeChart(id, opt);
}

/* ----------------------------------------------- ratios PE / PS / PB */
function chartRatio(id, pairs, stats, color, name) {
  if (!pairs || pairs.length < 6) return hideCard(id);
  showCard(id);
  const cc = getChartColors();
  const lastVal = pairs && pairs.length ? pairs[pairs.length - 1][1] : null;
  const markLineData = [];
  if (stats && stats.median != null) {
    markLineData.push({ yAxis: stats.median, lineStyle: { color: cc.gold, type: 'dashed', width: 1.5 }, label: { color: cc.gold, fontSize: 10, position: 'insideEndTop', formatter: `Mediana ${stats.median}x` } });
  }
  if (lastVal != null) {
    markLineData.push({ yAxis: lastVal, lineStyle: { color: cc.green, type: 'solid', width: 1.5 }, label: { color: cc.green, fontSize: 10, position: 'insideEndBottom', formatter: `Hoy ${lastVal.toFixed(1)}x` } });
  }
  const markLine = markLineData.length ? { silent: true, symbol: 'none', data: markLineData } : undefined;
  const markArea = stats && stats.p25 != null ? {
    silent: true,
    itemStyle: { color: cc.grid },
    data: [[{ yAxis: stats.p25 }, { yAxis: stats.p75 }]],
  } : undefined;
  makeChart(id, timeOption({
    series: [{
      type: 'line', data: pairs, showSymbol: false, name,
      lineStyle: { color, width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '30' }, { offset: 1, color: color + '02' },
      ]) },
      markLine, markArea,
      tooltip: { valueFormatter: v => fmtRatio(v, 1) },
    }],
  }));
}


/* --------------------------------------------- fundamentales anuales */
function chartIncome(data) {
  const a = data.annuals.filter(x => x.revenue != null);
  if (a.length < 2) return hideCard('ch-income');
  showCard('ch-income');
  const years = a.map(x => x.year);
  const cur = data.profile.currency;
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-income', yearsOption(years, {
    yAxis: [
      Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }),
      Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    ],
    series: [
      { type: 'bar', name: 'Ingresos', data: a.map(x => x.revenue), itemStyle: { color: cc.blue, borderRadius: [4,4,0,0] }, barMaxWidth: 34, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'bar', name: 'Utilidad neta', data: a.map(x => x.netIncome), itemStyle: { color: cc.green, borderRadius: [4,4,0,0] }, barMaxWidth: 34, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'Margen neto', yAxisIndex: 1, data: a.map(x => x.netMargin != null ? +x.netMargin.toFixed(1) : null), lineStyle: { color: cc.gold, width: 2 }, itemStyle: { color: cc.gold }, tooltip: { valueFormatter: v => fmtPct(v) } },
    ],
  }));
}

function chartMargins(data) {
  const a = data.annuals.filter(x => x.netMargin != null || x.grossMargin != null);
  if (a.length < 2) return hideCard('ch-margins');
  showCard('ch-margins');
  const years = a.map(x => x.year);
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  const line = (name, key, color) => ({
    type: 'line', name, data: a.map(x => x[key] != null ? +x[key].toFixed(1) : null),
    lineStyle: { color, width: 2 }, itemStyle: { color }, symbolSize: 6,
    tooltip: { valueFormatter: v => fmtPct(v) },
  });
  makeChart('ch-margins', yearsOption(years, {
    yAxis: Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    series: [
      line('Margen bruto', 'grossMargin', cc.cyan),
      line('Margen operativo', 'opMargin', cc.violet),
      line('Margen neto', 'netMargin', cc.gold),
    ],
  }));
}

function chartFcf(data) {
  const a = data.annuals.filter(x => x.fcf != null);
  if (a.length < 2) return hideCard('ch-fcf');
  showCard('ch-fcf');
  const cur = data.profile.currency;
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-fcf', yearsOption(a.map(x => x.year), {
    yAxis: [
      Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }),
      Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    ],
    series: [
      { type: 'bar', name: 'FCF', data: a.map(x => x.fcf), barMaxWidth: 40,
        itemStyle: { color: p => p.value >= 0 ? cc.green : cc.red, borderRadius: [4,4,0,0] },
        tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'Margen FCF', yAxisIndex: 1, data: a.map(x => x.fcfMargin != null ? +x.fcfMargin.toFixed(1) : null),
        lineStyle: { color: cc.gold, width: 2 }, itemStyle: { color: cc.gold }, tooltip: { valueFormatter: v => fmtPct(v) } },
    ],
  }));
}

function chartReturns(data) {
  const a = data.annuals.filter(x => x.roe != null || x.roic != null);
  if (a.length < 2) return hideCard('ch-returns');
  showCard('ch-returns');
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-returns', yearsOption(a.map(x => x.year), {
    yAxis: Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    series: [
      { type: 'bar', name: 'ROE', data: a.map(x => x.roe != null ? +x.roe.toFixed(1) : null), itemStyle: { color: cc.blue, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtPct(v) } },
      { type: 'bar', name: 'ROIC', data: a.map(x => x.roic != null ? +x.roic.toFixed(1) : null), itemStyle: { color: cc.violet, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtPct(v) },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: cc.gold, type: 'dashed' }, label: { color: cc.gold, formatter: '15%' }, data: [{ yAxis: 15 }] } },
    ],
  }));
}

function chartDebt(data) {
  const a = data.annuals.filter(x => x.totalDebt != null || x.cash != null);
  if (a.length < 2) return hideCard('ch-debt');
  showCard('ch-debt');
  const cur = data.profile.currency;
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-debt', yearsOption(a.map(x => x.year), {
    yAxis: [
      Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }),
      Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}x' } }),
    ],
    series: [
      { type: 'bar', name: 'Deuda total', data: a.map(x => x.totalDebt), itemStyle: { color: cc.red, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'bar', name: 'Caja', data: a.map(x => x.cash), itemStyle: { color: cc.green, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'Deuda/Patrimonio', yAxisIndex: 1, data: a.map(x => x.debtToEquity != null ? +x.debtToEquity.toFixed(2) : null),
        lineStyle: { color: cc.amber, width: 2 }, itemStyle: { color: cc.amber }, tooltip: { valueFormatter: v => fmtRatio(v, 2) } },
    ],
  }));
}

function chartShares(data) {
  const pts = data.history.shares;
  if (!pts || pts.length < 4) return hideCard('ch-shares');
  showCard('ch-shares');
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-shares', timeOption({
    yAxis: Object.assign({ type: 'value', scale: true }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }),
    series: [{
      type: 'line', data: pts, showSymbol: false, name: 'Acciones', step: 'end',
      lineStyle: { color: cc.cyan, width: 2 },
      areaStyle: { color: 'rgba(6,182,212,0.10)' },
      tooltip: { valueFormatter: v => fmtBig(v) },
    }],
  }));
}

function chartEps(data) {
  const a = data.annuals.filter(x => x.eps != null);
  if (a.length < 2) return hideCard('ch-eps');
  showCard('ch-eps');
  const cc = getChartColors();
  makeChart('ch-eps', yearsOption(a.map(x => x.year), {
    series: [{
      type: 'bar', name: 'EPS diluido', data: a.map(x => +x.eps.toFixed(2)), barMaxWidth: 40,
      itemStyle: { color: p => p.value >= 0 ? cc.gold : cc.red, borderRadius: [4,4,0,0] },
      label: { show: true, position: 'top', color: cc.muted, fontSize: 11, formatter: p => fmtNum(p.value, 2) },
      tooltip: { valueFormatter: v => fmtNum(v, 2) },
    }],
  }));
}

function chartDividends(data) {
  const d = data.history.dividends;
  if (!d || d.length < 3) return hideCard('ch-divs');
  showCard('ch-divs');
  const cc = getChartColors();
  const curYear = new Date().getFullYear();
  makeChart('ch-divs', yearsOption(d.map(x => x[0]), {
    series: [{
      type: 'bar', name: 'Dividendo por acción', barMaxWidth: 26,
      data: d.map(x => ({ value: +x[1].toFixed(3), itemStyle: x[0] === curYear ? { color: 'rgba(34,197,94,0.35)', borderRadius: [4,4,0,0] } : { color: cc.green, borderRadius: [4,4,0,0] } })),
      tooltip: { valueFormatter: v => fmtNum(v, 3) },
    }],
  }));
}

/* ------------------------------------------- historial de margen seg. */
function chartMos(data) {
  const pts = (data.history.mos || []).map(p => [p[0], p[1]]);
  if (pts.length < 2) return hideCard('ch-mos');
  showCard('ch-mos');
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);
  makeChart('ch-mos', timeOption({
    yAxis: Object.assign({ type: 'value', scale: true }, ba,
      { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    series: [{
      type: 'line', data: pts, name: 'Margen de seguridad', symbolSize: 7,
      lineStyle: { color: cc.gold, width: 2 }, itemStyle: { color: cc.gold },
      areaStyle: { color: 'rgba(212,175,55,0.08)' },
      markLine: {
        silent: true, symbol: 'none',
        data: [
          { yAxis: 0, lineStyle: { color: cc.muted, type: 'dashed' }, label: { color: cc.muted, formatter: 'precio justo' } },
          { yAxis: 25, lineStyle: { color: cc.green, type: 'dashed' }, label: { color: cc.green, formatter: 'zona de compra' } },
        ],
      },
      tooltip: { valueFormatter: v => fmtPct(v, 1, true) },
    }],
  }));
}

/* -------------------------------------------------- gauge de margen */
function renderGauge(mos) {
  const val = mos == null ? 0 : Math.max(-50, Math.min(100, mos));
  makeChart("gauge-mos", {
    series: [{
      type: "gauge", startAngle: 200, endAngle: -20,
      min: -50, max: 100, radius: "105%", center: ["50%", "72%"],
      axisLine: { lineStyle: { width: 16, color: [
        [0.333, C.red], [0.5, C.amber], [0.667, "#a3b81f"], [1, C.green],
      ] } },
      pointer: { length: "62%", width: 5, itemStyle: { color: C.text } },
      axisTick: { show: false }, splitLine: { show: false },
      axisLabel: { color: C.muted, fontSize: 10, distance: -46, formatter: v => (v === -50 || v === 0 || v === 50 || v === 100) ? v + "%" : "" },
      detail: {
        valueAnimation: true, offsetCenter: [0, "28%"],
        formatter: mos == null ? "—" : (mos > 0 ? "+" : "") + mos.toFixed(0) + "%",
        color: mos == null ? C.muted : (mos >= 25 ? C.green : mos >= 0 ? C.amber : C.red),
        fontSize: 26, fontWeight: 700, fontFamily: "Inter",
      },
      data: [{ value: val }],
    }],
  });
}

/* --------------------------------------------- heatmap del screener */
function mosColor(mos) {
  if (mos == null) return "#2a3348";
  const t = Math.max(-50, Math.min(60, mos));
  if (t >= 25) return "#15803d";
  if (t >= 10) return "#22c55e";
  if (t >= 0) return "#4d7c0f";
  if (t >= -15) return "#a16207";
  if (t >= -30) return "#c2410c";
  return "#b91c1c";
}

function chartEarningsSurprise(elemId, surprises) {
  if (!surprises || !surprises.length) return;
  const dates = surprises.map(s => s.date.substring(0,7)); // YYYY-MM
  const est = surprises.map(s => s.estimate);
  const rep = surprises.map(s => s.reported);
  
  const cc = getChartColors();
  
  makeChart(elemId, {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: cc.bg,
      borderColor: cc.border,
      textStyle: { color: cc.text, fontSize: 12 },
      padding: [12, 16],
      borderRadius: 8,
      formatter: (params) => {
        let tip = `<div style="font-weight:700;margin-bottom:4px;color:${cc.text}">${params[0].axisValue}</div>`;
        let e = null, r = null;
        params.forEach(p => {
          tip += `<div style="display:flex;justify-content:space-between;gap:12px;margin-bottom:2px;">
            <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}</span>
            <span style="font-family:var(--font-mono);font-weight:600;">$${p.value != null ? p.value.toFixed(2) : '—'}</span>
          </div>`;
          if (p.seriesIndex === 0) e = p.value;
          if (p.seriesIndex === 1) r = p.value;
        });
        if (e != null && r != null && e !== 0) {
          const diff = ((r - e) / Math.abs(e)) * 100;
          const color = diff >= 0 ? 'var(--green)' : 'var(--red)';
          const icon = diff >= 0 ? '▲' : '▼';
          tip += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid ${cc.border};font-weight:600;color:${color}">${icon} Sorpresa: ${diff > 0 ? '+' : ''}${diff.toFixed(1)}%</div>`;
        }
        return tip;
      }
    },
    legend: {
      data: ['Estimado', 'Reportado'],
      textStyle: { color: cc.muted, fontSize: 11 },
      bottom: 0,
      icon: 'circle',
      itemWidth: 8
    },
    grid: { left: 45, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: cc.muted, fontSize: 10, margin: 12 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: cc.grid, type: 'dashed' } },
      axisLabel: {
        color: cc.muted,
        fontSize: 10,
        formatter: (v) => '$' + v
      }
    },
    series: [
      {
        name: 'Estimado',
        type: 'bar',
        data: est,
        itemStyle: { color: 'rgba(59, 130, 246, 0.3)', borderRadius: [4, 4, 0, 0] },
        barWidth: '25%',
        barGap: '15%'
      },
      {
        name: 'Reportado',
        type: 'bar',
        data: rep,
        itemStyle: {
          color: (p) => {
            const e = est[p.dataIndex];
            if (e == null) return '#10b981';
            return p.value >= e ? '#10b981' : '#ef4444';
          },
          borderRadius: [4, 4, 0, 0]
        },
        barWidth: '25%'
      }
    ]
  });
}

function renderHeatmap(rows) {
  const bySector = {};
  for (const r of rows) {
    if (!r.marketCap) continue;
    (bySector[r.sector || "Otros"] = bySector[r.sector || "Otros"] || []).push(r);
  }
  const data = Object.entries(bySector).map(([sector, list]) => ({
    name: sector,
    children: list.map(r => ({
      name: r.symbol,
      value: r.marketCap,
      mos: r.mos,
      itemStyle: { color: mosColor(r.mos) },
      label: {
        formatter: r.mos != null
          ? `{sym|${r.symbol}}\n{mos|${r.mos > 0 ? "+" : ""}${Math.round(r.mos)}%}`
          : `{sym|${r.symbol}}`,
        rich: {
          sym: { fontSize: 13, fontWeight: 700, color: "#fff" },
          mos: { fontSize: 11, color: "rgba(255,255,255,0.85)" },
        },
      },
    })),
  }));

  makeChart("screener-heatmap", {
    tooltip: {
      backgroundColor: "#0f1522", borderColor: C.border, textStyle: { color: C.text, fontSize: 12 },
      formatter: p => {
        if (!p.data || p.data.children) return p.name;
        return `<b>${p.name}</b><br>Capitalización: ${fmtBig(p.value, "USD")}<br>` +
               `Margen de seguridad: <b>${p.data.mos != null ? fmtPct(p.data.mos, 0, true) : "—"}</b>`;
      },
    },
    series: [{
      type: "treemap", data,
      width: "100%", height: "94%", top: 0,
      roam: false, nodeClick: false, breadcrumb: { show: false },
      upperLabel: { show: true, height: 22, color: C.muted, fontSize: 11.5,
        backgroundColor: "transparent", fontWeight: 600 },
      itemStyle: { borderColor: "#0b0f1a", borderWidth: 2, gapWidth: 2 },
      levels: [
        { itemStyle: { borderColor: "#0b0f1a", borderWidth: 3, gapWidth: 3 } },
        { itemStyle: { borderWidth: 1, gapWidth: 1 } },
      ],
    }],
  });
  charts["screener-heatmap"].off("click");
  charts["screener-heatmap"].on("click", p => {
    if (p.data && !p.data.children) go(p.name);
  });
}

/* ------------------------------------------------- descarga como PNG */
function addChartDownloadButtons() {
  document.querySelectorAll('#view-analisis .chart-card').forEach(card => {
    const h3 = card.querySelector('h3');
    const div = card.querySelector('.chart');
    if (!h3 || !div || h3.querySelector('.btn-dl')) return;
    const btn = document.createElement('button');
    btn.className = 'btn-dl';
    btn.title = 'Descargar gráfico como PNG';
    btn.textContent = '⤓';
    btn.onclick = () => {
      const ch = charts[div.id];
      if (!ch) return;
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      const bg = dark ? '#090d16' : '#ffffff';
      const a = document.createElement('a');
      a.href = ch.getDataURL({ pixelRatio: 2, backgroundColor: bg });
      const sym = (window.state && state.symbol) || 'chart';
      a.download = `${sym}_${div.id.replace('ch-', '')}.png`;
      a.click();
    };
    h3.appendChild(btn);
  });
}


/* ------------------------------------------------ comparador overlay */
function renderCompareCharts(symbols, payloads, colors) {
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);

  // retorno total normalizado (base 100 desde la fecha común más antigua)
  const priceSeries = symbols.map((s, i) => {
    const pts = payloads[s].history.price;
    return { s, i, pts };
  }).filter(x => x.pts && x.pts.length > 10);

  if (priceSeries.length) {
    const commonStart = Math.max(...priceSeries.map(x => x.pts[0][0]));
    makeChart('cmp-price', timeOption({
      legend: { textStyle: { color: cc.muted, fontSize: 11 }, top: 0 },
      grid: { left: 56, right: 18, top: 34, bottom: 42 },
      yAxis: Object.assign({ type: 'value', scale: true }, ba,
        { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}' } }),
      series: priceSeries.map(({ s, i, pts }) => {
        const from = pts.filter(p => p[0] >= commonStart);
        const base = from.length ? from[0][1] : 1;
        return {
          type: 'line', name: s, showSymbol: false,
          data: from.map(p => [p[0], +(p[1] / base * 100).toFixed(1)]),
          lineStyle: { color: colors[i], width: 2 }, itemStyle: { color: colors[i] },
          tooltip: { valueFormatter: v => fmtNum(v, 0) },
        };
      }),
    }));
  }

  const mkOverlay = (id, key, fmt) => {
    const series = symbols.map((s, i) => {
      const pts = payloads[s].history[key];
      if (!pts || pts.length < 4) return null;
      return {
        type: 'line', name: s, showSymbol: false, data: pts,
        lineStyle: { color: colors[i], width: 2 }, itemStyle: { color: colors[i] },
        tooltip: { valueFormatter: fmt },
      };
    }).filter(Boolean);
    if (!series.length) return hideCard(id);
    showCard(id);
    makeChart(id, timeOption({
      legend: { textStyle: { color: cc.muted, fontSize: 11 }, top: 0 },
      grid: { left: 56, right: 18, top: 34, bottom: 42 },
      series,
    }));
  };
  mkOverlay('cmp-pe', 'peTtm', v => fmtRatio(v, 1));

  // margen neto anual (categorías = años)
  const marginSeries = symbols.map((s, i) => {
    const a = payloads[s].annuals.filter(x => x.netMargin != null);
    if (a.length < 2) return null;
    return {
      type: 'line', name: s, data: a.map(x => [String(x.year), +x.netMargin.toFixed(1)]),
      lineStyle: { color: colors[i], width: 2 }, itemStyle: { color: colors[i] }, symbolSize: 5,
      tooltip: { valueFormatter: v => fmtPct(v) },
    };
  }).filter(Boolean);
  if (marginSeries.length) {
    showCard('cmp-margins');
    const years = [...new Set(marginSeries.flatMap(s => s.data.map(d => d[0])))].sort();
    makeChart('cmp-margins', yearsOption(years, {
      yAxis: Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
      series: marginSeries,
    }));
  } else {
    hideCard('cmp-margins');
  }
}

/* ------------------------------------------------------- orquestador */
function renderAllCharts(data) {
  const cc = getChartColors();
  chartPrice(data);
  chartRatio('ch-pe',  data.history.peTtm,  data.history.peStats,  cc.blue,   'PE (TTM)');
  chartRatio('ch-ps',  data.history.psTtm,  data.history.psStats,  cc.violet, 'P/Ventas (TTM)');
  chartRatio('ch-pb',  data.history.pbTtm,  data.history.pbStats,  cc.cyan,   'P/Valor libro');
  chartRatio('ch-pcf', data.history.pcfTtm, data.history.pcfStats, cc.amber,  'P/Cash Flow');
  chartIncome(data);
  chartMargins(data);
  chartFcf(data);
  chartReturns(data);
  chartDebt(data);
  chartShares(data);
  chartEps(data);
  chartDividends(data);
  chartMos(data);

  // Badge PE fuera de banda histórica
  _renderPeBandBadge(data.history.peStats, data.current.pe);
}

function _renderPeBandBadge(peStats, peCurrent) {
  const headEl = document.querySelector('#ch-pe')?.closest('.chart-card')?.querySelector('h3');
  if (!headEl || !peStats || peCurrent == null) return;

  // Eliminar badge previo
  const prev = headEl.querySelector('.pe-band-badge');
  if (prev) prev.remove();

  if (peCurrent > 150) return; // PE no fiable, no mostrar

  const { p25, p75, median } = peStats;
  let label, bg, fg;
  if (p25 != null && peCurrent < p25) {
    label = `Barato vs historia (< p25: ${p25}x)`;
    bg = 'rgba(16,185,129,0.15)'; fg = '#065f46';
  } else if (p75 != null && peCurrent > p75) {
    label = `Caro vs historia (> p75: ${p75}x)`;
    bg = 'rgba(239,68,68,0.15)'; fg = '#991b1b';
  } else if (median != null) {
    label = `Dentro de banda histórica`;
    bg = 'rgba(59,130,246,0.12)'; fg = '#1e40af';
  }
  if (!label) return;

  const badge = document.createElement('span');
  badge.className = 'pe-band-badge';
  badge.style.cssText = `display:inline-block; margin-left:8px; padding:2px 7px; border-radius:5px; font-size:10.5px; font-weight:700; background:${bg}; color:${fg};`;
  badge.textContent = label;
  headEl.appendChild(badge);
}

