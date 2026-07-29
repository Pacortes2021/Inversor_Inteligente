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
const _origSetTheme = window.setTheme;
window.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    const origOnClick = btn.onclick;
    btn.onclick = (e) => {
      if (origOnClick) origOnClick.call(btn, e);
      /* Pequeño delay para que el atributo data-theme cambie antes de re-renderizar */
      setTimeout(() => {
        if (window.state && window.state.data) {
          const activePane = document.querySelector('.a-tab.active');
          const pane = activePane ? activePane.dataset.pane : null;
          if (pane === 'financials') renderAllCharts(window.state.data);
          else if (pane === 'ratios') renderRatiosCharts(window.state.data, window.currentMultiplesRange || 'all');
          else if (pane === 'summary') chartPriceSummary(window.state.data);
        }
      }, 80);
    };
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
      borderWidth: 1, borderRadius: 6,
      padding: [8, 12],
      textStyle: { color: cc.text, fontSize: 11, fontFamily: 'Inter, sans-serif' },
      axisPointer: { type: 'cross', label: { backgroundColor: '#64748b' } },
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
      textStyle: { color: cc.text, fontSize: 11 },
    },
    legend: { textStyle: { color: cc.muted, fontSize: 10 }, top: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 6 },
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

function chartPrice(data, id = 'ch-price', customPts = null) {
  const pts = customPts || data.history.price;
  if (!pts || pts.length < 5) return hideCard(id);
  showCard(id);
  const cur = data.profile.currency;
  const cc = getChartColors();
  const ba = baseAxisStyle(cc);

  const isArea = priceView.type === 'area';
  const series = [{
    type: 'line', data: pts, showSymbol: false, name: 'Precio',
    lineStyle: { color: cc.gold, width: 2 },
    areaStyle: isArea ? { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: 'rgba(217,119,6,0.22)' }, { offset: 1, color: 'rgba(217,119,6,0.01)' },
    ]) } : undefined,
    tooltip: { valueFormatter: v => fmtPrice(v, cur) },
    /* markLine: precio actual como referencia horizontal */
    markLine: {
      silent: true, symbol: 'none',
      data: [{ yAxis: data.quote.price, lineStyle: { color: cc.gold, type: 'dashed', width: 1 },
        label: { color: cc.gold, fontSize: 10, position: 'insideEndTop', formatter: `Hoy ${fmtPrice(data.quote.price, cur)}` } }],
    },
  }];

  if (priceView.sma && pts.length > 50) {
    series.push({ type: 'line', name: 'SMA 50', data: sma(pts, 50), showSymbol: false,
      lineStyle: { color: cc.cyan, width: 1.3 }, itemStyle: { color: cc.cyan },
      tooltip: { valueFormatter: v => fmtPrice(v, cur) } });
    series.push({ type: 'line', name: 'SMA 200', data: sma(pts, 200), showSymbol: false,
      lineStyle: { color: cc.violet, width: 1.3 }, itemStyle: { color: cc.violet },
      tooltip: { valueFormatter: v => fmtPrice(v, cur) } });
  }

  makeChart(id, timeOption({
    legend: priceView.sma ? { textStyle: { color: cc.text, fontSize: 10 }, top: 0 } : undefined,
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 16, bottom: 4, borderColor: cc.border,
        backgroundColor: 'transparent', fillerColor: 'rgba(217,119,6,0.08)',
        handleStyle: { color: cc.gold }, textStyle: { color: cc.muted, fontSize: 9 } },
    ],
    grid: { left: 45, right: 12, top: 20, bottom: 48 },
    yAxis: Object.assign(
      priceView.log ? { type: 'log', logBase: 10, min: 'dataMin' } : { type: 'value', scale: true },
      ba,
      { axisLabel: { color: cc.muted, fontSize: 10, formatter: v => fmtBig(v, cur) } }),
    series,
  }));
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

