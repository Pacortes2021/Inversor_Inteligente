/* Gráficos ECharts con tema propio — El Inversor Inteligente */

import { fmtBig, fmtPrice, fmtPct, fmtRatio, fmtNum } from "./format.js";
import { state } from "./state.js";

/** Colores que se adaptan al tema claro/oscuro en tiempo de ejecución */
export function getChartColors() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    gold: '#e8a33d',
    green: dark ? '#1ca58d' : '#0f9c8a',
    red: dark ? '#f4555c' : '#e54850',
    blue: dark ? '#4f8df7' : '#2f6be7',
    cyan: dark ? '#2fb7e6' : '#1478c9',
    violet: dark ? '#9d8cfb' : '#7c5cdb',
    amber: '#e8a33d',
    text: dark ? '#e6ebf2' : '#1c2430',
    muted: dark ? '#8996a9' : '#5e6b7d',
    border: dark ? 'rgba(148,163,184,0.16)' : 'rgba(15,23,42,0.14)',
    grid: dark ? 'rgba(148,163,184,0.13)' : 'rgba(15,23,42,0.08)',
    panel: dark ? '#101720' : '#ffffff',
  };
}

/* Alias estático C mantenido para compat. con referencias en makeChart/hideCard */
export const C = {
  gold: '#d97706', green: '#10b981', red: '#ef4444', blue: '#3b82f6',
  cyan: '#0ea5e9', violet: '#8b5cf6', amber: '#d97706',
  text: '#1e293b', muted: '#64748b', border: '#e2e8f0', grid: '#f1f5f9',
};

export const charts = {};;

export function makeChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (charts[id]) charts[id].dispose();
  const ch = echarts.init(el, null, { renderer: 'canvas' });
  ch.setOption(option);
  charts[id] = ch;
  return ch;
}

window.addEventListener('resize', () => Object.values(charts).forEach(c => c.resize()));

export function hideCard(id) {
  const el = document.getElementById(id);
  if (el) {
    const card = el.closest('.chart-card') || el.closest('.card');
    if (card) card.classList.add('hidden');
  }
}
export function showCard(id) {
  const el = document.getElementById(id);
  if (el) {
    const card = el.closest('.chart-card') || el.closest('.card');
    if (card) card.classList.remove('hidden');
  }
}

/* ---------------------------------------------------------- base común */
export function baseAxisStyle(cc) {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: cc.muted, fontSize: 11, fontFamily: 'Inter, sans-serif' },
    splitLine: { lineStyle: { color: cc.grid, type: 'dashed', opacity: 0.4 } },
  };
}

/* Retro-compatibilidad: baseAxis legacy (usa colores estáticos) */
export const baseAxis = {
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { color: C.muted, fontSize: 11, fontFamily: 'Inter, sans-serif' },
  splitLine: { lineStyle: { color: C.grid, type: 'dashed', opacity: 0.4 } },
};

export function timeOption(extra) {
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

export function yearsOption(years, extra) {
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
export const priceView = { log: false, sma: false, trend: false, type: 'area' };

export function sma(pts, n) {
  const out = [];
  let sum = 0;
  for (let i = 0; i < pts.length; i++) {
    sum += pts[i][1];
    if (i >= n) sum -= pts[i - n][1];
    if (i >= n - 1) out.push([pts[i][0], +(sum / n).toFixed(2)]);
  }
  return out;
}

export function linreg(pts) {
  /* Regresión lineal de mínimos cuadrados sobre el precio: devuelve el valor
     de la recta en el primer y último punto y su retorno % en el período. */
  const n = pts.length;
  if (n < 3) return null;
  let sx = 0, sy = 0, sxy = 0, sxx = 0;
  for (let i = 0; i < n; i++) {
    sx += i; sy += pts[i][1]; sxy += i * pts[i][1]; sxx += i * i;
  }
  const den = n * sxx - sx * sx;
  if (den === 0) return null;
  const slope = (n * sxy - sx * sy) / den;
  const intercept = (sy - slope * sx) / n;
  const y0 = intercept, y1 = intercept + slope * (n - 1);
  return { y0, y1, pct: y0 > 0 ? (y1 / y0 - 1) * 100 : null };
}

export function calculateEMA(pts, period) {
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

export function calculateMACD(pts, shortP = 12, longP = 26, sigP = 9) {
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

export function calculateRSI(pts, period = 14) {
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

export function chartPrice(data, id = 'ch-price', customPts = null) {
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
  const fillStart = isUp ? `${cc.green}26` : `${cc.red}26`;
  const fillEnd   = isUp ? `${cc.green}00` : `${cc.red}00`;

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
    lineStyle: { color: lineColor, width: 1.5 },
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
      lineStyle: { color: '#9aa8bd', width: 1.3 }, itemStyle: { color: '#9aa8bd' },
      tooltip: { valueFormatter: v => fmtPrice(v, cur) } });
  }

  if (priceView.trend && pts.length > 10) {
    const tr = linreg(pts);
    if (tr) {
      const pct = tr.pct;
      const lbl = pct != null ? `Tendencia ${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%` : "Tendencia";
      series.push({
        type: 'line', name: 'Tendencia (regresión)', xAxisIndex: 0, yAxisIndex: 0,
        data: [
          [pts[0][0], tr.y0, { label: { show: false } }],
          [pts[pts.length - 1][0], tr.y1, {
            label: { show: true, position: 'end', color: cc.violet, fontSize: 10, fontWeight: 'bold',
                     padding: [3, 5], borderRadius: 3, backgroundColor: cc.panel, formatter: lbl },
          }],
        ],
        showSymbol: false,
        lineStyle: { color: cc.violet, width: 1.5, type: 'dashed' },
        itemStyle: { color: cc.violet },
        tooltip: { valueFormatter: v => fmtPrice(v, cur) },
      });
    }
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

  const opt = timeOption({
    legend: { textStyle: { color: cc.text, fontSize: 10 }, top: 0, right: 80 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: cc.muted, color: '#fff' }, lineStyle: { type: 'dashed', color: cc.muted } },
      backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1, padding: 10,
      textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' }
    }
  });

  opt.grid = grids;
  opt.xAxis = xAxes;
  opt.yAxis = yAxes;
  opt.dataZoom = [
    { type: 'inside', xAxisIndex: grids.map((_, i) => i) },
    { type: 'slider', xAxisIndex: grids.map((_, i) => i), height: 22, bottom: 5,
      borderColor: 'transparent', backgroundColor: 'transparent', showDetail: false,
      fillerColor: isUp ? `${cc.green}1a` : `${cc.red}1a`,
      handleStyle: { color: cc.muted }, handleSize: '80%',
      textStyle: { color: cc.muted, fontSize: 9 } }
  ];
  opt.series = series;

  makeChart(id, opt);
}

/* ----------------------------------------------- ratios PE / PS / PB */
export function chartRatio(id, pairs, stats, color, name) {
  if (!pairs || pairs.length < 6) return hideCard(id);
  showCard(id);
  const cc = getChartColors();
  const lastVal = pairs && pairs.length ? pairs[pairs.length - 1][1] : null;
  const markLineData = [];

  const markArea = stats && stats.p25 != null ? {
    silent: true,
    itemStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '16' }, { offset: 1, color: color + '05' },
      ]),
    },
    data: [[{ yAxis: stats.p25 }, { yAxis: stats.p75 }]],
  } : undefined;

  if (stats && stats.p25 != null) {
    markLineData.push({ yAxis: stats.p25, lineStyle: { color: cc.muted, type: 'dotted', width: 1, opacity: 0.55 }, label: { show: false } });
  }
  if (stats && stats.p75 != null) {
    markLineData.push({ yAxis: stats.p75, lineStyle: { color: cc.muted, type: 'dotted', width: 1, opacity: 0.55 }, label: { show: false } });
  }
  if (stats && stats.median != null) {
    markLineData.push({
      yAxis: stats.median,
      lineStyle: { color: cc.gold, type: 'dashed', width: 1.5 },
      label: { color: cc.gold, fontSize: 10.5, fontWeight: 700, position: 'insideEndTop', formatter: `Mediana ${stats.median}x`, fontFamily: 'Inter' },
    });
  }
  if (lastVal != null) {
    markLineData.push({
      yAxis: lastVal,
      lineStyle: { color: cc.green, type: 'solid', width: 1.8 },
      label: { color: cc.green, fontSize: 10.5, fontWeight: 700, position: 'insideEndBottom', formatter: `Hoy ${lastVal.toFixed(1)}x` },
    });
  }
  const markLine = markLineData.length ? { silent: true, symbol: 'none', data: markLineData } : undefined;

  // Posición del valor actual dentro de la distribución histórica
  const validPts = pairs.filter(p => p[1] != null);
  const pctile = lastVal != null && validPts.length
    ? Math.round(validPts.filter(p => p[1] <= lastVal).length / validPts.length * 100)
    : null;
  const vsMed = lastVal != null && stats && stats.median != null
    ? ((lastVal - stats.median) / stats.median) * 100
    : null;

  makeChart(id, timeOption({
    grid: { left: 48, right: 22, top: 26, bottom: 34 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: cc.panel, borderColor: cc.border,
      borderWidth: 1, borderRadius: 8, padding: [10, 14],
      textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' },
      axisPointer: { type: 'line', lineStyle: { color: cc.muted, type: 'dashed', opacity: 0.5 } },
      formatter: (params) => {
        const p = params && params[0];
        if (!p || !p.value || p.value[1] == null) return '';
        const t = p.value[0], v = p.value[1];
        const dateStr = new Date(t).toLocaleDateString('es-CL', { year: 'numeric', month: 'short' });
        let vs = '';
        if (stats && stats.median != null) {
          const delta = (v - stats.median) / stats.median * 100;
          const c = delta > 0 ? cc.red : cc.green;
          vs = `<div style="margin-top:6px;padding-top:6px;border-top:1px solid ${cc.border};display:flex;justify-content:space-between;gap:16px;align-items:baseline">
            <span style="color:${cc.muted}">vs mediana (${stats.median}x)</span>
            <b style="color:${c}">${delta >= 0 ? '+' : ''}${delta.toFixed(1)}%</b></div>`;
        }
        return `<div style="font-weight:700;color:${cc.text};margin-bottom:4px">${name} · ${dateStr}</div>
          <div style="display:flex;justify-content:space-between;gap:16px;align-items:baseline">
            <span style="color:${cc.muted}">Valor</span>
            <b style="font-family:'Inter';font-size:14px;color:${color}">${v.toFixed(1)}x</b></div>${vs}`;
      },
    },
    yAxis: Object.assign({ type: 'value', scale: true }, baseAxisStyle(cc), {
      axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}x' },
    }),
    series: [{
      type: 'line', data: pairs, showSymbol: false, name, smooth: 0.3,
      lineStyle: { color, width: 2.5, shadowColor: color + '55', shadowBlur: 10, shadowOffsetY: 5 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '3c' }, { offset: 1, color: color + '00' },
      ]) },
      emphasis: { focus: 'series', lineStyle: { width: 3.5 } },
      endLabel: {
        show: lastVal != null,
        color, fontSize: 12, fontWeight: 800, fontFamily: 'Inter',
        formatter: lastVal != null ? `${lastVal.toFixed(1)}x` : '',
      },
      markLine, markArea,
      tooltip: { valueFormatter: v => fmtRatio(v, 1) },
    }],
  }));

  // ── Chips de estadísticas bajo el gráfico ──
  const statEl = document.getElementById('stat-' + id.replace('ch-', ''));
  if (statEl) {
    const chips = [];
    if (stats && stats.median != null) chips.push([cc.gold, `Mediana <b>${stats.median}x</b>`]);
    if (stats && stats.p25 != null) chips.push([cc.muted, `p25 <b>${stats.p25}x</b>`]);
    if (stats && stats.p75 != null) chips.push([cc.muted, `p75 <b>${stats.p75}x</b>`]);
    if (lastVal != null) {
      const pos = vsMed == null ? cc.muted : (vsMed > 15 ? cc.red : vsMed < -15 ? cc.green : cc.amber);
      chips.push([pos, `Hoy <b>${lastVal.toFixed(1)}x</b>`]);
    }
    if (pctile != null) chips.push([cc.blue, `Percentil <b>P${pctile}</b>`]);
    statEl.innerHTML = chips.map(([c, html]) =>
      `<span class="stat-chip"><span class="dot" style="background:${c}"></span>${html}</span>`).join('');
  }
}


/* --------------------------------------------- fundamentales anuales */
export function chartIncome(data) {
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

export function chartMargins(data) {
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

export function chartFcf(data) {
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

export function chartReturns(data) {
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

export function chartDebt(data) {
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

export function chartShares(data) {
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

export function chartEps(data) {
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

export function chartDividends(data) {
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
export function chartMos(data) {
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
export function renderGauge(mos) {
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
export function mosColor(mos) {
  if (mos == null) return "#2a3348";
  const t = Math.max(-50, Math.min(60, mos));
  if (t >= 25) return "#15803d";
  if (t >= 10) return "#22c55e";
  if (t >= 0) return "#4d7c0f";
  if (t >= -15) return "#a16207";
  if (t >= -30) return "#c2410c";
  return "#b91c1c";
}

export function chartEarningsSurprise(elemId, surprises) {
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

export function renderHeatmap(rows, onOpen) {
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
    if (p.data && !p.data.children && onOpen) onOpen(p.name);
  });
}

/* --------------------------------------- overlay precio + múltiplos */
export function renderPriceOverlay(data) {
  const el = document.getElementById('ch-overlay');
  const chipsEl = document.getElementById('overlay-chips');
  const togglesEl = document.getElementById('overlay-toggles');
  const timeEl = document.getElementById('overlay-time');
  const freqEl = document.getElementById('overlay-freq');
  if (!el || !chipsEl || !togglesEl) return;
  const cc = getChartColors();
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const PRICE_C = isDark ? '#dfe5ee' : '#232c3b';
  const hist = (data && data.history) || {};
  const pricePts = Array.isArray(hist.price) ? hist.price.filter(p => p && p[1] != null) : [];
  if (pricePts.length < 30) {
    el.innerHTML = `<p class="muted" style="padding:60px 20px;text-align:center;font-size:13px">Sin suficiente historial de precio para el overlay de ${(state && state.symbol) || "este símbolo"}.</p>`;
    chipsEl.innerHTML = '';
    togglesEl.innerHTML = '';
    return;
  }

  const OVERLAYS = [
    { key: 'peTtm',  label: 'PE',            color: '#4f8df7', fmt: v => fmtRatio(v, 1) },
    { key: 'psTtm',  label: 'PS',            color: '#9d8cfb', fmt: v => fmtRatio(v, 2) },
    { key: 'pbTtm',  label: 'PB',            color: '#2fb7e6', fmt: v => fmtRatio(v, 2) },
    { key: 'pcfTtm', label: 'P/CF',          color: '#f4555c', fmt: v => fmtRatio(v, 1) },
    { key: 'epsTtm', label: 'EPS TTM',       color: '#1ca58d', fmt: v => fmtNum(v, 2) },
    { key: 'revTtm', label: 'Revenue TTM',   color: '#e8a33d', fmt: v => fmtBig(v) },
    { key: 'netMarginTtm', label: 'Margen TTM', color: '#ec4899', fmt: v => fmtPct(v, 1) },
    { key: 'sma50',  label: 'SMA 50',        color: '#94a3b8', fmt: v => fmtNum(v, 2) },
    { key: 'sma200', label: 'SMA 200',       color: '#64748b', fmt: v => fmtNum(v, 2) },
  ];

  let normalized = false;
  let logScale = false;
  let pRange = '1y';
  let pFreq = 'D';

  const src = { price: pricePts };
  const buck = (pairs, freq) => {
    if (!freq || freq === 'D') return pairs;
    const keyed = new Map();
    for (const [ts, v] of pairs) {
      const d = new Date(ts);
      let kt;
      if (freq === 'W') {
        const base = new Date(d);
        base.setDate(d.getDate() - ((d.getDay() + 6) % 7));
        base.setHours(0, 0, 0, 0);
        kt = base.getTime();
      } else {
        kt = new Date(d.getFullYear(), d.getMonth(), 1).getTime();
      }
      keyed.set(kt, v);
    }
    return [...keyed.entries()].sort((a, b) => a[0] - b[0]);
  };
  const priceFull = buck(pricePts, pFreq);
  for (const o of OVERLAYS) {
    const raw = hist[o.key] || [];
    src[o.key] = buck(raw.filter(p => p && p[1] != null), pFreq === 'D' ? null : pFreq);
  }
  src.sma50 = sma(priceFull, 50);
  src.sma200 = sma(priceFull, 200);

  const FMT = {};
  for (const o of OVERLAYS) FMT[o.label] = o.fmt;
  const fmtByName = name => FMT[name] || (name === 'Precio' ? (v => fmtNum(v, 2)) : (v => v != null ? v : '—'));
  const keyOf = label => (OVERLAYS.find(o => o.label === label) || {}).key || label;

  const active = new Set(['peTtm']);

  const RANGES = [
    { key: 'mtd', label: 'MTD' }, { key: '1m', label: '1M' }, { key: 'qtd', label: 'QTD' },
    { key: '3m', label: '3M' }, { key: '6m', label: '6M' }, { key: 'ytd', label: 'YTD' },
    { key: '1y', label: '1Y' }, { key: '3y', label: '3Y' }, { key: '5y', label: '5Y' },
    { key: '10y', label: '10Y' }, { key: '20y', label: '20Y' }, { key: 'all', label: 'TODOS' },
  ];

  function windowMin() {
    const last = priceFull[priceFull.length - 1][0];
    const day = 86400000;
    const days = { '1m': 31, '3m': 92, '6m': 183, '1y': 365, '3y': 1095, '5y': 1826, '10y': 3652, '20y': 7305 };
    if (days[pRange]) return last - days[pRange] * day;
    const t = new Date(last);
    if (pRange === 'mtd') return new Date(t.getFullYear(), t.getMonth(), 1).getTime();
    if (pRange === 'qtd') return new Date(t.getFullYear(), Math.floor(t.getMonth() / 3) * 3, 1).getTime();
    if (pRange === 'ytd') return new Date(t.getFullYear(), 0, 1).getTime();
    return 0;
  }
  const inWin = pts => { const mn = windowMin(); return mn ? pts.filter(p => p[0] >= mn) : pts; };

  function rangeStats(pairs) {
    const vals = pairs.map(p => p[1]).filter(v => v != null && isFinite(v));
    if (vals.length < 8) return null;
    const s = vals.slice().sort((a, b) => a - b);
    const pct = q => { const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.min(lo + 1, s.length - 1); return s[lo] + (i - lo) * (s[hi] - s[lo]); };
    return { high: s[s.length - 1], low: s[0], median: pct(0.5), p25: pct(0.25), p75: pct(0.75) };
  }

  function indexed(pts) {
    if (!pts.length) return [];
    const base = pts[0][1];
    if (!base) return pts;
    return pts.map(p => [p[0], +(p[1] / base * 100).toFixed(2)]);
  }

  function build() {
    const ba = baseAxisStyle(cc);
    const rightSeries = OVERLAYS.filter(o => active.has(o.key) && !o.key.startsWith('sma'));
    const leftSeries = OVERLAYS.filter(o => active.has(o.key) && o.key.startsWith('sma'));
    const yAxis = [];
    const series = [];

    const dataOf = key => inWin(src[keyOf(key)] || []);

    if (normalized) {
      yAxis.push(Object.assign({ type: 'value', position: 'right', scale: true, name: 'Base 100', nameTextStyle: { color: cc.muted } }, ba,
        { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 10.5 } }));
      const mk = (name, color) =>
        series.push({
          type: 'line', name, yAxisIndex: 0,
          data: indexed(dataOf(name)),
          showSymbol: false, lineStyle: { color, width: 1.6 }, itemStyle: { color },
          tooltip: { valueFormatter: v => v != null ? fmtNum(v, 1) : '—' },
        });
      mk('Precio', PRICE_C);
      OVERLAYS.filter(o => active.has(o.key)).forEach(o => mk(o.label, o.color));
    } else {
      yAxis.push(Object.assign({ type: logScale ? 'log' : 'value', position: 'left', scale: true, name: 'Precio', nameTextStyle: { color: cc.muted }, logBase: 10 }, ba,
        { axisLabel: { color: cc.muted, fontSize: 10.5, formatter: v => fmtNum(v, 0) } }));
      series.push({
        type: 'line', name: 'Precio', yAxisIndex: 0, data: dataOf('price'), showSymbol: false,
        lineStyle: { color: PRICE_C, width: 2 },
        itemStyle: { color: PRICE_C },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: PRICE_C + '14' }, { offset: 1, color: PRICE_C + '00' }]) },
        tooltip: { valueFormatter: v => fmtNum(v, 2) },
      });
      leftSeries.forEach(o => {
        series.push({ type: 'line', name: o.label, yAxisIndex: 0, data: dataOf(o.key), showSymbol: false, lineStyle: { color: o.color, width: 1.4 }, itemStyle: { color: o.color }, tooltip: { valueFormatter: o.fmt } });
      });
      let banded = null;
      rightSeries.forEach((o, i) => {
        const idx = i + 1;
        yAxis.push(Object.assign({ type: 'value', position: 'right', scale: true, offset: i * 46, name: o.label, nameTextStyle: { color: o.color, fontWeight: 600 } }, ba,
          { splitLine: { show: false }, axisLabel: { color: o.color, fontSize: 10.5, formatter: v => o.fmt(v) } }));
        const s = { type: 'line', name: o.label, yAxisIndex: idx, data: dataOf(o.key), showSymbol: false, lineStyle: { color: o.color, width: 1.8 }, itemStyle: { color: o.color }, tooltip: { valueFormatter: o.fmt } };
        if (!banded) {
          const lastTs = src[o.key].length ? src[o.key][src[o.key].length - 1][0] : 0;
          const ref = src[o.key].filter(p => p[0] >= lastTs - 10 * 365.25 * 86400000);
          const st = rangeStats(ref);
          if (st && st.high > st.low) {
            banded = o;
            s.markArea = {
              silent: true,
              itemStyle: { color: 'rgba(148,163,184,0.07)' },
              data: [[{ yAxis: st.p25 }, { yAxis: st.p75 }]],
            };
            s.markLine = {
              silent: true, symbol: 'none',
              data: [
                { yAxis: st.high, lineStyle: { color: cc.red, type: 'dashed', width: 1, opacity: 0.85 }, label: { show: true, color: cc.red, position: 'insideEndTop', fontSize: 10, formatter: () => 'Alto ' + o.fmt(st.high) } },
                { yAxis: st.median, lineStyle: { color: cc.muted, type: 'dashed', width: 1 }, label: { show: true, color: cc.muted, position: 'insideEndTop', fontSize: 10, formatter: () => 'Mediana ' + o.fmt(st.median) } },
                { yAxis: st.low, lineStyle: { color: cc.green, type: 'dashed', width: 1, opacity: 0.85 }, label: { show: true, color: cc.green, position: 'insideEndBottom', fontSize: 10, formatter: () => 'Bajo ' + o.fmt(st.low) } },
              ],
            };
          }
        }
        series.push(s);
      });
    }

    const axisCount = normalized ? 1 : 1 + rightSeries.length;
    makeChart('ch-overlay', {
      animationDuration: 350,
      grid: { left: 56, right: 14 + (axisCount - 1) * 46, top: 8, bottom: 52 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1, borderRadius: 8, padding: [10, 12],
        textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' },
        axisPointer: { type: 'line', lineStyle: { color: cc.muted, type: 'dashed', opacity: 0.5 } },
        formatter: (params) => {
          if (!params || !params.length) return '';
          const t = params[0].value ? params[0].value[0] : null;
          const dStr = t ? new Date(t).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: '2-digit' }) : '';
          let rows = '';
          for (const p of params) {
            if (!p.value || p.value[1] == null) continue;
            rows += `<div style="display:flex;justify-content:space-between;gap:20px;align-items:baseline;font-variant-numeric:tabular-nums">
              <span style="color:${cc.muted};font-size:11.5px"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}</span>
              <b style="color:${p.color};font-size:12.5px;font-weight:700">${fmtByName(p.seriesName)(p.value[1])}</b></div>`;
          }
          return `<div style="font-weight:700;color:${cc.text};margin-bottom:5px;font-size:11px;text-transform:uppercase;letter-spacing:.02em">${dStr}</div>${rows}`;
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, bottom: 8, height: 18,
          borderColor: cc.border, backgroundColor: 'transparent', showDetail: false,
          fillerColor: 'rgba(148,163,184,0.08)', handleStyle: { color: cc.muted }, handleSize: '70%',
          textStyle: { color: cc.muted, fontSize: 10 } },
      ],
      xAxis: Object.assign({ type: 'time' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 10.5 } }),
      yAxis,
      series,
    });
  }

  // toolbar: timeframes + frecuencia
  const pill = (parent, on, make) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ov-pill';
    b.textContent = make.label;
    const paint = () => b.classList.toggle('active', on());
    b.onclick = () => { make.fn(); paint(); build(); };
    paint();
    parent.appendChild(b);
  };
  if (timeEl) {
    timeEl.innerHTML = '';
    for (const r of RANGES) pill(timeEl, () => pRange === r.key, { label: r.label, fn: () => { pRange = r.key; } });
  }
  if (freqEl) {
    freqEl.innerHTML = '';
    for (const [key, label] of [['D', 'Diario'], ['W', 'Semanal'], ['M', 'Mensual']]) pill(freqEl, () => pFreq === key, { label, fn: () => { pFreq = key; } });
  }

  // chips de series activables
  chipsEl.innerHTML = '';
  for (const o of OVERLAYS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'overlay-chip';
    b.innerHTML = `<span class="dot" style="background:${o.color}"></span>${o.label}`;
    const paint = () => {
      const on = active.has(o.key);
      b.classList.toggle('active', on);
      b.style.cssText = on ? `border-color:${o.color};color:${o.color};background:${o.color}1c;` : '';
    };
    b.onclick = () => {
      if (active.has(o.key)) active.delete(o.key); else active.add(o.key);
      paint(); build();
    };
    paint();
    chipsEl.appendChild(b);
  }

  togglesEl.innerHTML = `
    <label class="ov-toggle"><input type="checkbox" id="ov-normalize"><span>Base 100</span></label>
    <label class="ov-toggle"><input type="checkbox" id="ov-log"><span>Escala log</span></label>`;
  const cbN = document.getElementById('ov-normalize');
  const cbL = document.getElementById('ov-log');
  cbN.onchange = e => { normalized = e.target.checked; build(); };
  cbL.onchange = e => { logScale = e.target.checked; build(); };

  build();

  // botón de descarga PNG (repite el patrón de las demás tarjetas)
  const head = el.closest('.card')?.querySelector('.section-heading');
  if (head && !head.querySelector('.btn-dl')) {
    const btn = document.createElement('button');
    btn.className = 'btn-dl';
    btn.title = 'Descargar gráfico como PNG';
    btn.textContent = '⤓';
    btn.onclick = () => {
      const ch = charts['ch-overlay'];
      if (!ch) return;
      const a = document.createElement('a');
      a.href = ch.getDataURL({ pixelRatio: 2, backgroundColor: isDark ? '#090d16' : '#ffffff' });
      a.download = `${(state && state.symbol) || 'chart'}_overlay.png`;
      a.click();
    };
    head.appendChild(btn);
  }
}
/* ------------------------------------------------- descarga como PNG */
export function addChartDownloadButtons() {
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
      const sym = (state && state.symbol) || 'chart';
      a.download = `${sym}_${div.id.replace('ch-', '')}.png`;
      a.click();
    };
    h3.appendChild(btn);
  });
}


/* ------------------------------------------------ comparador overlay */
export function renderCompareCharts(symbols, payloads, colors) {
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
export function renderAllCharts(data) {
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


/* ======================================================================
   renderKoyfinLayout — Populates the 4-zone Koyfin-style chart layout
   ====================================================================== */
export function renderKoyfinLayout(data) {
  if (!data) return;
  const cc  = getChartColors();
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const p   = data.profile  || {};
  const q   = data.quote    || {};
  const c   = data.current  || {};
  const est = data.estimates || {};
  const ih  = data.insidersHolders || {};

  // ── 1. TOP STRIP ────────────────────────────────────────────────────
  const elSym    = document.getElementById('koy-sym');
  const elPrice  = document.getElementById('koy-price');
  const elChange = document.getElementById('koy-change');
  const elAh     = document.getElementById('koy-ah');
  const elKpis   = document.getElementById('koy-strip-kpis');

  if (elSym)    elSym.textContent  = data.symbol || '—';
  if (elPrice)  elPrice.textContent = q.price != null ? fmtNum(q.price, q.price >= 1000 ? 0 : 2) : '—';

  if (elChange && q.previousClose && q.price) {
    const chgAbs = q.price - q.previousClose;
    const chgPct = (chgAbs / q.previousClose) * 100;
    const dir    = chgAbs >= 0;
    elChange.textContent  = `${dir ? '+' : ''}${fmtNum(chgAbs, 2)} (${dir ? '+' : ''}${fmtNum(chgPct, 2)}%)`;
    elChange.className    = 'koy-top-change ' + (dir ? 'up' : 'down');
  } else if (elChange) {
    elChange.textContent = '—';
    elChange.className   = 'koy-top-change';
  }

  if (elAh) {
    if (q.postMarketPrice) {
      const ahChg = q.postMarketChangePercent;
      elAh.textContent = `AH ${fmtNum(q.postMarketPrice, 2)} ${ahChg != null ? (ahChg >= 0 ? '+' : '') + fmtNum(ahChg * 100, 2) + '%' : ''}`;
      elAh.classList.remove('hidden');
    } else {
      elAh.classList.add('hidden');
    }
  }

  // KPIs en línea del Top Strip
  if (elKpis) {
    const pts = (data.history && data.history.price) || [];
    const cagr = (n) => {
      if (pts.length < 5) return null;
      const last = pts[pts.length - 1][0];
      const tgt  = last - n * 365.25 * 86400000;
      let i = 0;
      for (let k = 0; k < pts.length; k++) { if (pts[k][0] >= tgt) { i = k > 0 ? k - 1 : 0; break; } }
      const v0 = pts[i][1], v1 = pts[pts.length - 1][1];
      if (!v0 || !v1 || v0 <= 0) return null;
      return (Math.pow(v1 / v0, 1 / n) - 1) * 100;
    };
    const cagr3  = cagr(3);
    const cagr10 = cagr(10);
    let nextStr  = p.nextEarnings ? String(p.nextEarnings) : null;
    try { if (nextStr) nextStr = new Date(nextStr + 'T00:00:00').toLocaleDateString('es-CL', { weekday: 'short', day: '2-digit', month: 'short' }); } catch {}

    const kpiItem = (lbl, val, cls = '') =>
      `<div class="koy-kpi-item" title="${lbl}">
         <span class="koy-kpi-lbl">${lbl}</span>
         <span class="koy-kpi-val${cls ? ' ' + cls : ''}">${val || '—'}</span>
       </div>`;

    const pctCls = v => v == null ? '' : (v >= 0 ? ' up' : ' down');
    elKpis.innerHTML = [
      kpiItem('Sector',       p.sector   || '—'),
      kpiItem('Industry',     p.industry || '—'),
      kpiItem('Div. Yield',   c.divYield  != null ? fmtNum(c.divYield, 2) + '%' : '—'),
      kpiItem('Market Cap',   q.marketCap != null ? fmtBig(q.marketCap) : '—'),
      kpiItem('P/E Trailing', c.pe        != null ? fmtRatio(c.pe, 1) + 'x' : '—'),
      kpiItem('P/E Forward',  c.forwardPe != null ? fmtRatio(c.forwardPe, 1) + 'x' : '—'),
      kpiItem('CAGR 3Y',      cagr3  != null ? fmtNum(cagr3,  1, true) + '%' : '—', pctCls(cagr3)),
      kpiItem('CAGR 10Y',     cagr10 != null ? fmtNum(cagr10, 1, true) + '%' : '—', pctCls(cagr10)),
      kpiItem('Next Earnings', nextStr || '—'),
    ].join('');
  }

  // ── 2. LEFT SIDEBAR — nav routing ──────────────────────────────────
  const allNavBtns = document.querySelectorAll('[data-koy-view]');
  const CHART_MAP = {
    overlay:    () => { renderPriceOverlay(data); _koySetTitle('Precio + Múltiplos (Overlay)'); },
    pe:         () => { _koySwapCanvas('ch-pe-koy', 520); chartRatioInCanvas('ch-pe-koy', (data.history||{}).peTtm, (data.history||{}).peStats, '#4f8df7', 'PE (TTM)'); _koySetTitle('PE Ratio histórico (TTM)'); },
    income:     () => { _koySwapCanvas('ch-income-koy', 520); chartIncomeInCanvas('ch-income-koy', data); _koySetTitle('P&L — Ingresos y Utilidad'); },
    fcf:        () => { _koySwapCanvas('ch-fcf-koy', 520); chartFcfInCanvas('ch-fcf-koy', data); _koySetTitle('Free Cash Flow'); },
    returns:    () => { _koySwapCanvas('ch-returns-koy', 520); chartReturnsInCanvas('ch-returns-koy', data); _koySetTitle('Retornos — ROE y ROIC'); },
    shares:     () => { _koySwapCanvas('ch-shares-koy', 520); chartSharesInCanvas('ch-shares-koy', data); _koySetTitle('Acciones en circulación'); },
    debt:       () => { _koySwapCanvas('ch-debt-koy', 520); chartDebtInCanvas('ch-debt-koy', data); _koySetTitle('Balance — Deuda vs Caja'); },
    margins:    () => { _koySwapCanvas('ch-margins-koy', 520); chartMarginsInCanvas('ch-margins-koy', data); _koySetTitle('Márgenes — Bruto / Operativo / Neto'); },
    eps:        () => { _koySwapCanvas('ch-eps-koy', 520); chartEpsInCanvas('ch-eps-koy', data); _koySetTitle('EPS Histórico (Diluted)'); },
    divs:       () => { _koySwapCanvas('ch-divs-koy', 520); chartDividendsInCanvas('ch-divs-koy', data); _koySetTitle('Dividendo por acción (DPS)'); },
    technicals: () => { renderPriceOverlay(data); _koySetTitle('Técnico — MACD / RSI / SMA'); },
    sma:        () => { renderPriceOverlay(data); _koySetTitle('SMA 50 / SMA 200'); },
    'fa-val':   () => { renderPriceOverlay(data); _koySetTitle('FA — Valuation Overlay'); },
    'fa-fin':   () => { renderPriceOverlay(data); _koySetTitle('FA — Financials Overlay'); },
    'fa-growth':() => { renderPriceOverlay(data); _koySetTitle('FA — Growth Overlay'); },
    'fa-ratios':() => { renderPriceOverlay(data); _koySetTitle('FA — Key Ratios Overlay'); },
    estimates:  () => { renderPriceOverlay(data); _koySetTitle('Estimates'); },
  };

  allNavBtns.forEach(btn => {
    if (btn.dataset._koyBound) return; // evitar duplicar listeners
    btn.dataset._koyBound = '1';
    btn.addEventListener('click', () => {
      // Toggle active
      document.querySelectorAll('.koy-nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Mostrar toolbar solo en overlay
      const view = btn.getAttribute('data-koy-view');
      const isOverlay = (view === 'overlay');
      const toolbar = document.querySelector('.koy-chart-toolbar');
      const row2    = document.querySelector('.koy-toolbar-row2');
      if (toolbar) toolbar.style.display = isOverlay ? '' : 'none';
      if (row2)    row2.style.display    = isOverlay ? '' : 'none';
      // Ejecutar el chart
      const fn = CHART_MAP[view];
      if (fn) { try { fn(); } catch(e) { console.error('koy nav error:', e); } }
      setTimeout(() => Object.values(charts).forEach(ch => ch.resize()), 50);
    });
  });

  // ── 3. RIGHT SIDEBAR: Analyst Consensus ────────────────────────────
  _koyRenderAnalyst(data, cc, isDark);

  // ── 4. RIGHT SIDEBAR: Institutional Holders ────────────────────────
  _koyRenderHolders(ih, cc);

  // ── 5. RIGHT SIDEBAR: Insider Trades ───────────────────────────────
  _koyRenderInsiders(ih, cc);

  // ── 6. RIGHT SIDEBAR: Comparable Companies ─────────────────────────
  _koyRenderPeers(data, cc);

  // ── 7. RIGHT SIDEBAR: PE mini-chart ────────────────────────────────
  _koyRenderPeMini(data, cc);
}

/* ─────────────────────────── helpers internos ─────────────────────── */

function _koySetTitle(txt) {
  const el = document.getElementById('koy-chart-title');
  if (el) el.textContent = txt;
}

/** Replaces ch-overlay content with a temporary div for non-overlay charts */
function _koySwapCanvas(newId, h = 500) {
  const wrap = document.getElementById('ch-overlay');
  if (!wrap) return;
  // Hide overlay toolbar since this is a standalone chart
  wrap.innerHTML = `<div id="${newId}" style="width:100%;height:${h}px;"></div>`;
}

/** Analyst consensus donut in right sidebar */
function _koyRenderAnalyst(data, cc, isDark) {
  const donutEl = document.getElementById('koy-analyst-donut');
  const legEl   = document.getElementById('koy-analyst-legend');
  if (!donutEl) return;
  const est = data.estimates || {};
  const rec = est.recommendations || {};
  const buy  = (rec.strongBuy || 0) + (rec.buy || 0);
  const hold = rec.hold || 0;
  const sell = (rec.sell || 0) + (rec.strongSell || 0);
  const tot  = buy + hold + sell;
  if (tot === 0) {
    donutEl.innerHTML = '<div class="koy-no-data">Sin datos de analistas</div>';
    return;
  }
  const panel = isDark ? '#111720' : '#ffffff';
  const buyPct = Math.round(buy / tot * 100);
  if (charts['koy-analyst-donut']) charts['koy-analyst-donut'].dispose();
  const ch = echarts.init(donutEl, null, { renderer: 'canvas' });
  ch.setOption({
    animationDuration: 500,
    tooltip: {
      trigger: 'item',
      backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1,
      textStyle: { color: cc.text, fontSize: 11, fontFamily: 'Inter' },
    },
    graphic: [{
      type: 'text', left: 'center', top: '30%',
      style: { text: `${buyPct}%`, fill: '#22c55e', fontSize: 17, fontWeight: 700, fontFamily: 'Inter' },
    }, {
      type: 'text', left: 'center', top: '50%',
      style: { text: 'Buy', fill: cc.muted, fontSize: 10, fontFamily: 'Inter' },
    }],
    series: [{
      type: 'pie', radius: ['56%', '85%'], center: ['50%', '50%'],
      itemStyle: { borderColor: panel, borderWidth: 2, borderRadius: 4 },
      label: { show: false },
      data: [
        { value: buy,  name: `Comprar (${buy})`,  itemStyle: { color: '#22c55e' } },
        { value: hold, name: `Mantener (${hold})`, itemStyle: { color: cc.muted } },
        { value: sell, name: `Vender (${sell})`,   itemStyle: { color: '#f87171' } },
      ],
    }],
  });
  charts['koy-analyst-donut'] = ch;

  if (legEl) {
    const pt = est.priceTargets || {};
    const cur = data.quote && data.quote.price;
    const ups = cur && pt.mean ? ((pt.mean / cur) - 1) * 100 : null;
    legEl.innerHTML = [
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:#22c55e"></span>Buy ${buy}</div>`,
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:${cc.muted}"></span>Hold ${hold}</div>`,
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:#f87171"></span>Sell ${sell}</div>`,
      pt.mean ? `<div class="koy-analyst-legend-item" style="width:100%;margin-top:4px;color:${cc.muted}">Target <b style="color:${cc.text}">${fmtNum(pt.mean, 2)}${ups != null ? ` <span style="color:${ups >= 0 ? '#22c55e' : '#f87171'}">(${ups >= 0 ? '+' : ''}${fmtNum(ups, 1)}%)</span>` : ''}</b></div>` : '',
    ].join('');
  }
}

/** Institutional holders table in right sidebar */
function _koyRenderHolders(ih, cc) {
  const tbody = document.getElementById('koy-holders-tbody');
  if (!tbody) return;
  const holders = (ih.holders || []).slice(0, 8);
  if (!holders.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="koy-no-data">Sin datos</td></tr>`;
    return;
  }
  tbody.innerHTML = holders.map(h => {
    const chg = h.pctChange != null
      ? `<span style="color:${h.pctChange >= 0 ? '#22c55e' : '#f87171'}">${h.pctChange >= 0 ? '▲' : '▼'}${fmtNum(Math.abs(h.pctChange), 1)}%</span>`
      : '—';
    const name = (h.holder || '').replace(/,.*/, '').slice(0, 18);
    return `<tr>
      <td title="${escHtml(h.holder || '')}">${escHtml(name)}</td>
      <td class="num muted">${h.value ? fmtBig(h.value) : '—'}</td>
      <td class="num">${chg}</td>
    </tr>`;
  }).join('');
}

/** Insider trades list in right sidebar */
function _koyRenderInsiders(ih, cc) {
  const el = document.getElementById('koy-insiders-list');
  if (!el) return;
  const insiders = (ih.insiders || []).slice(0, 6);
  if (!insiders.length) {
    el.innerHTML = `<div class="koy-no-data">Sin datos de directivos</div>`;
    return;
  }
  el.innerHTML = insiders.map(x => {
    const t   = String(x.transaction || '');
    const isBuy  = /purchase|buy/i.test(t);
    const isSell = /sale/i.test(t);
    const tagCls = isBuy ? 'buy' : isSell ? 'sell' : 'other';
    const tagLbl = isBuy ? 'BUY' : isSell ? 'SELL' : t.slice(0, 6);
    const name   = (x.insider || '—').split(',')[0].slice(0, 20);
    const val    = x.value ? fmtBig(x.value) : (x.shares ? fmtNum(x.shares, 0) + ' sh' : '—');
    return `<div class="koy-insider-row">
      <span class="koy-insider-name" title="${escHtml(x.insider || '')}">${escHtml(name)}</span>
      <span class="koy-insider-meta">${val}</span>
      <span class="koy-insider-tag ${tagCls}">${escHtml(tagLbl)}</span>
    </div>`;
  }).join('');
}

/** Peer/comparable table in right sidebar */
function _koyRenderPeers(data, cc) {
  const tbody = document.getElementById('koy-peers-tbody');
  if (!tbody) return;
  // Use sector peers if available (data.comparables or data.sectorPeers)
  const peers = data.comparables || data.sectorPeers || [];
  if (!peers.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="koy-no-data">Sin comparables</td></tr>`;
    return;
  }
  const currentSym = data.symbol;
  tbody.innerHTML = peers.slice(0, 7).map(peer => {
    const isCur = peer.symbol === currentSym;
    const pe    = peer.pe  != null ? fmtRatio(peer.pe, 1) + 'x' : '—';
    const price = peer.price != null ? fmtNum(peer.price, peer.price >= 100 ? 0 : 2) : '—';
    return `<tr class="${isCur ? 'koy-peers-current' : ''}">
      <td title="${escHtml(peer.symbol)}">${escHtml(peer.symbol)}${isCur ? ' ★' : ''}</td>
      <td class="num">${price}</td>
      <td class="num">${pe}</td>
    </tr>`;
  }).join('');
}

/** PE trailing mini sparkline chart in right sidebar */
function _koyRenderPeMini(data, cc) {
  const el     = document.getElementById('koy-fwd-pe-chart');
  const legEl  = document.getElementById('koy-fwd-pe-legend');
  if (!el) return;
  const series = (data.history && data.history.peTtm) || [];
  if (series.length < 20) {
    el.innerHTML = '<div class="koy-no-data">Sin historial de PE</div>';
    return;
  }
  const tail = series.slice(-260); // últimos ~1 año de datos diarios
  const vals = tail.map(p => p[1]).filter(v => v != null && isFinite(v));
  const mn   = Math.min(...vals);
  const mx   = Math.max(...vals);
  const last = vals[vals.length - 1];
  const peSt = data.history.peStats || {};

  if (charts['koy-fwd-pe-chart']) charts['koy-fwd-pe-chart'].dispose();
  const ch = echarts.init(el, null, { renderer: 'canvas' });
  ch.setOption({
    animationDuration: 400,
    grid: { left: 4, right: 4, top: 4, bottom: 4 },
    xAxis: { type: 'time', show: false },
    yAxis: { type: 'value', show: false, scale: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1,
      textStyle: { color: cc.text, fontSize: 10.5, fontFamily: 'Inter' },
      formatter: p => {
        if (!p || !p[0] || !p[0].value) return '';
        const d = new Date(p[0].value[0]).toLocaleDateString('es-CL', { month: 'short', year: '2-digit' });
        return `${d} · <b>${fmtRatio(p[0].value[1], 1)}x</b>`;
      },
    },
    series: [{
      type: 'line', data: tail, showSymbol: false,
      lineStyle: { color: '#4f8df7', width: 1.5 },
      areaStyle: { color: 'rgba(79,141,247,0.10)' },
    }],
  });
  charts['koy-fwd-pe-chart'] = ch;

  if (legEl) {
    legEl.innerHTML = [
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:#f87171"></span>High ${fmtRatio(mx, 1)}x</div>`,
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:#fbbf24"></span>Median ${peSt.median ? fmtRatio(peSt.median, 1) + 'x' : '—'}</div>`,
      `<div class="koy-analyst-legend-item"><span class="koy-dot" style="background:#22c55e"></span>Low ${fmtRatio(mn, 1)}x</div>`,
    ].join('');
  }
}

/* ─── Canvas-swapping wrappers para nav del left sidebar ──────────── */
/* Cada función crea un div temporal dentro de ch-overlay y llama a     */
/* makeChart con ese id, reutilizando las funciones existentes pero      */
/* sin depender de sus IDs fijos (ch-pe, ch-income, etc.)               */

function chartRatioInCanvas(id, pairs, stats, color, name) {
  if (!pairs || pairs.length < 6) { document.getElementById(id) && (document.getElementById(id).innerHTML = '<div class="koy-no-data">Datos insuficientes</div>'); return; }
  const cc = getChartColors();
  const lastVal = pairs[pairs.length - 1][1];
  const markLineData = [];
  if (stats && stats.p25 != null) markLineData.push({ yAxis: stats.p25, lineStyle: { color: cc.muted, type: 'dotted', width: 1, opacity: 0.5 }, label: { show: false } });
  if (stats && stats.p75 != null) markLineData.push({ yAxis: stats.p75, lineStyle: { color: cc.muted, type: 'dotted', width: 1, opacity: 0.5 }, label: { show: false } });
  if (stats && stats.median != null) markLineData.push({ yAxis: stats.median, lineStyle: { color: cc.gold, type: 'dashed', width: 1.5 }, label: { color: cc.gold, fontSize: 10.5, fontWeight: 700, position: 'insideEndTop', formatter: `Mediana ${stats.median}x`, fontFamily: 'Inter' } });
  if (lastVal != null) markLineData.push({ yAxis: lastVal, lineStyle: { color: cc.green, type: 'solid', width: 1.8 }, label: { color: cc.green, fontSize: 10.5, fontWeight: 700, position: 'insideEndBottom', formatter: `Hoy ${lastVal.toFixed(1)}x` } });
  const ba = baseAxisStyle(cc);
  makeChart(id, timeOption({
    grid: { left: 50, right: 22, top: 24, bottom: 40 },
    yAxis: Object.assign({ type: 'value', scale: true }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}x' } }),
    series: [{ type: 'line', data: pairs, showSymbol: false, name, smooth: 0.3, lineStyle: { color, width: 2.2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: color + '30' }, { offset: 1, color: color + '00' }]) }, markLine: { silent: true, symbol: 'none', data: markLineData } }],
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 6, height: 18, borderColor: cc.border, fillerColor: color + '18', handleStyle: { color: cc.muted }, showDetail: false }],
  }));
}

function chartIncomeInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.revenue != null);
  if (a.length < 2) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  const cur = data.profile && data.profile.currency;
  makeChart(id, yearsOption(a.map(x => x.year), {
    yAxis: [Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }), Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } })],
    series: [
      { type: 'bar', name: 'Ingresos',      data: a.map(x => x.revenue),   itemStyle: { color: cc.blue,  borderRadius: [4,4,0,0] }, barMaxWidth: 34, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'bar', name: 'Utilidad neta', data: a.map(x => x.netIncome), itemStyle: { color: cc.green, borderRadius: [4,4,0,0] }, barMaxWidth: 34, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'Margen neto', yAxisIndex: 1, data: a.map(x => x.netMargin != null ? +x.netMargin.toFixed(1) : null), lineStyle: { color: cc.gold, width: 2 }, itemStyle: { color: cc.gold }, tooltip: { valueFormatter: v => fmtPct(v) } },
    ],
  }));
}

function chartFcfInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.fcf != null);
  if (a.length < 2) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  const cur = data.profile && data.profile.currency;
  makeChart(id, yearsOption(a.map(x => x.year), {
    yAxis: [Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }), Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } })],
    series: [
      { type: 'bar', name: 'FCF', data: a.map(x => x.fcf), barMaxWidth: 40, itemStyle: { color: p => p.value >= 0 ? cc.green : cc.red, borderRadius: [4,4,0,0] }, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'Margen FCF', yAxisIndex: 1, data: a.map(x => x.fcfMargin != null ? +x.fcfMargin.toFixed(1) : null), lineStyle: { color: cc.gold, width: 2 }, itemStyle: { color: cc.gold }, tooltip: { valueFormatter: v => fmtPct(v) } },
    ],
  }));
}

function chartReturnsInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.roe != null || x.roic != null);
  if (a.length < 2) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  makeChart(id, yearsOption(a.map(x => x.year), {
    yAxis: Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    series: [
      { type: 'bar', name: 'ROE',  data: a.map(x => x.roe  != null ? +x.roe.toFixed(1)  : null), itemStyle: { color: cc.blue,   borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtPct(v) } },
      { type: 'bar', name: 'ROIC', data: a.map(x => x.roic != null ? +x.roic.toFixed(1) : null), itemStyle: { color: cc.violet, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtPct(v) }, markLine: { silent: true, symbol: 'none', lineStyle: { color: cc.gold, type: 'dashed' }, data: [{ yAxis: 15 }] } },
    ],
  }));
}

function chartSharesInCanvas(id, data) {
  const pts = data.history && data.history.shares;
  if (!pts || pts.length < 4) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  makeChart(id, timeOption({
    yAxis: Object.assign({ type: 'value', scale: true }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }),
    series: [{ type: 'line', data: pts, showSymbol: false, step: 'end', lineStyle: { color: cc.cyan, width: 2 }, areaStyle: { color: 'rgba(6,182,212,0.08)' } }],
  }));
}

function chartDebtInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.totalDebt != null || x.cash != null);
  if (a.length < 2) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  const cur = data.profile && data.profile.currency;
  makeChart(id, yearsOption(a.map(x => x.year), {
    yAxis: [Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: v => fmtBig(v) } }), Object.assign({ type: 'value' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}x' } })],
    series: [
      { type: 'bar', name: 'Deuda total', data: a.map(x => x.totalDebt), itemStyle: { color: cc.red,   borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'bar', name: 'Caja',        data: a.map(x => x.cash),      itemStyle: { color: cc.green, borderRadius: [4,4,0,0] }, barMaxWidth: 30, tooltip: { valueFormatter: v => fmtBig(v, cur) } },
      { type: 'line', name: 'D/E', yAxisIndex: 1, data: a.map(x => x.debtToEquity != null ? +x.debtToEquity.toFixed(2) : null), lineStyle: { color: cc.amber, width: 2 }, itemStyle: { color: cc.amber }, tooltip: { valueFormatter: v => fmtRatio(v, 2) } },
    ],
  }));
}

function chartMarginsInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.netMargin != null || x.grossMargin != null);
  if (a.length < 2) return;
  const cc = getChartColors(), ba = baseAxisStyle(cc);
  const line = (name, key, color) => ({ type: 'line', name, data: a.map(x => x[key] != null ? +x[key].toFixed(1) : null), lineStyle: { color, width: 2 }, itemStyle: { color }, symbolSize: 5, tooltip: { valueFormatter: v => fmtPct(v) } });
  makeChart(id, yearsOption(a.map(x => x.year), {
    yAxis: Object.assign({ type: 'value' }, ba, { axisLabel: { color: cc.muted, fontSize: 11, formatter: '{value}%' } }),
    series: [line('Margen bruto', 'grossMargin', cc.cyan), line('Margen operativo', 'opMargin', cc.violet), line('Margen neto', 'netMargin', cc.gold)],
  }));
}

function chartEpsInCanvas(id, data) {
  const a = (data.annuals || []).filter(x => x.eps != null);
  if (a.length < 2) return;
  const cc = getChartColors();
  makeChart(id, yearsOption(a.map(x => x.year), {
    series: [{ type: 'bar', name: 'EPS diluido', data: a.map(x => +x.eps.toFixed(2)), barMaxWidth: 40, itemStyle: { color: p => p.value >= 0 ? cc.gold : cc.red, borderRadius: [4,4,0,0] }, label: { show: true, position: 'top', color: cc.muted, fontSize: 11, formatter: p => fmtNum(p.value, 2) } }],
  }));
}

function chartDividendsInCanvas(id, data) {
  const d = data.history && data.history.dividends;
  if (!d || d.length < 3) return;
  const cc = getChartColors();
  const curYear = new Date().getFullYear();
  makeChart(id, yearsOption(d.map(x => x[0]), {
    series: [{ type: 'bar', name: 'DPS', barMaxWidth: 26, data: d.map(x => ({ value: +x[1].toFixed(3), itemStyle: x[0] === curYear ? { color: 'rgba(34,197,94,0.35)', borderRadius: [4,4,0,0] } : { color: cc.green, borderRadius: [4,4,0,0] } })), tooltip: { valueFormatter: v => fmtNum(v, 3) } }],
  }));
}

// Inline escHtml for use in renderKoyfinLayout without importing
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
