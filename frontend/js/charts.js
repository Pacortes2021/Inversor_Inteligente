/* Gráficos ECharts con tema propio — El Inversor Inteligente */

import { fmtBig, fmtPrice, fmtPct, fmtRatio, fmtNum } from "./format.js";
import { state } from "./state.js";

/** Colores que se adaptan al tema claro/oscuro en tiempo de ejecución */
export function getChartColors() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    gold:   '#d97706', green:  '#0d9488', red:    '#e11d48',
    blue:   '#3b82f6', cyan:   '#0ea5e9', violet: '#8b5cf6', amber: '#d97706',
    text:   dark ? '#f1f5f9'  : '#0f172a',
    muted:  dark ? '#94a3b8'  : '#64748b',
    border: dark ? '#1e293b'  : '#e2e8f0',
    grid:   dark ? '#1a2236'  : '#eef1f5',
    panel:  dark ? '#131a22'  : '#ffffff',
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
    axisLine: { lineStyle: { color: cc.border } },
    axisLabel: { color: cc.muted, fontSize: 11, fontFamily: 'Inter, sans-serif' },
    splitLine: { lineStyle: { color: cc.grid } },
  };
}

/* Retro-compatibilidad: baseAxis legacy (usa colores estáticos) */
export const baseAxis = {
  axisLine: { lineStyle: { color: C.border } },
  axisLabel: { color: C.muted, fontSize: 11, fontFamily: 'Inter, sans-serif' },
  splitLine: { lineStyle: { color: C.grid } },
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
      borderWidth: 1, borderRadius: 10, padding: [10, 14],
      extraCssText: 'box-shadow: 0 10px 28px rgba(0,0,0,0.18); backdrop-filter: blur(6px);',
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
  if (!el || !chipsEl || !togglesEl) return;
  const cc = getChartColors();
  const hist = (data && data.history) || {};
  const pricePts = hist.price || [];
  if (pricePts.length < 30) return;

  const OVERLAYS = [
    { key: 'peTtm',  label: 'PE',            color: '#3b82f6', fmt: v => fmtRatio(v, 1) },
    { key: 'psTtm',  label: 'PS',            color: '#8b5cf6', fmt: v => fmtRatio(v, 2) },
    { key: 'pbTtm',  label: 'PB',            color: '#0ea5e9', fmt: v => fmtRatio(v, 2) },
    { key: 'pcfTtm', label: 'P/CF',          color: '#e11d48', fmt: v => fmtRatio(v, 1) },
    { key: 'epsTtm', label: 'EPS TTM',       color: '#10b981', fmt: v => fmtNum(v, 2) },
    { key: 'revTtm', label: 'Revenue TTM',   color: '#f59e0b', fmt: v => fmtBig(v) },
    { key: 'netMarginTtm', label: 'Margen TTM', color: '#ec4899', fmt: v => fmtPct(v, 1) },
    { key: 'sma50',  label: 'SMA 50',        color: '#94a3b8', fmt: v => fmtNum(v, 2) },
    { key: 'sma200', label: 'SMA 200',       color: '#64748b', fmt: v => fmtNum(v, 2) },
  ];

  const src = {};
  for (const o of OVERLAYS) {
    const raw = hist[o.key] || [];
    src[o.key] = raw.filter(p => p && p[1] != null);
  }
  src.sma50 = sma(pricePts, 50);
  src.sma200 = sma(pricePts, 200);

  const FMT = {};
  for (const o of OVERLAYS) FMT[o.label] = o.fmt;
  const fmtByName = name => FMT[name] || (name === 'Precio' ? (v => fmtNum(v, 2)) : (v => v));

  const active = new Set(['peTtm']);
  let normalized = false;
  let logScale = false;

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

    if (normalized) {
      yAxis.push(Object.assign({ type: 'value', position: 'right', scale: true, name: 'Base 100', nameTextStyle: { color: cc.muted } }, ba,
        { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 10.5 } }));
      const mk = (name, color) =>
        series.push({
          type: 'line', name, yAxisIndex: 0,
          data: indexed(name === 'Precio' ? pricePts : (src[name] || [])),
          showSymbol: false, lineStyle: { color, width: 1.8 }, itemStyle: { color },
          tooltip: { valueFormatter: v => v != null ? fmtNum(v, 1) : '—' },
        });
      mk('Precio', cc.gold);
      OVERLAYS.filter(o => active.has(o.key)).forEach(o => mk(o.label, o.color));
    } else {
      yAxis.push(Object.assign({ type: logScale ? 'log' : 'value', position: 'left', scale: true, name: 'Precio', nameTextStyle: { color: cc.muted }, logBase: 10 }, ba,
        { axisLabel: { color: cc.muted, fontSize: 10.5, formatter: v => fmtNum(v, 0) } }));
      series.push({
        type: 'line', name: 'Precio', yAxisIndex: 0, data: pricePts, showSymbol: false,
        lineStyle: { color: cc.gold, width: 2.5, shadowColor: cc.gold + '55', shadowBlur: 8, shadowOffsetY: 4 },
        itemStyle: { color: cc.gold },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: cc.gold + '26' }, { offset: 1, color: cc.gold + '00' }]) },
        tooltip: { valueFormatter: v => fmtNum(v, 2) },
      });
      leftSeries.forEach(o => {
        series.push({ type: 'line', name: o.label, yAxisIndex: 0, data: src[o.key], showSymbol: false, lineStyle: { color: o.color, width: 1.4 }, itemStyle: { color: o.color }, tooltip: { valueFormatter: o.fmt } });
      });
      rightSeries.forEach((o, i) => {
        const idx = i + 1;
        yAxis.push(Object.assign({ type: 'value', position: 'right', scale: true, offset: i * 46, name: o.label, nameTextStyle: { color: o.color, fontWeight: 600 } }, ba,
          { splitLine: { show: false }, axisLabel: { color: o.color, fontSize: 10.5, formatter: v => o.fmt(v) } }));
        series.push({ type: 'line', name: o.label, yAxisIndex: idx, data: src[o.key], showSymbol: false, lineStyle: { color: o.color, width: 1.8 }, itemStyle: { color: o.color }, tooltip: { valueFormatter: o.fmt } });
      });
    }

    const axisCount = normalized ? 1 : 1 + rightSeries.length;
    makeChart('ch-overlay', {
      animationDuration: 400,
      grid: { left: 60, right: 14 + (axisCount - 1) * 46, top: 26, bottom: 52 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: cc.panel, borderColor: cc.border, borderWidth: 1, borderRadius: 10, padding: [10, 14],
        extraCssText: 'box-shadow: 0 10px 28px rgba(0,0,0,0.18);',
        textStyle: { color: cc.text, fontSize: 12, fontFamily: 'Inter, sans-serif' },
        axisPointer: { type: 'line', lineStyle: { color: cc.muted, type: 'dashed', opacity: 0.5 } },
        formatter: (params) => {
          if (!params || !params.length) return '';
          const t = params[0].value ? params[0].value[0] : null;
          const dStr = t ? new Date(t).toLocaleDateString('es-CL', { year: 'numeric', month: 'short' }) : '';
          let rows = '';
          for (const p of params) {
            if (!p.value || p.value[1] == null) continue;
            rows += `<div style="display:flex;justify-content:space-between;gap:16px;align-items:baseline">
              <span style="color:${cc.muted}"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}</span>
              <b style="color:${cc.text}">${fmtByName(p.seriesName)(p.value[1])}</b></div>`;
          }
          return `<div style="font-weight:700;color:${cc.text};margin-bottom:4px">${dStr}</div>${rows}`;
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, bottom: 8, height: 18,
          borderColor: cc.border, backgroundColor: cc.grid, fillerColor: 'rgba(59,130,246,0.12)',
          handleStyle: { color: cc.muted }, textStyle: { color: cc.muted, fontSize: 10 } },
      ],
      xAxis: Object.assign({ type: 'time' }, ba, { splitLine: { show: false }, axisLabel: { color: cc.muted, fontSize: 10.5 } }),
      yAxis,
      series,
    });
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
      if (on) b.style.cssText = `border-color:${o.color};color:${o.color};background:${o.color}1f;`;
      else b.style.cssText = '';
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
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      const a = document.createElement('a');
      a.href = ch.getDataURL({ pixelRatio: 2, backgroundColor: dark ? '#090d16' : '#ffffff' });
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

