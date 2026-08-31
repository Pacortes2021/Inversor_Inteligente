/* Screener de valor: modos rápido/profundo, universos, filtros y export CSV. */

import { fmtPrice, fmtNum, fmtPct, escHtml, pctClass } from "./format.js?v=78";
import { renderHeatmap } from "./charts.js?v=78";
import { go } from "./router.js?v=78";

const scr = {
  universe: "us", mode: "quick", view: "table",
  data: null,          // filas del modo/universo actual
  loadedKey: null,     // `${mode}_${universe}` ya cargado
  sortKey: "score", sortDir: -1,
  pollTimer: null,
  pollToken: 0,
};

const COLS_QUICK = [
  ["symbol", "Símbolo"], ["name", "Empresa"], ["sector", "Sector"],
  ["price", "Precio", "num"], ["pe", "PE", "num"], ["forwardPe", "PE fwd", "num"],
  ["fcfYield", "FCF yield", "num"], ["roe", "ROE", "num"],
  ["debtToEquity", "D/P", "num"], ["drawdown", "vs 52s máx", "num"],
  ["distSma200d", "vs SMA200d", "num"], ["distSma200w", "vs SMA200w", "num"],
  ["score", "Puntaje", "num"],
];

const COLS_DEEP = [
  ["symbol", "Símbolo"], ["name", "Empresa"], ["sector", "Sector"],
  ["price", "Precio", "num"], ["pe", "PE", "num"], ["peMedian", "PE med 15a", "num"],
  ["vsMedian", "vs mediana", "num"], ["fairValue", "Valor justo", "num"],
  ["mos", "Margen seg.", "num"], ["verdict", "Veredicto"],
  ["distSma200d", "vs SMA200d", "num"], ["distSma200w", "vs SMA200w", "num"],
  ["roc", "ROC", "num"], ["fScore", "F-Score", "num"],
  ["score", "Puntaje", "num"],
];

const COLS_TARGETS2030 = [
  ["symbol", "Símbolo"], ["name", "Empresa"],
  ["price", "Precio Actual", "num"], ["basePe", "PE Salida", "num"], ["eps2030", "EPS 2030E", "num"],
  ["targetCons", "Obj. Conservador (-20%)", "num"], ["cagrCons", "CAGR Cons.", "num"],
  ["targetBase", "★ Obj. Base (Mediana)", "num"], ["cagrBase", "★ CAGR Base", "num"],
  ["upsideBase", "Upside Base", "num"],
  ["targetOpt", "Obj. Optimista (+20%)", "num"], ["cagrOpt", "CAGR Opt.", "num"],
];

function scrCols() {
  if (scr.view === "targets2030") return COLS_TARGETS2030;
  return scr.mode === "deep" ? COLS_DEEP : COLS_QUICK;
}

export async function loadScreener(refresh = false) {
  const key = `${scr.mode}_${scr.universe}`;
  if (scr.loadedKey === key && scr.data && !refresh) return;

  scr.pollToken++; // invalida cualquier poll en curso del universo anterior
  clearTimeout(scr.pollTimer);
  const btn = document.getElementById("btn-refresh");
  document.getElementById("screener-loading").classList.remove("hidden");
  document.getElementById("screener-table").classList.add("hidden");
  document.getElementById("deep-progress").classList.add("hidden");
  btn.disabled = true;

  try {
    if (scr.mode === "quick") {
      document.getElementById("screener-loading-msg").textContent =
        "Escaneando universo… la primera vez toma ~1 minuto.";
      const r = await fetch(`/api/screener?universe=${scr.universe}${refresh ? "&refresh=1" : ""}`);
      scr.data = (await r.json()).results || [];
      finishScreenerLoad(key);
    } else {
      await pollDeep(refresh);
    }
  } catch (e) {
    document.getElementById("screener-loading-msg").textContent = "⚠ Error: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

async function pollDeep(refresh = false) {
  const token = scr.pollToken;
  const r = await fetch(`/api/screener/deep?universe=${scr.universe}${refresh ? "&refresh=1" : ""}`);
  const d = await r.json();
  if (token !== scr.pollToken) return; // universo/modo cambió mientras se consultaba
  if (d.status === "done") {
    scr.data = d.results || [];
    scr.sortKey = "mos"; scr.sortDir = -1;
    finishScreenerLoad(`deep_${scr.universe}`);
    return;
  }
  // en curso: muestra progreso y sigue consultando
  if (token !== scr.pollToken) return;
  document.getElementById("screener-loading").classList.remove("hidden");
  document.getElementById("screener-table").classList.add("hidden");
  document.getElementById("screener-loading-msg").textContent =
    `Análisis profundo en curso: ${d.done}/${d.total} acciones (DCF + PE histórico de 15 años vía SEC EDGAR). La primera vez toma varios minutos.`;
  const bar = document.getElementById("deep-progress");
  bar.classList.remove("hidden");
  document.getElementById("deep-progress-fill").style.width =
    (d.total ? (d.done / d.total * 100) : 0) + "%";
  scr.pollTimer = setTimeout(() => { if (token === scr.pollToken) pollDeep(false); }, 4000);
}

function finishScreenerLoad(key) {
  scr.loadedKey = key;
  document.getElementById("screener-loading").classList.add("hidden");
  fillSectorFilter();
  renderScreener();
}

function fillSectorFilter() {
  const sel = document.getElementById("f-sector");
  const cur = sel.value;
  const sectors = [...new Set((scr.data || []).map(r => r.sector).filter(Boolean))].sort();
  sel.innerHTML = `<option value="">Todos</option>` +
    sectors.map(s => `<option value="${escHtml(s)}">${escHtml(s)}</option>`).join("");
  sel.value = sectors.includes(cur) ? cur : "";
}

const toNum = v => (v != null && v !== '' && !isNaN(v)) ? parseFloat(v) : null;

function smaMatch(r) {
  /* Devuelve {kind:'d'|'w', dist} si la fila cumple el filtro SMA activo, o null.
     Comparte la semántica con filteredRows(). */
  const period = document.getElementById('f-sma-period')?.value;
  if (!period) return null;
  const side = document.getElementById('f-sma-side')?.value || 'near';
  const band = toNum(document.getElementById('f-sma-band')?.value) ?? 3;
  const inRange = d => {
    if (d == null) return false;
    if (side === 'below') return d <= 0 && d >= -band;
    if (side === 'above') return d >= 0 && d <= band;
    return Math.abs(d) <= band;
  };
  if (period !== 'w' && inRange(r.distSma200d)) return { kind: 'd', dist: r.distSma200d };
  if (period !== 'd' && inRange(r.distSma200w)) return { kind: 'w', dist: r.distSma200w };
  return null;
}

function filteredRows() {
  const sector       = document.getElementById('f-sector').value;
  const text         = document.getElementById('f-text').value.trim().toLowerCase();
  const minMosVal    = document.getElementById('f-min-mos')?.value;
  const maxPeVal     = document.getElementById('f-max-pe')?.value;
  const maxFwdPeVal  = document.getElementById('f-max-fwdpe')?.value;
  const minRoeVal    = document.getElementById('f-min-roe')?.value;
  const minNetMarginVal = document.getElementById('f-min-netmargin')?.value;
  const minFcfYieldVal  = document.getElementById('f-min-fcfyield')?.value;
  const maxDeVal        = document.getElementById('f-max-de')?.value;
  const smaPeriodVal    = document.getElementById('f-sma-period')?.value;
  const smaSideVal      = document.getElementById('f-sma-side')?.value;

  const minMos       = toNum(minMosVal);
  const maxPe        = toNum(maxPeVal);
  const maxFwdPe     = toNum(maxFwdPeVal);
  const minRoe       = toNum(minRoeVal);
  const minNetMargin = toNum(minNetMarginVal);
  const minFcfYield  = toNum(minFcfYieldVal);
  const maxDe        = toNum(maxDeVal);

  let rows = [...(scr.data || [])];  if (sector)       rows = rows.filter(r => r.sector === sector);
  if (text)         rows = rows.filter(r =>
    r.symbol.toLowerCase().includes(text) || (r.name || '').toLowerCase().includes(text));
  if (minMos       != null) rows = rows.filter(r => r.mos        != null && r.mos        >= minMos);
  // FIX: exclude negative PEs — a company with PE=-5 is NOT "cheap" at PE <= 15, it's losing money
  if (maxPe        != null) rows = rows.filter(r => r.pe         != null && r.pe > 0    && r.pe         <= maxPe);
  if (maxFwdPe     != null) rows = rows.filter(r => r.forwardPe  != null && r.forwardPe > 0 && r.forwardPe  <= maxFwdPe);
  if (minRoe       != null) rows = rows.filter(r => r.roe        != null && r.roe        >= minRoe);
  if (minNetMargin != null) rows = rows.filter(r => r.netMargin  != null && r.netMargin  >= minNetMargin);
  if (minFcfYield  != null) rows = rows.filter(r => r.fcfYield   != null && r.fcfYield   >= minFcfYield);
  if (maxDe        != null) rows = rows.filter(r => r.debtToEquity != null && r.debtToEquity <= maxDe);

  if (smaPeriodVal) {
    rows = rows.filter(r => smaMatch(r) !== null);
  }

  const naVerdict = r => r.verdict && r.verdict.level === "na";
  rows.sort((a, b) => {
    let va = a[scr.sortKey], vb = b[scr.sortKey];
    if (scr.sortKey === "verdict") { va = a.mos; vb = b.mos; }
    // al rankear por margen de seguridad, los veredictos no confiables se hunden
    if (scr.sortKey === "mos" || scr.sortKey === "verdict") {
      if (naVerdict(a)) va = null;
      if (naVerdict(b)) vb = null;
    }
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "string") return va.localeCompare(vb) * scr.sortDir;
    return (va - vb) * scr.sortDir;
  });
  return rows;
}

function renderScreener() {
  if (!scr.data) return;

  const ctlView = document.getElementById("ctl-view");
  if (ctlView) ctlView.style.display = "";
  
  const mapOption = document.querySelector("#f-view option[value='map']");
  if (mapOption) mapOption.disabled = (scr.mode !== "deep");

  const asMap = scr.mode === "deep" && scr.view === "map";
  document.getElementById("screener-heatmap").classList.toggle("hidden", !asMap);
  if (asMap) {
    document.getElementById("screener-table").classList.add("hidden");
    document.getElementById("screener-sub").textContent =
      "Mapa del universo: tamaño = capitalización, color = margen de seguridad (verde: infravalorada). Clic para analizar.";
    renderHeatmap(filteredRows(), s => go(s));
    return;
  }

  // Calcular precios objetivo por escenario (mejorado: usa PE mediano real del modo deep)
  (scr.data || []).forEach(r => {
    if (r.price && r.price > 0) {
      // 1. PER base: preferir peMedian histórico del modo deep (15 años), luego forward, luego trailing
      const cleanMed = (r.peMedian && r.peMedian > 0 && r.peMedian <= 80) ? r.peMedian : null;
      const cleanFpe = (r.forwardPe && r.forwardPe > 0 && r.forwardPe <= 80) ? r.forwardPe : null;
      const cleanPe  = (r.pe && r.pe > 0 && r.pe <= 80) ? r.pe : null;

      const basePe = cleanMed || cleanFpe || cleanPe || 18; // 18x = mediana histórica S&P500
      r.basePe = Math.round(basePe * 10) / 10;

      // Escenarios: ±20% del PE base
      const consPe = Math.max(5, basePe * 0.80);
      const optPe  = basePe * 1.20;

      // 2. EPS 2030 (4 años): usando la tasa de crecimiento implícita del mercado
      //    Si tenemos epsForward del screener, usamos eso como base real (más preciso)
      let epsBase;
      if (r.epsForward && r.epsForward > 0) {
        epsBase = r.epsForward; // EPS estimado próximo año
      } else {
        // Fallback: invertir del PE forward o trailing
        const refPe = cleanFpe || cleanPe || 20;
        epsBase = refPe > 0 ? r.price / refPe : r.price / 20;
      }
      // Crecer EPS 4 años a ~10% anual (tasa conservadora de largo plazo)
      const eps2030 = epsBase * (1.10 ** 4);
      r.eps2030 = Math.round(eps2030 * 100) / 100;

      // 3. Precios objetivo — guard against negative EPS/targets that produce NaN CAGR
      const safeCAGR = (target, price) => {
        if (target <= 0 || price <= 0) return null;
        return Math.round(((target / price) ** (1/4) - 1) * 1000) / 10;
      };

      r.targetCons = Math.round(eps2030 * consPe * 100) / 100;
      r.cagrCons   = safeCAGR(r.targetCons, r.price);

      r.targetBase = Math.round(eps2030 * basePe * 100) / 100;
      r.cagrBase   = safeCAGR(r.targetBase, r.price);

      r.targetOpt  = Math.round(eps2030 * optPe * 100) / 100;
      r.cagrOpt    = safeCAGR(r.targetOpt, r.price);

      // 4. Upside vs precio actual al objetivo base
      r.upsideBase = r.targetBase > 0 ? Math.round((r.targetBase / r.price - 1) * 1000) / 10 : null;
    }
  });


  const cols = scrCols();

  const TERMS = { pe: "pe", forwardPe: "pefwd", peMedian: "banda", vsMedian: "banda",
    fcfYield: "fcfyield", roe: "roe", debtToEquity: "de", drawdown: "drawdown",
    score: "score", mos: "mos", fairValue: "dcf", pb: "pb" };
  document.getElementById("screener-thead").innerHTML = cols.map(([k, label, cls]) =>
    `<th data-k="${k}" class="${cls || ""}">${escHtml(label)}${TERMS[k] ? ` <span class="info-i" data-term="${TERMS[k]}">ⓘ</span>` : ""}${scr.sortKey === k ? (scr.sortDir < 0 ? " ↓" : " ↑") : ""}</th>`).join("");

  const rows = filteredRows();
  const tbody = document.querySelector("#screener-table tbody");
  tbody.innerHTML = rows.map(r => {
    const cells = cols.map(([k, , cls]) => {
      let v;
      switch (k) {
        case 'symbol': {
          const m = smaMatch(r);
          const chip = m ? `<span class="sma-match-chip" title="Pasa el filtro SMA200: ${m.kind === 'd' ? 'diaria' : 'semanal'} a ${fmtPct(m.dist, 1, true)}">≈SMA</span>` : '';
          return `<td class="sym" style="cursor:pointer;">${escHtml(r.symbol)}${chip}</td>`;
        }
        case 'name': return `<td><div style="font-weight:600; font-size:12.5px; line-height:1.3;">${escHtml(r.name || '—')}</div><div style="font-size:10px; color:var(--muted); margin-top:1px;">${escHtml(r.sector || '')}</div></td>`;
        case 'sector': return `<td></td>`; /* sector va dentro de name; celda vacía para mantener la alineación */
        case "price": v = fmtPrice(r.price, r.currency); break;
        case "pe": v = r.pe != null ? fmtNum(r.pe, 1) : "—"; break;
        case "forwardPe": v = r.forwardPe != null ? fmtNum(r.forwardPe, 1) : "—"; break;
        case "peMedian": v = r.peMedian != null ? fmtNum(r.peMedian, 1) : "—"; break;
        case "vsMedian": return `<td class="num ${r.vsMedian != null && r.vsMedian < 0 ? "up" : "down"}">${fmtPct(r.vsMedian, 0, true)}</td>`;
        case "fairValue": v = r.fairValue != null ? fmtPrice(r.fairValue, r.currency) : "—"; break;
        case "mos": return `<td class="num ${pctClass(r.mos)}"><b>${fmtPct(r.mos, 0, true)}</b></td>`;
        case "verdict": {
          const lvl = r.verdict ? r.verdict.level : "na";
          const short = { buy: "Infravalorada", hold: "Razonable", warn: "Algo cara", sell: "Sobrevalorada", na: "Sin datos" }[lvl];
          return `<td><span class="verdict-chip ${lvl}">${short}</span></td>`;
        }
        case 'fcfYield': v = fmtPct(r.fcfYield, 2); break;
        case 'roe': v = r.roe != null ? fmtPct(r.roe, 1) : '—'; break;
        case 'roc': v = r.roc != null ? fmtPct(r.roc, 1) : '—'; break;
        case "fScore": v = r.fScore != null ? r.fScore + " / 9" : "—"; break;
        case "debtToEquity": v = r.debtToEquity != null ? fmtNum(r.debtToEquity, 2) : "—"; break;
        case "drawdown": return `<td class="num ${pctClass(r.drawdown)}">${fmtPct(r.drawdown, 1)}</td>`;
        case "distSma200d": {
          const m = smaMatch(r);
          const hit = m && m.kind === 'd' ? ' sma-hit' : '';
          return `<td class="num ${pctClass(r.distSma200d)}${hit}" title="Precio vs SMA 200 diaria${r.sma200d ? ' (' + fmtPrice(r.sma200d, r.currency) + ')' : ''} · ${r.smaDate || '—'}">${r.distSma200d != null ? fmtPct(r.distSma200d, 1, true) : '—'}</td>`;
        }
        case "distSma200w": {
          const m = smaMatch(r);
          const hit = m && m.kind === 'w' ? ' sma-hit' : '';
          return `<td class="num ${pctClass(r.distSma200w)}${hit}" title="Precio vs SMA 200 semanal${r.sma200w ? ' (' + fmtPrice(r.sma200w, r.currency) + ')' : ''} · ${r.smaDate || '—'}">${r.distSma200w != null ? fmtPct(r.distSma200w, 1, true) : '—'}</td>`;
        }
        case 'eps2030': v = r.eps2030 != null ? fmtPrice(r.eps2030, r.currency) : "—"; break;
        case 'basePe': v = r.basePe != null ? fmtNum(r.basePe, 1) + "x" : "—"; break;
        case 'targetCons': v = r.targetCons != null ? fmtPrice(r.targetCons, r.currency) : "—"; break;
        case 'cagrCons': return `<td class="num ${r.cagrCons != null && r.cagrCons >= 0 ? "up" : "down"}">${r.cagrCons != null ? fmtPct(r.cagrCons, 1, true) : '—'}</td>`;
        case 'targetBase': return `<td class="num font-bold" style="color:var(--green);">${r.targetBase != null ? fmtPrice(r.targetBase, r.currency) : '—'}</td>`;
        case 'cagrBase': return `<td class="num ${r.cagrBase != null && r.cagrBase >= 0 ? "up" : "down"}" style="font-weight:700;"><b>${r.cagrBase != null ? fmtPct(r.cagrBase, 1, true) : '—'}</b></td>`;
        case 'upsideBase': return `<td class="num ${r.upsideBase != null && r.upsideBase >= 0 ? 'up' : 'down'}" style="font-weight:800; font-size:13px;">${r.upsideBase != null ? (r.upsideBase >= 0 ? '+' : '') + r.upsideBase.toFixed(0) + '%' : '—'}</td>`;
        case 'targetOpt': v = r.targetOpt != null ? fmtPrice(r.targetOpt, r.currency) : "—"; break;
        case 'cagrOpt': return `<td class="num ${r.cagrOpt != null && r.cagrOpt >= 0 ? "up" : "down"}">${r.cagrOpt != null ? fmtPct(r.cagrOpt, 1, true) : '—'}</td>`;
        case "score": {
          const cls2 = r.score >= 65 ? "hi" : r.score >= 45 ? "mid" : "lo";
          return `<td class="num"><span class="score-chip ${cls2}">${r.score != null ? fmtNum(r.score, 0) : "—"}</span></td>`;
        }
        default: v = r[k] ?? "—";
      }
      return `<td class="${cls || ""}">${v}</td>`;
    }).join("");
    return `<tr data-symbol="${escHtml(r.symbol)}">${cells}</tr>`;
  }).join("");

  if (scr.view === "targets2030") {
    document.getElementById("screener-sub").textContent =
      `${rows.length} acciones analizadas con proyecciones a 2030E en 3 escenarios PER (Conservador -20%, Base Mediana y Optimista +20%).`;
  } else if (scr.mode === "deep") {
    document.getElementById("screener-sub").textContent =
      `${rows.length} acciones con valoración completa (DCF + reversión al PE de 15 años + Graham). Ordenadas por margen de seguridad.`;
  } else {
    document.getElementById("screener-sub").textContent =
      `${rows.length} acciones puntuadas por valoración (45%), calidad (30%), salud financiera (15%) y castigo en precio (10%).`;
  }
  document.getElementById("screener-table").classList.remove("hidden");
}

function exportCsv() {
  const cols = scrCols();
  const rows = filteredRows();
  const esc = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
  const lines = [cols.map(c => esc(c[1])).join(";")];
  for (const r of rows) {
    lines.push(cols.map(([k]) => {
      if (k === "verdict") return esc(r.verdict ? r.verdict.label : "");
      return esc(r[k]);
    }).join(";"));
  }
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `screener_${scr.mode}_${scr.universe}_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ============================================================ PRESETS ============================================================ */

const PRESETS = {
  quality: {
    label: 'Calidad Total',
    filters: { 'f-min-roe': 15, 'f-min-netmargin': 10, 'f-min-fcfyield': 3, 'f-max-de': 1 },
    desc: 'ROE > 15% · Margen neto > 10% · FCF Yield > 3% · D/E < 1'
  },
  buffett: {
    label: 'Buffett',
    filters: { 'f-min-roe': 15, 'f-min-netmargin': 10, 'f-max-pe': 25, 'f-max-de': 0.5 },
    desc: 'ROE > 15% · Margen neto > 10% · PE < 25 · D/E < 0.5'
  },
  deep: {
    label: 'Valor Profundo',
    filters: { 'f-min-mos': 20, 'f-max-pe': 20 },
    mode: 'deep',
    desc: 'Margen de seguridad > 20% · PE < 20'
  },
  growth: {
    label: 'Crecimiento',
    filters: { 'f-min-roe': 20, 'f-min-fcfyield': 4 },
    desc: 'ROE > 20% · FCF Yield > 4%'
  },
  targets2030: {
    label: 'Objetivos 2030',
    filters: { 'f-min-roe': 12 },
    view: 'targets2030',
    desc: 'Matriz de Precios Objetivos a 2030E en 3 escenarios PER (Conservador -20%, Base Mediana y Optimista +20%).'
  },
  clean: {
    label: 'Sin Red Flags',
    filters: { 'f-min-fcfyield': 0, 'f-max-de': 1.5 },
    desc: 'FCF Yield ≥ 0% · D/E < 1.5'
  },
  sma200: {
    label: 'Compra SMA 200',
    filters: { 'f-min-roe': 15, 'f-min-netmargin': 10, 'f-max-de': 1,
               'f-sma-period': 'any', 'f-sma-side': 'below', 'f-sma-band': 3 },
    desc: 'Calidad (ROE > 15% · Mg. neto > 10% · D/E < 1) y precio en o hasta 3% bajo su SMA 200 (diaria o semanal).'
  }
};

const FILTER_IDS = ['f-min-mos','f-max-pe','f-max-fwdpe','f-min-roe','f-min-netmargin','f-min-fcfyield','f-max-de','f-text','f-sector','f-sma-period','f-sma-side','f-sma-band'];

let activePreset = null;

function clearFilters() {
  FILTER_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = '';
  });
  syncSmaControls();
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  activePreset = null;
  renderScreener();
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) return clearFilters();

  // Limpiar todos los filtros primero (incluye selects del SMA: no deben
  // arrastrarse de un preset al siguiente)
  FILTER_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  syncSmaControls();

  // Aplicar filtros del preset
  Object.entries(preset.filters).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  });

  if (preset.view) {
    scr.view = preset.view;
    const viewEl = document.getElementById('f-view');
    if (viewEl) viewEl.value = preset.view;
    scr.sortKey = 'cagrBase';
    scr.sortDir = -1;
  }

  // Cambiar a modo profundo si el preset lo requiere
  if (preset.mode) {
    const modeEl = document.getElementById('f-mode');
    if (modeEl && modeEl.value !== preset.mode) {
      modeEl.value = preset.mode;
      scr.mode = preset.mode;
      scr.sortKey = 'mos'; scr.sortDir = -1;
      scr.data = null;
      // Marcar botón activo
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      document.querySelector(`.preset-btn[data-preset="${name}"]`)?.classList.add('active');
      activePreset = name;
      syncSmaControls();
      loadScreener();
      return;
    }
  }

  // Marcar botón activo
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.preset-btn[data-preset="${name}"]`)?.classList.add('active');
  activePreset = name;
  syncSmaControls();

  // Mostrar descripción del preset
  const sub = document.getElementById('screener-sub');
  if (sub && scr.data) sub.textContent = `🔍 Preset "${preset.label}": ${preset.desc}`;

  renderScreener();
}

/* Eventos de presets */
document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
});

/* Eventos filtros */
function syncSmaControls() {
  const on = !!document.getElementById('f-sma-period').value;
  document.getElementById('ctl-sma-side')?.classList.toggle('hidden', !on);
  document.getElementById('ctl-sma-band')?.classList.toggle('hidden', !on);
}
document.getElementById('btn-refresh').addEventListener('click', () => loadScreener(true));
document.getElementById('btn-csv').addEventListener('click', exportCsv);
document.getElementById('f-universe').addEventListener('change', e => {
  scr.universe = e.target.value; scr.data = null; loadScreener();
});
document.getElementById('f-mode').addEventListener('change', e => {
  scr.mode = e.target.value;
  scr.sortKey = scr.mode === 'deep' ? 'mos' : 'score'; scr.sortDir = -1;
  scr.data = null; loadScreener();
});
document.getElementById('f-sector').addEventListener('change', renderScreener);
document.getElementById('f-text').addEventListener('input', () => { activePreset = null; document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active')); renderScreener(); });
  ['f-min-mos','f-max-pe','f-max-fwdpe','f-min-roe','f-min-netmargin','f-min-fcfyield','f-max-de','f-sma-period','f-sma-side','f-sma-band'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', () => {
    /* Si el usuario toca un filtro manualmente, deseleccionar preset */
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    activePreset = null;
    syncSmaControls();
    renderScreener();
  });
});
document.addEventListener('DOMContentLoaded', syncSmaControls);
document.getElementById('f-view').addEventListener('change', e => {
  scr.view = e.target.value; renderScreener();
});

document.getElementById("screener-thead").addEventListener("click", e => {
  const th = e.target.closest("th");
  if (!th) return;
  if (e.target.closest(".info-i")) return;
  const k = th.dataset.k;
  if (!k) return;
  if (scr.sortKey === k) scr.sortDir *= -1;
  else { scr.sortKey = k; scr.sortDir = ["symbol", "name", "sector"].includes(k) ? 1 : -1; }
  renderScreener();
});
