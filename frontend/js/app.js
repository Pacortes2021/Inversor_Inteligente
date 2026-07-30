/* Lógica principal: routing, carga de datos, render del análisis y DCF interactivo. */

const state = { symbol: null, data: null, activeTab: "summary" };
let currentPeriodYears = 1;

const $ = id => document.getElementById(id);

/* ------------------------------------------------------------- routing */
const VIEWS = ["analisis", "screener", "comparar", "watchlist", "portafolio"];
const UNLOCKED_TABS = ["summary", "valuation", "financials-hub", "ownership", "financials", "ratios", "rating", "estimates", "insiders", "eps-fv", "dcf-fv", "ddm-fv", "historical-ratios", "dividends", "earnings", "qualitative", "additional"];

/* ------------------------------------------------------------- theme toggle */
function initTheme() {
  const stored = localStorage.getItem("theme") || "dark";
  setTheme(stored);
}

function setTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("theme", t);
  const btn = $("theme-toggle");
  if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = $("theme-toggle");
  if (btn) {
    btn.onclick = () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(current === "dark" ? "light" : "dark");
    };
  }
  initTheme();
});

const TAB_MAP = {
  "summary": "summary",
  "rating": "summary",
  "qualitative": "summary",

  "valuation": "valuation",
  "estimates": "valuation",
  "eps-fv": "valuation",
  "dcf-fv": "valuation",
  "ddm-fv": "valuation",

  "financials-hub": "financials-hub",
  "financials": "financials-hub",
  "ratios": "financials-hub",
  "historical-ratios": "financials-hub",
  "dividends": "financials-hub",
  "earnings": "financials-hub",

  "ownership": "ownership",
  "insiders": "ownership",
  "additional": "ownership"
};

function route() {
  const hash = location.hash || "#/analisis";
  let current = VIEWS.find(v => hash.startsWith(`#/${v}`)) || "analisis";
  
  for (const v of VIEWS) {
    $(`view-${v}`).classList.toggle("hidden", v !== current);
    $(`tab-${v}`).classList.toggle("active", v === current);
  }
  
  if (current === "screener") loadScreener();
  else if (current === "watchlist") loadWatchlist();
  else if (current === "portafolio") loadPortfolio();
  else if (current === "analisis") {
    const parts = hash.split("/");
    const sym = parts[2] ? decodeURIComponent(parts[2]).toUpperCase() : (state.symbol || "NVDA");
    let tab = parts[3] || "summary";
    const masterTab = TAB_MAP[tab] || "summary";
    
    state.activeTab = masterTab;

    // Activar botón de pestaña de acción
    document.querySelectorAll(".action-tabs .a-tab").forEach(btn => {
      const active = (btn.dataset.pane === masterTab || btn.dataset.pane === tab);
      btn.classList.toggle("active", active);
    });
    
    // Activar panel(es) de pestaña de acción — soporta panes divididos (prefix match)
    document.querySelectorAll(".tab-pane").forEach(pane => {
      const isActive = pane.id === `pane-${masterTab}` || pane.id.startsWith(`pane-${masterTab}-`);
      pane.classList.toggle("hidden", !isActive);
    });

    if (sym !== state.symbol) {
      loadSymbol(sym);
    } else if (state.data) {
      triggerTabSpecificActions(masterTab);
    }
  }
}

let currentMultiplesRange = "all";

function renderRatiosCharts(d, range = "all") {
  currentMultiplesRange = range;
  const btnContainer = $("multiples-range-controls");
  if (btnContainer) {
    btnContainer.querySelectorAll(".period-btn-mult").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-range") === range);
    });
  }

  const now = Date.now();
  let minTs = 0;
  if (range === "ytd") {
    minTs = new Date(new Date().getFullYear(), 0, 1).getTime();
  } else if (range === "1") {
    minTs = now - 365 * 24 * 60 * 60 * 1000;
  } else if (range === "3") {
    minTs = now - 3 * 365 * 24 * 60 * 60 * 1000;
  } else if (range === "5") {
    minTs = now - 5 * 365 * 24 * 60 * 60 * 1000;
  } else if (range === "10") {
    minTs = now - 10 * 365 * 24 * 60 * 60 * 1000;
  }

  const filterPairs = (pairs) => {
    if (!pairs) return [];
    if (range === "all") return pairs;
    return pairs.filter(pt => pt[0] >= minTs);
  };

  const pePairs = filterPairs(d.history.peTtm);
  const psPairs = filterPairs(d.history.psTtm);
  const pbPairs = filterPairs(d.history.pbTtm);

  const getStats = (pairs) => {
    if (!pairs || pairs.length < 2) return null;
    const vals = pairs.map(pt => pt[1]).filter(v => v != null).sort((a, b) => a - b);
    if (vals.length === 0) return null;
    const pct = (arr, p) => {
      const idx = (arr.length - 1) * p;
      const base = Math.floor(idx);
      const rest = idx - base;
      return arr[base + 1] !== undefined ? arr[base] + rest * (arr[base + 1] - arr[base]) : arr[base];
    };
    return {
      median: parseFloat(pct(vals, 0.5).toFixed(1)),
      p25: parseFloat(pct(vals, 0.25).toFixed(1)),
      p75: parseFloat(pct(vals, 0.75).toFixed(1))
    };
  };

  chartRatio("ch-pe", pePairs, getStats(pePairs), C.blue, "PE (TTM)");
  chartRatio("ch-ps", psPairs, getStats(psPairs), C.violet, "P/Ventas (TTM)");
  chartRatio("ch-pb", pbPairs, getStats(pbPairs), C.cyan, "P/Valor libro");
  requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
}

function triggerTabSpecificActions(tab) {
  if (tab === "summary") {
    chartPriceSummary(state.data);
  } else if (tab === "valuation") {
    renderEstimates(state.data?.estimates);
    renderEpsEstimatesChart(state.data?.estimates);
    requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
  } else if (tab === "financials-hub" || tab === "financials" || tab === "ratios") {
    renderAllCharts(state.data);
    renderRatiosCharts(state.data, currentMultiplesRange);
    chartDividends(state.data);
    chartEps(state.data);
    
    const btnContainer = $("multiples-range-controls");
    if (btnContainer && !btnContainer.dataset.bound) {
      btnContainer.dataset.bound = "1";
      btnContainer.querySelectorAll(".period-btn-mult").forEach(btn => {
        btn.onclick = () => {
          renderRatiosCharts(state.data, btn.getAttribute("data-range"));
        };
      });
    }
    requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
  } else if (tab === "ownership" || tab === "insiders") {
    renderInsidersHolders(state.data?.insidersHolders);
    renderAdditional(state.data);
  }
}

// Configurar click handlers en los tabs de acción del HTML
document.querySelectorAll(".action-tabs .a-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    const pane = btn.dataset.pane;
    if (state.symbol) {
      location.hash = `#/analisis/${state.symbol}/${pane}`;
    }
  });
});

window.addEventListener("hashchange", route);

/* --------------------------------------------------------------- toast */
let toastTimer = null;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}

/* ------------------------------------------------------------ búsqueda */
let searchTimer = null;
$("search-input").addEventListener("input", e => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  if (q.length < 2) return hideSearch();
  searchTimer = setTimeout(() => doSearch(q), 280);
});
$("search-input").addEventListener("keydown", e => {
  if (e.key === "Enter") {
    const q = e.target.value.trim().toUpperCase();
    if (q) go(q);
  }
  if (e.key === "Escape") hideSearch();
});
document.addEventListener("click", e => {
  if (!e.target.closest(".search-box")) hideSearch();
});

async function doSearch(q) {
  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const { results } = await r.json();
    const box = $("search-results");
    if (!results.length) return hideSearch();
    box.innerHTML = results.map(it =>
      `<div class="search-item" onclick="go('${it.symbol}')">
         <span class="sym">${it.symbol}</span>
         <span class="name">${it.name}</span>
         <span class="ex">${it.exchange}</span>
       </div>`).join("");
    box.classList.remove("hidden");
  } catch { hideSearch(); }
}

function hideSearch() { $("search-results").classList.add("hidden"); }

function go(symbol) {
  hideSearch();
  $("search-input").value = "";
  location.hash = `#/analisis/${encodeURIComponent(symbol)}/${state.activeTab || "summary"}`;
}

/* --------------------------------------------------------------- carga */
const LOADING_MSGS = [
  "Descargando fundamentales…",
  "Construyendo series de ratios históricos…",
  "Calculando valor intrínseco…",
  "Aplicando los criterios de Buffett…",
];

async function loadSymbol(symbol) {
  state.symbol = symbol;
  $("analysis-content").classList.add("hidden");
  $("error-box").classList.add("hidden");
  $("loading").classList.remove("hidden");

  let msgIdx = 0;
  $("loading-msg").textContent = LOADING_MSGS[0];
  const msgTimer = setInterval(() => {
    msgIdx = (msgIdx + 1) % LOADING_MSGS.length;
    $("loading-msg").textContent = LOADING_MSGS[msgIdx];
  }, 2500);

  try {
    const r = await fetch(`/api/stock/${encodeURIComponent(symbol)}`);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${r.status}`);
    }
    state.data = await r.json();
    renderAnalysis(state.data);
  } catch (e) {
    $("error-box").textContent = "⚠ " + (e.message || "No se pudo cargar el símbolo.");
    $("error-box").classList.remove("hidden");
  } finally {
    clearInterval(msgTimer);
    $("loading").classList.add("hidden");
  }
}

/* --------------------------------------------------------------- render */
function renderAnalysis(d) {
  document.title = `${d.symbol} · El Inversor Inteligente`;

  // Asegurar que el contenedor principal esté visible inmediatamente
  const analysisBox = $("analysis-content");
  if (analysisBox) analysisBox.classList.remove("hidden");

  // Encabezado corporativo
  if ($("co-name")) $("co-name").textContent = `${d.symbol} - ${d.profile.name}`;
  if ($("co-currency")) $("co-currency").textContent = d.profile.currency || "USD";
  if ($("co-price")) $("co-price").textContent = fmtPrice(d.quote.price, d.profile.currency);
  
  const chg = d.quote.previousClose ? (d.quote.price / d.quote.previousClose - 1) * 100 : null;
  if ($("co-change")) {
    $("co-change").textContent = chg != null ? fmtPct(chg, 2, true) : "";
    $("co-change").className = "price-change-value " + pctClass(chg);
  }

  // Logo de empresa
  const logoCircle = $("co-logo-circle");
  if (logoCircle) logoCircle.textContent = d.symbol.slice(0, 2);

  // After hours
  if (d.quote.postMarketPrice && d.quote.postMarketChangePercent) {
    if ($("ah-price")) $("ah-price").textContent = fmtPrice(d.quote.postMarketPrice, d.profile.currency);
    const ahChg = d.quote.postMarketChangePercent;
    if ($("ah-change")) {
      $("ah-change").textContent = fmtPct(ahChg, 2, true);
      $("ah-change").className = "after-hours-chg " + pctClass(ahChg);
    }
    if ($("ah-wrapper")) $("ah-wrapper").classList.remove("hidden");
  } else {
    if ($("ah-wrapper")) $("ah-wrapper").classList.add("hidden");
  }

  const safeCall = (fn, arg) => { try { fn(arg); } catch(err) { console.error("Render sub-step error:", err); } };

  safeCall(renderWarnings, d.warnings);
  safeCall(renderSummary, d);
  safeCall(renderValuationCard, d);
  safeCall(renderRatiosGrid, d);
  safeCall(renderGrowthTable, d);
  safeCall(renderDividendSafety, d.dividendSafety);
  safeCall(renderBuffettScorecard, d.scorecard);
  safeCall(renderEstimates, d.estimates);
  safeCall(renderInsidersHolders, d.insidersHolders);
  safeCall(renderFinancialStatements, d);
  safeCall(renderEpsFv, d);
  safeCall(renderDcfFv, d);
  safeCall(renderDdmFv, d);
  safeCall(renderHistoricalRatios, d);
  safeCall(renderAdditional, d);
  safeCall(checkStockAlerts, d);
  safeCall(renderNews, d.news);

  try { loadNotes(d.symbol); } catch(e){}
  try { setStarState(d.inWatchlist); } catch(e){}
  
  safeCall(triggerTabSpecificActions, state.activeTab);

  if ($("co-summary")) $("co-summary").textContent = d.profile.summary || "";
  if (analysisBox) analysisBox.classList.remove("hidden");
}

/* ----------------------------------------------------- render summary */
function renderSummary(d) {
  const cur = d.profile.currency;
  const px = d.quote.price;

  // Tarjeta 1: Fair Value
  $("fv-symbol-title").textContent = `${d.symbol} Fair Value`;
  const consensusVal = d.valuation.consensus;
  $("fv-consensus-val").textContent = consensusVal ? fmtPrice(consensusVal, cur) : "—";
  const mos = d.valuation.marginOfSafety;
  $("fv-mos-pct").innerHTML = mos != null 
    ? `Margin of Safety: <b class="${mos >= 0 ? "up" : "down"}">${fmtPct(mos, 1, true)}</b>` 
    : "No hay datos";
  
  if (d.current.analystTarget && d.current.analystRecommendation) {
    $("fv-analyst-target").innerHTML = `Wall St Target: <b style="color:#0ea5e9">${fmtPrice(d.current.analystTarget, cur)}</b> (${d.current.analystRecommendation.toUpperCase()})`;
  } else {
    $("fv-analyst-target").textContent = "Wall St Target: —";
  }
  
  const verdict = d.valuation.verdict;
  const vBadge = $("verdict-badge");
  vBadge.textContent = verdict.label;
  vBadge.className = "verdict-badge-new " + verdict.level;

  // Tarjeta 2: Graham Model
  const grahamModel = d.valuation.models.find(m => m.id === "graham_intrinsic" || m.id === "graham");
  if (grahamModel) {
    $("graham-val").textContent = fmtPrice(grahamModel.fair, cur);
    $("graham-upside").textContent = fmtPct(grahamModel.upside, 1, true) + " vs precio";
    $("graham-upside").className = "card-subtext " + pctClass(grahamModel.upside);
  } else {
    $("graham-val").textContent = "—";
    $("graham-upside").textContent = "—";
    $("graham-upside").className = "card-subtext";
  }

  // Tarjeta 3: DCF Model
  const dcfModel = d.valuation.models.find(m => m.id === "dcf");
  if (dcfModel) {
    $("dcf-val").textContent = fmtPrice(dcfModel.fair, cur);
    $("dcf-upside").textContent = fmtPct(dcfModel.upside, 1, true) + " vs precio";
    $("dcf-upside").className = "card-subtext " + pctClass(dcfModel.upside);
    // Barra de progreso: precio relativo al fair value
    const barWrap = $("dcf-price-bar-wrap");
    const barFill = $("dcf-price-bar");
    const barPct = $("dcf-bar-pct");
    if (barWrap && barFill && barPct) {
      const pxRatio = Math.min(1, Math.max(0, px / dcfModel.fair));
      barFill.style.width = (pxRatio * 100).toFixed(1) + "%";
      barFill.style.background = dcfModel.upside >= 0 ? "var(--green)" : "var(--red)";
      barPct.textContent = fmtPct(px / dcfModel.fair * 100, 0) + " de FV";
      barWrap.style.display = "block";
    }
  } else {
    $("dcf-val").textContent = "—";
    $("dcf-upside").textContent = "—";
    $("dcf-upside").className = "card-subtext";
    const barWrap = $("dcf-price-bar-wrap");
    if (barWrap) barWrap.style.display = "none";
  }

  // Tarjeta 4: Financial Indicators
  $("ind-altman").textContent = d.current.altmanZ != null ? d.current.altmanZ.toFixed(2) : "—";
  const z = d.current.altmanZ;
  $("ind-altman").className = "v " + (z > 2.9 ? "green" : z < 1.1 ? "red" : "gold");

  $("ind-piotroski").textContent = d.current.fScore != null ? `${d.current.fScore} / 9` : "—";
  const fs = d.current.fScore;
  $("ind-piotroski").className = "v " + (fs >= 7 ? "green" : fs <= 3 ? "red" : "gold");

  $("ind-wc").textContent = d.current.workingCapital != null ? fmtBig(d.current.workingCapital, cur) : "—";
  $("ind-wc").className = "v " + (d.current.workingCapital >= 0 ? "green" : "red");

  $("ind-insider").textContent = d.current.insiderPercent != null ? fmtPct(d.current.insiderPercent, 2) : "—";

  // Tarjeta 5: Technical Indicators
  $("ind-rsi").textContent = d.current.rsi != null ? d.current.rsi.toFixed(1) : "—";
  const rsiVal = d.current.rsi;
  $("ind-rsi").className = "v " + (rsiVal < 30 ? "green" : rsiVal > 70 ? "red" : "");

  const ma50Diff = d.current.sma50 ? (px / d.current.sma50 - 1) * 100 : null;
  $("ind-ma50").textContent = ma50Diff != null ? fmtPct(ma50Diff, 1, true) : "—";
  $("ind-ma50").className = "v " + (ma50Diff >= 0 ? "green" : "red");

  const ma200Diff = d.current.sma200 ? (px / d.current.sma200 - 1) * 100 : null;
  $("ind-ma200").textContent = ma200Diff != null ? fmtPct(ma200Diff, 1, true) : "—";
  $("ind-ma200").className = "v " + (ma200Diff >= 0 ? "green" : "red");

  const shortF = d.current.shortPercent;
  const shortR = d.current.shortRatio;
  $("ind-short").textContent = shortF != null ? `${fmtPct(shortF, 1)} (${shortR != null ? shortR.toFixed(1) + 'd' : '—'})` : "—";

  // Sidebar Ratios
  $("sum-mcap").textContent = fmtBig(d.quote.marketCap, cur);
  
  // 52 Week Range progress bar
  const { low52w, high52w } = d.quote;
  if (low52w && high52w && high52w > low52w) {
    const rangePct = Math.max(0, Math.min(100, (px - low52w) / (high52w - low52w) * 100));
    $("sum-52w-range").textContent = `${fmtPrice(low52w, cur)} - ${fmtPrice(high52w, cur)}`;
    $("range-52w-low").textContent = fmtPrice(low52w, cur);
    $("range-52w-high").textContent = fmtPrice(high52w, cur);
    $("range-52w-fill").style.width = rangePct + "%";
    $("range-52w-pin").style.left = rangePct + "%";
  } else {
    $("sum-52w-range").textContent = "—";
    $("range-52w-low").textContent = "—";
    $("range-52w-high").textContent = "—";
    $("range-52w-fill").style.width = "0%";
    $("range-52w-pin").style.left = "0%";
  }

  $("sum-beta").textContent = d.current.beta != null ? d.current.beta.toFixed(2) : "—";
  
  const pe = d.current.pe;
  const fpe = d.current.forwardPe;
  const peReliable = pe != null && pe > 0 && pe <= 150;
  const peText = pe != null ? (peReliable ? pe.toFixed(1) + 'x' : pe.toFixed(0) + 'x ⚠') : "—";
  const fpeText = fpe != null ? fpe.toFixed(1) + 'x' : "—";
  const peEl = $("sum-pe");
  if (peEl) {
    peEl.textContent = `${peText} (${fpeText})`;
    peEl.style.color = !peReliable && pe != null ? "var(--gold)" : "";
    peEl.title = !peReliable && pe != null ? "PE muy elevado — EPS puede ser cercano a cero o distorsionado por cargo puntual" : "";
  }

  // PE vs mediana histórica
  const peStats = d.history?.peStats;
  const peMedRow = $("sum-pe-median-row");
  const peMedEl = $("sum-pe-median");
  const peMedBadge = $("sum-pe-vs-median-badge");
  if (peStats && peStats.median && peReliable && peMedRow && peMedEl) {
    const med = peStats.median;
    const vs = peStats.vsMedian; // % vs mediana
    peMedEl.textContent = `Med 15a: ${med.toFixed(1)}x`;
    if (peMedBadge && vs != null) {
      const isAbove = vs > 0;
      peMedBadge.textContent = (isAbove ? '+' : '') + vs.toFixed(0) + '%';
      peMedBadge.style.background = isAbove ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)';
      peMedBadge.style.color = isAbove ? 'var(--red)' : 'var(--green)';
    }
    peMedRow.style.display = "";
  } else if (peMedRow) {
    peMedRow.style.display = "none";
  }

  // Micro-gráficos de PE
  const peVals = d.history.peTtm ? d.history.peTtm.map(pt => pt[1]).slice(-24) : [];
  $("pe-sparkline").innerHTML = peVals.length >= 2 ? sparkSvgSmall(peVals, "#3b82f6") : "";

  $("sum-eps").textContent = d.current.eps != null ? fmtPrice(d.current.eps, cur) : "—";

  // Micro-gráficos de EPS
  const epsVals = d.annuals ? d.annuals.map(a => a.eps).filter(x => x != null) : [];
  $("eps-sparkline").innerHTML = epsVals.length >= 2 ? sparkSvgSmall(epsVals, "#10b981") : "";
  
  const divVal = d.current.divYield != null ? `${fmtPct(d.current.divYield, 2)}` : "—";
  const divSVal = d.dividendSafety && d.dividendSafety.payoutFcf != null ? `(${fmtPct(d.dividendSafety.payoutFcf, 0)})` : "";
  $("sum-div").textContent = `${divVal} ${divSVal}`;

  // Micro-gráficos de Dividendos
  const divVals = d.annuals ? d.annuals.map(a => a.dividendPS).filter(x => x != null) : [];
  $("div-sparkline").innerHTML = divVals.length >= 2 ? sparkSvgSmall(divVals, "#d97706") : "";

  $("sum-vol").textContent = d.quote.volume != null ? d.quote.volume.toLocaleString("es-CL") : "—";
  $("sum-avg-vol").textContent = d.quote.avgVolume != null ? d.quote.avgVolume.toLocaleString("es-CL") : "—";

  // FCF Yield y Next Earnings
  const fcfYieldEl = $("sum-fcf-yield");
  if (fcfYieldEl) {
    const fcfy = d.current.fcfYield;
    fcfYieldEl.textContent = fcfy != null ? fmtPct(fcfy, 2) : "—";
    fcfYieldEl.className = "val " + (fcfy != null && fcfy >= 4 ? "up" : fcfy != null && fcfy < 2 ? "down" : "");
  }
  const nextEarningsEl = $("sum-next-earnings");
  if (nextEarningsEl) {
    const ne = d.profile.nextEarnings;
    if (ne) {
      // Calcular días hasta los earnings
      const daysUntil = Math.round((new Date(ne) - new Date()) / (1000 * 60 * 60 * 24));
      const label = daysUntil >= 0 ? `${ne} (en ${daysUntil}d)` : ne;
      nextEarningsEl.textContent = label;
      nextEarningsEl.style.color = daysUntil >= 0 && daysUntil <= 14 ? "var(--gold)" : "var(--text)";
    } else {
      nextEarningsEl.textContent = "Por confirmar";
      nextEarningsEl.style.color = "var(--muted)";
    }
  }

  // Trailing perf columns
  const setPerfCol = (colId, dirId, valId, val) => {
    const col = $(colId);
    const dir = $(dirId);
    const vSpan = $(valId);
    if (val == null) {
      col.style.display = "none";
      return;
    }
    col.style.display = "flex";
    const up = val >= 0;
    col.className = "perf-tag-col " + (up ? "green" : "red");
    dir.textContent = up ? "▲ Up" : "▼ Down";
    vSpan.textContent = fmtPct(val, 2, true);
  };
  setPerfCol("perf-col-1m", "perf-dir-1m", "perf-val-1m", d.current.perf1m);
  setPerfCol("perf-col-1y", "perf-dir-1y", "perf-val-1y", d.current.perf1y);
  setPerfCol("perf-col-ytd", "perf-dir-ytd", "perf-val-ytd", d.current.perfYtd);

  // Performance title badge
  $("stock-perf-val").textContent = d.current.perf1y != null ? `Performance: ${fmtPct(d.current.perf1y, 2, true)}` : "Performance: —";
  $("stock-perf-val").className = "perf-badge " + (d.current.perf1y >= 0 ? "up" : "down");

  // Reporte de Ganancias (Earnings Surprises)
  const earningsSec = $("earnings-section");
  if (earningsSec && d.earningsSurprises && d.earningsSurprises.length > 0) {
    earningsSec.style.display = "block";
    
    // Próximo reporte y estimación
    const nxtDt = d.profile.nextEarnings;
    const nxtEst = d.profile.nextEarningsEst;
    $("lbl-next-earnings-date").textContent = nxtDt ? nxtDt : "Por anunciar";
    $("lbl-next-earnings-est").textContent = nxtEst != null ? fmtPrice(nxtEst, cur) : "N/D";
    
    // Gráfico de sorpresas
    if (typeof chartEarningsSurprise === "function") {
      chartEarningsSurprise("ch-earnings-surprise", d.earningsSurprises);
    }
  } else if (earningsSec) {
    earningsSec.style.display = "none";
  }
}

function renderNews(news) {
  const container = $("news-container");
  const section = $("news-section");
  if (!container || !section) return;

  if (!news || news.length === 0) {
    section.style.display = "none";
    return;
  }
  section.style.display = "block";

  // Renderizar máximo 6 noticias
  const topNews = news.slice(0, 6);
  container.innerHTML = topNews.map(item => {
    const n = item.content || item; // Manejar si viene anidado en .content (formato de yfinance)
    let thumb = "";
    if (n.thumbnail && n.thumbnail.resolutions && n.thumbnail.resolutions.length > 0) {
      thumb = n.thumbnail.resolutions[0].url;
    } else if (n.thumbnail && n.thumbnail.originalUrl) {
      thumb = n.thumbnail.originalUrl;
    }
    
    const publisher = n.provider ? n.provider.displayName : "News";
    const date = n.pubDate ? new Date(n.pubDate).toLocaleDateString() : "";
    const link = n.clickThroughUrl ? n.clickThroughUrl.url : (n.canonicalUrl ? n.canonicalUrl.url : "#");

    return `
      <a href="${link}" target="_blank" style="display:flex; gap:16px; padding:12px; border:1px solid var(--border); border-radius:var(--radius); text-decoration:none; color:inherit; transition:all 0.2s; background:var(--surface);" class="hover-card">
        ${thumb ? `<img src="${thumb}" alt="thumbnail" style="width:100px; height:70px; object-fit:cover; border-radius:4px;">` : `<div style="width:100px; height:70px; background:var(--bg); border-radius:4px; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:10px;">Sin Imagen</div>`}
        <div style="display:flex; flex-direction:column; justify-content:space-between; flex:1;">
          <h4 style="margin:0; font-size:14px; font-weight:600; line-height:1.3; color:var(--text);">${n.title || 'Noticia'}</h4>
          <div style="font-size:11px; color:var(--muted); margin-top:6px; display:flex; justify-content:space-between;">
            <span style="font-weight:600; color:var(--primary);">${publisher}</span>
            <span>${date}</span>
          </div>
        </div>
      </a>
    `;
  }).join('');
}

/* -------------------------------------------- chart price summary */
function chartPriceSummary(d) {
  if (!d || !d.history || !d.history.price) return;
  const pts = d.history.price;
  
  // Filtrar según período en años
  const cutoff = Date.now() - (currentPeriodYears * 365 * 24 * 60 * 60 * 1000);
  const filteredPts = pts.filter(pt => pt[0] >= cutoff);
  
  chartPrice(d, "summary-price-chart", filteredPts);
}

// Configurar click handlers en los controles de gráficos de Summary
$("tg-area").onclick = () => {
  priceView.type = "area";
  $("tg-area").classList.add("active");
  $("tg-line").classList.remove("active");
  chartPriceSummary(state.data);
};
$("tg-line").onclick = () => {
  priceView.type = "line";
  $("tg-line").classList.add("active");
  $("tg-area").classList.remove("active");
  chartPriceSummary(state.data);
};
$("tg-sma-summary").onclick = () => {
  priceView.sma = !priceView.sma;
  $("tg-sma-summary").classList.toggle("active", priceView.sma);
  chartPriceSummary(state.data);
};
$("tg-log-summary").onclick = () => {
  priceView.log = !priceView.log;
  $("tg-log-summary").classList.toggle("active", priceView.log);
  chartPriceSummary(state.data);
};
$("tg-macd").onclick = () => {
  priceView.macd = !priceView.macd;
  $("tg-macd").classList.toggle("active", priceView.macd);
  chartPriceSummary(state.data);
};
$("tg-rsi").onclick = () => {
  priceView.rsi = !priceView.rsi;
  $("tg-rsi").classList.toggle("active", priceView.rsi);
  chartPriceSummary(state.data);
};

document.querySelectorAll(".chart-periods-style .period-btn").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".chart-periods-style .period-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentPeriodYears = parseFloat(btn.dataset.years);
    chartPriceSummary(state.data);
  };
});

$("btn-add-note").onclick = () => {
  location.hash = `#/analisis/${state.symbol}/qualitative`;
};
function updateCagrModal() {
  const principal = parseFloat($("cagr-in-principal").value) || 0;
  const rate = parseFloat($("cagr-in-rate").value) || 0;
  const years = parseInt($("cagr-in-years").value) || 1;
  $("cagr-lbl-years").textContent = years;

  const future = principal * Math.pow(1 + rate / 100, years);
  const gain = future - principal;
  const mult = principal > 0 ? (future / principal) : 1;

  $("cagr-res-future").textContent = `$${Math.round(future).toLocaleString()} USD`;
  $("cagr-res-gain").textContent = `${gain >= 0 ? "+" : ""}$${Math.round(gain).toLocaleString()} (${mult.toFixed(2)}x)`;
}

$("cagr-in-principal").oninput = updateCagrModal;
$("cagr-in-rate").oninput = updateCagrModal;
$("cagr-in-years").oninput = updateCagrModal;

$("btn-cagr-nav").onclick = () => {
  if (state.data && state.data.growthTable) {
    const revG = state.data.growthTable.find(g => g.metric === "Ingresos");
    if (revG && revG.cagr5 != null) {
      $("cagr-in-rate").value = revG.cagr5.toFixed(1);
    }
  }
  updateCagrModal();
  $("modal-cagr").classList.remove("hidden");
};
$("modal-cagr-close").onclick = () => {
  $("modal-cagr").classList.add("hidden");
};
$("btn-export-pdf").onclick = () => {
  window.print();
};

/* ----------------------------------------------------- avisos de datos */
function renderWarnings(warnings) {
  const box = $("data-warnings");
  if (!warnings || !warnings.length) return box.classList.add("hidden");
  
  const summary = $("warnings-summary");
  const list = $("warnings-list");
  
  if (summary && list) {
    // Nueva UI colapsable
    summary.innerHTML = `⚠️ ${warnings.length} aviso${warnings.length > 1 ? 's' : ''} de calidad de datos <span style="font-size:11px; font-weight:400; color:var(--muted); margin-left:4px;">(haz clic para expandir)</span>`;
    list.innerHTML = warnings.map(w => `<li style="margin-bottom:4px; line-height:1.5;">${w}</li>`).join("");
  } else {
    // Fallback para compatibilidad
    box.innerHTML = `<details><summary style="cursor:pointer; font-weight:700;">⚠️ ${warnings.length} aviso${warnings.length > 1 ? 's' : ''} de calidad de datos</summary><ul style="margin:6px 0 0 18px; padding:0;">${warnings.map(w => `<li>${w}</li>`).join("")}</ul></details>`;
  }
  box.classList.remove("hidden");
}

/* ----------------------------------------------- seguridad del dividendo */
function renderDividendSafety(ds) {
  const box = $("div-safety");
  if (!ds) return box.classList.add("hidden");
  const chip = (label, val, term) =>
    `<span class="ds-chip">${termify(label, term)}: <b>${val}</b></span>`;
  box.innerHTML =
    `<span class="ds-chip ds-${ds.level}"><b>${ds.label}</b></span>` +
    chip("Racha pagando", `${ds.payingStreak} años`, "streak") +
    chip("Racha subiendo", `${ds.growthStreak} años`, "streak") +
    (ds.payoutFcf != null ? chip("Payout s/FCF", fmtPct(ds.payoutFcf, 0), "payoutfcf") : "") +
    (ds.payoutEps != null ? chip("Payout s/utilidad", fmtPct(ds.payoutEps, 0), "payout") : "");
  box.classList.remove("hidden");
}

/* ------------------------------------------------- notas cualitativas */
const MOATS = [
  ["marca", "Marca poderosa", "Puede subir precios sin perder clientes (Coca-Cola, Apple)"],
  ["costos", "Costos más bajos", "Produce más barato que cualquier rival (Costco, GEICO)"],
  ["red", "Efecto de red", "Cada usuario nuevo hace el servicio más valioso (Visa, MercadoLibre)"],
  ["switching", "Costos de cambio", "Cambiarse a la competencia duele (bancos, software empresarial)"],
  ["intangibles", "Patentes / licencias", "Protección legal que bloquea competidores (farmacéuticas)"],
  ["escala", "Escala eficiente", "El mercado solo da para uno o dos jugadores (ferrocarriles)"],
];
let noteTimer = null;
let noteSymbol = null;

async function loadNotes(symbol) {
  noteSymbol = symbol;
  const note = await (await fetch(`/api/notes/${encodeURIComponent(symbol)}`)).json();
  $("moat-checks").innerHTML = MOATS.map(([id, label, desc]) => `
    <label class="moat ${note.moats.includes(id) ? "on" : ""}" title="${desc}">
      <input type="checkbox" value="${id}" ${note.moats.includes(id) ? "checked" : ""}> ${label}
    </label>`).join("");
  $("note-thesis").value = note.thesis || "";
  $("note-risks").value = note.risks || "";

  $("moat-checks").querySelectorAll("input").forEach(cb =>
    cb.onchange = () => { cb.closest(".moat").classList.toggle("on", cb.checked); saveNotes(); });
  $("note-thesis").oninput = saveNotesDebounced;
  $("note-risks").oninput = saveNotesDebounced;
}

function saveNotesDebounced() {
  clearTimeout(noteTimer);
  $("note-status").textContent = "escribiendo…";
  noteTimer = setTimeout(saveNotes, 900);
}

async function saveNotes() {
  if (!noteSymbol) return;
  const moats = [...$("moat-checks").querySelectorAll("input:checked")].map(cb => cb.value);
  await fetch(`/api/notes/${encodeURIComponent(noteSymbol)}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thesis: $("note-thesis").value, risks: $("note-risks").value, moats }),
  });
  $("note-status").textContent = "guardado ✓";
}

/* --------------------------------------------- buffett scorecard */
function renderBuffettScorecard(sc) {
  const el = $("scorecard-details");
  if (el) {
    el.innerHTML = sc.checks.map(ch => {
      const cls = ch.passed === true ? "passed" : ch.passed === false ? "failed" : "na";
      const icon = ch.passed === true ? "✓" : ch.passed === false ? "✗" : "–";
      let val = "";
      if (ch.value != null) {
        if (ch.fmt === "pct") val = fmtPct(ch.value);
        else if (ch.fmt === "x") val = fmtRatio(ch.value, 2);
        else if (ch.fmt === "$") val = fmtNum(ch.value, 2);
        else if (ch.fmt === "años") val = ch.value + " años con datos";
        else val = String(ch.value);
        val = ` · <b>${val}</b>`;
      }
      return `<div class="check ${cls}" title="${ch.desc}">
        <span class="icon">${icon}</span>
        <div><div class="name">${ch.name}</div><div class="val">${ch.desc}${val}</div></div>
      </div>`;
    }).join("");
  }

  // Ahora pintamos en la pestaña Rating si existe
  const listEl = $("scorecard-list");
  if (listEl) {
    $("scorecard-donut").textContent = `${sc.passed}/${sc.evaluated}`;
    const pct = sc.evaluated > 0 ? (sc.passed / sc.evaluated) : 0;
    
    // Animar SVG donut fill ring con transición suave
    const fillEl = $("donut-fill");
    if (fillEl) {
      const circ = 263.89;
      // Primero asegurar que esté en 0 para disparar animación
      fillEl.style.transition = "none";
      fillEl.style.strokeDashoffset = circ;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          fillEl.style.transition = "stroke-dashoffset 0.9s cubic-bezier(0.4,0,0.2,1), stroke 0.4s ease";
          fillEl.style.strokeDashoffset = circ * (1 - pct);
          fillEl.style.stroke = pct >= 0.8 ? "#10b981" : pct >= 0.5 ? "#f59e0b" : "#ef4444";
        });
      });
    }

    let desc = "";
    if (pct >= 0.8) desc = "Excelente solidez de inversión. Cumple con la mayoría de criterios de Buffett.";
    else if (pct >= 0.5) desc = "Solidez moderada. Cumple con algunos criterios clave de Buffett, revisar con cautela.";
    else desc = "Solidez débil. Pasa muy pocos criterios de Buffett, alta precaución recomendada.";
    $("scorecard-desc").textContent = desc;

    listEl.innerHTML = sc.checks.map(c => {
      const isPass = c.passed === true;
      const isFail = c.passed === false;
      let badgeHtml = isPass
        ? `<div class="scorecard-item-badge pass">✓</div>`
        : isFail
          ? `<div class="scorecard-item-badge fail">✗</div>`
          : `<div class="scorecard-item-badge na">?</div>`;

      let valStr = "—";
      if (c.value != null) {
        if (c.fmt === "pct") valStr = fmtPct(c.value);
        else if (c.fmt === "x") valStr = `${c.value.toFixed(2)}x`;
        else if (c.fmt === "años") valStr = `${c.value} años`;
        else if (c.fmt === "$") valStr = fmtPrice(c.value, state.data.profile.currency);
        else valStr = String(c.value);
      }

      return `
        <div class="scorecard-item-row">
          <div class="scorecard-item-left">
            ${badgeHtml}
            <div class="scorecard-item-info">
              <span class="scorecard-item-name">${c.name}</span>
              <span class="scorecard-item-desc">${c.desc}</span>
            </div>
          </div>
          <div class="scorecard-item-right">
            <span class="scorecard-item-value">${valStr}</span>
          </div>
        </div>
      `;
    }).join("");
  }
}

/* ----------------------------------------------------- tabla crecimiento */
function renderGrowthTable(d) {
  const rows = d.growthTable || [];
  const card = $("growth-card");
  if (rows.length < 2) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const cell = v => v == null ? `<td class="num muted">—</td>`
    : `<td class="num ${v >= 0 ? "up" : "down"}"><b>${fmtPct(v, 1, true)}</b></td>`;
  $("growth-table").innerHTML = `
    <thead><tr><th>Métrica</th><th class="num">Último año</th>
      <th class="num">${termify("CAGR 1A", "cagr")}</th><th class="num">${termify("CAGR 3A", "cagr")}</th>
      <th class="num">${termify("CAGR 5A", "cagr")}</th><th class="num">${termify("CAGR 10A", "cagr")}</th></tr></thead>
    <tbody>${rows.map(r => `
      <tr>
        <td>${r.metric}</td>
        <td class="num">${r.metric.includes("EPS") || r.metric.includes("Dividendo") ? fmtNum(r.current, 2) : fmtBig(r.current, d.profile.currency)}</td>
        ${cell(r.cagr1)}${cell(r.cagr3)}${cell(r.cagr5)}${cell(r.cagr10)}
      </tr>`).join("")}</tbody>`;
}

/* ------------------------------------------------------------ watch star */
function setStarState(inWatchlist) {
  const b = $("btn-watch");
  b.classList.toggle("active", !!inWatchlist);
  b.innerHTML = inWatchlist ? "★ Siguiendo" : "☆ Seguir";
  b.title = inWatchlist ? "Quitar de la watchlist" : "Agregar a watchlist (objetivo: MoS ≥ 25%)";
}

$("btn-watch").addEventListener("click", async () => {
  if (!state.data) return;
  const sym = state.data.symbol;
  if ($("btn-watch").classList.contains("active")) {
    await wlRemove(sym);
    setStarState(false);
  } else {
    await wlAdd(sym, 25);
    setStarState(true);
  }
  state.data.inWatchlist = !state.data.inWatchlist;
  refreshSidebar();
});

/* ------------------------------------------------- valoración + DCF live */
function dcfJs(inp, growth, discount, terminal) {
  if (!inp || !inp.baseFcf || inp.baseFcf <= 0 || !inp.shares || discount <= terminal) return null;
  let fcf = inp.baseFcf, pv = 0;
  const years = inp.years, fadeStart = inp.fadeStart;
  for (let yr = 1; yr <= years; yr++) {
    let g = growth;
    if (yr >= fadeStart) {
      const frac = (yr - fadeStart + 1) / (years - fadeStart + 1);
      g = growth + (terminal - growth) * frac;
    }
    fcf *= 1 + g;
    pv += fcf / Math.pow(1 + discount, yr);
  }
  pv += (fcf * (1 + terminal) / (discount - terminal)) / Math.pow(1 + discount, years);
  return (pv + (inp.netCash || 0)) / inp.shares;
}

function renderValuationCard(d) {
  const inp = d.valuation.dcfInputs;
  if (!inp) return;
  if (!$("sl-growth")) return; // Salir si los sliders no están presentes en el DOM actual
  const lsKey = `dcf_${d.symbol}`;
  const sliders = { growth: $("sl-growth"), discount: $("sl-discount"), terminal: $("sl-terminal") };

  const setSliders = (g, r, t) => {
    sliders.growth.value = (g * 100).toFixed(1);
    sliders.discount.value = (r * 100).toFixed(2);
    sliders.terminal.value = (t * 100).toFixed(2);
  };
  setSliders(inp.growth, inp.discount, inp.terminal);

  // restaura supuestos guardados para esta acción
  try {
    const saved = JSON.parse(localStorage.getItem(lsKey));
    if (saved && isFinite(saved.g)) setSliders(saved.g, saved.r, saved.t);
  } catch { /* sin supuestos guardados */ }

  const update = (save = true) => {
    const g = parseFloat(sliders.growth.value) / 100;
    const r = parseFloat(sliders.discount.value) / 100;
    const t = parseFloat(sliders.terminal.value) / 100;
    $("lbl-growth").textContent = fmtPct(g * 100, 1);
    $("lbl-discount").textContent = fmtPct(r * 100, 2);
    $("lbl-terminal").textContent = fmtPct(t * 100, 2);
    renderModels(d, dcfJs(inp, g, r, t));
    renderSensitivity(d, g, r, t);
    if (save) localStorage.setItem(lsKey, JSON.stringify({ g, r, t }));
  };
  Object.values(sliders).forEach(s => s.oninput = () => update(true));
  $("btn-reset-dcf").onclick = () => {
    localStorage.removeItem(lsKey);
    setSliders(inp.growth, inp.discount, inp.terminal);
    update(false);
    toast("Supuestos restaurados a los valores estimados");
  };
  update(false);

  // sin modelo DCF (ej: financieras) los sliders y la sensibilidad no aplican
  const hasDcf = d.valuation.models.some(m => m.id === "dcf");
  const slidersEl = document.querySelector(".sliders");
  if (slidersEl) slidersEl.style.display = hasDcf ? "" : "none";
  if ($("sensitivity")) $("sensitivity").classList.toggle("hidden", !hasDcf);
  if ($("implied-growth")) $("implied-growth").classList.toggle("hidden", !hasDcf || d.valuation.impliedGrowth == null);
  if (!hasDcf && d.valuation.models.length && $("models-table")) {
    $("models-table").insertAdjacentHTML("beforeend",
      `<p class="muted" style="font-size:12.5px;margin-top:6px">El DCF de flujo de caja no aplica a financieras: su FCF contable no refleja la economía del negocio.</p>`);
  }

  // reverse DCF: qué crecimiento descuenta el precio actual
  const ig = d.valuation.impliedGrowth;
  if (hasDcf && ig != null && $("implied-growth")) {
    const est = inp.growth * 100;
    const label = ig <= -20 ? "una contracción de -20% o peor" : ig >= 60 ? "más de +60% anual" : `<b>${fmtPct(ig, 1, true)}</b> anual`;
    const judge = ig >= 60 || ig - est > 8
      ? `<span class="down">muy exigente vs el ${fmtPct(est, 1)} estimado — poco margen para decepciones.</span>`
      : ig <= -20 || est - ig > 8
        ? `<span class="up">pesimista vs el ${fmtPct(est, 1)} estimado — las expectativas son bajas.</span>`
        : `razonable frente al ${fmtPct(est, 1)} estimado.`;
    $("implied-growth").innerHTML =
      `<b>Reverse DCF:</b> para justificar el precio actual, el FCF debe crecer ${label} durante la próxima década (descuento 10%). Eso es ${judge}`;
  }

  const v = d.valuation;
  const yc = $("yield-compare");
  if (yc) {
    if (v.earningsYield != null && v.bond10y != null) {
      const diff = v.earningsYield - v.bond10y;
      yc.innerHTML =
        `Rendimiento de utilidades (earnings yield): <b>${fmtPct(v.earningsYield, 2)}</b> vs bono EE.UU. 10 años: <b>${fmtPct(v.bond10y, 2)}</b> — ` +
        (diff > 0
          ? `la acción rinde <b class="up">${fmtPct(diff, 2)}</b> más que el bono.`
          : `la acción rinde <b class="down">${fmtPct(Math.abs(diff), 2)}</b> menos que el bono (exige crecimiento futuro).`);
      yc.classList.remove("hidden");
    } else {
      yc.classList.add("hidden");
    }
  }
}

function renderModels(d, dcfLive) {
  if (!$("models-table")) return;
  const price = d.quote.price;
  const cur = d.profile.currency;
  const models = d.valuation.models.map(m => ({ ...m }));
  const dcfModel = models.find(m => m.id === "dcf");
  if (dcfModel && dcfLive != null) {
    dcfModel.fair = dcfLive;
    dcfModel.upside = (dcfLive / price - 1) * 100;
  }
  let consensus = null, mos = null;
  if (models.length) {
    const w = models.reduce((s, m) => s + m.weight, 0);
    consensus = models.reduce((s, m) => s + m.fair * m.weight, 0) / w;
    mos = (consensus / price - 1) * 100;
  }

  const termKey = { dcf: "dcf", reversion: "reversion", graham: "graham", graham_intrinsic: "graham", epv: "epv" };
  const rows = models.map(m => `
    <tr>
      <td>${termify(m.name, termKey[m.id])}</td>
      <td class="fair">${fmtPrice(m.fair, cur)}</td>
      <td class="upside ${pctClass(m.upside)}">${fmtPct(m.upside, 1, true)}</td>
    </tr>`).join("");

  $("models-table").innerHTML = models.length ? `
    <table class="models-table">
      <tbody>
        ${rows}
        <tr class="consensus-row">
          <td>Valor intrínseco (consenso ponderado)</td>
          <td class="fair">${fmtPrice(consensus, cur)}</td>
          <td class="upside ${pctClass(mos)}">${fmtPct(mos, 1, true)}</td>
        </tr>
        <tr><td class="muted">Precio actual</td><td class="fair muted">${fmtPrice(price, cur)}</td><td></td></tr>
      </tbody>
    </table>` : `<p class="muted">No hay datos suficientes para los modelos de valoración (EPS o FCF negativos).</p>`;

  if (mos != null) {
    renderGauge(mos);
    
    // También actualizamos los elementos de Summary
    const consensusEl = $("fv-consensus-val");
    if (consensusEl) consensusEl.textContent = fmtPrice(consensus, cur);
    const mosEl = $("fv-mos-pct");
    if (mosEl) {
      mosEl.innerHTML = `Margin of Safety: <b class="${mos >= 0 ? "up" : "down"}">${fmtPct(mos, 1, true)}</b>`;
    }
  }
}

// Conservamos una función renderGauge simulada/vacía por compatibilidad con código existente si fuese necesario
function renderGauge(mos) {
  // En el nuevo Summary el progreso se muestra mediante textos y el veredicto badge, no requiere canvas gauge circular
}

/* -------------------------------------------------- matriz sensibilidad */
function renderSensitivity(d, g, r, t) {
  if (!$("sensitivity-table")) return;
  const inp = d.valuation.dcfInputs;
  const price = d.quote.price;
  const cur = d.profile.currency;
  if (!inp || !inp.baseFcf || inp.baseFcf <= 0) return;

  const growths = [-4, -2, 0, 2, 4].map(dx => g + dx / 100).filter(x => x >= -0.05);
  const discounts = [-2, -1, 0, 1, 2].map(dx => r + dx / 100).filter(x => x > t + 0.01);

  let html = `<table class="sens-table"><thead><tr><th>crec. \\ desc.</th>` +
    discounts.map(dc => `<th class="num ${Math.abs(dc - r) < 1e-9 ? "cur" : ""}">${fmtPct(dc * 100, 1)}</th>`).join("") +
    `</tr></thead><tbody>`;
  for (const gr of growths) {
    html += `<tr><th class="${Math.abs(gr - g) < 1e-9 ? "cur" : ""}">${fmtPct(gr * 100, 1)}</th>`;
    for (const dc of discounts) {
      const fv = dcfJs(inp, gr, dc, t);
      const isCur = Math.abs(gr - g) < 1e-9 && Math.abs(dc - r) < 1e-9;
      if (fv == null) { html += `<td class="num muted">—</td>`; continue; }
      const cls = fv >= price * 1.25 ? "s-buy" : fv >= price ? "s-ok" : fv >= price * 0.8 ? "s-warn" : "s-bad";
      html += `<td class="num ${cls} ${isCur ? "cur" : ""}">${fmtPrice(fv, cur)}</td>`;
    }
    html += `</tr>`;
  }
  $("sensitivity-table").innerHTML = html + `</tbody></table>`;
}

/* --------------------------------------------------------- tabla ratios */
function renderRatiosGrid(d) {
  const r = d.ratios;
  if (!r) return;
  const cur = d.profile.currency;
  const px = d.quote.price;

  // Actualizar títulos de símbolo
  $("th-sym-left").textContent = d.symbol;
  $("th-sym-5y-left").textContent = `${d.symbol} 5Y Avg.`;
  $("th-sym-right").textContent = d.symbol;
  $("th-sym-5y-right").textContent = `${d.symbol} 5Y Avg.`;
  $("th-sym-right3").textContent = d.symbol;
  $("th-sym-5y-right3").textContent = `${d.symbol} 5Y Avg.`;

  // Helper para formato de diferencias porcentuales
  const fmtDiff = (comp, compRef) => {
    if (comp == null || compRef == null || compRef === 0) return "—";
    const diff = ((comp - compRef) / Math.abs(compRef)) * 100;
    const up = diff >= 0;
    const sign = up ? "↑" : "↓";
    const absDiff = Math.abs(diff);
    return {
      text: `${sign} ${absDiff.toFixed(2)}%`,
      val: diff
    };
  };

  const populateRowLeft = (rowId, metricData, isMarginOrYield = false) => {
    const row = $(rowId);
    if (!row) return;
    const compVal = metricData.val;
    const sectVal = metricData.sector;
    const avg5yVal = metricData.avg5y;

    const compCell = row.querySelector(".val-company");
    const sectCell = row.querySelector(".val-sector");
    const diffSectCell = row.querySelector(".val-diff-sector");
    const avg5yCell = row.querySelector(".val-5y");
    const diff5yCell = row.querySelector(".val-diff-5y");

    compCell.textContent = compVal != null ? (isMarginOrYield ? fmtPct(compVal, 2) : compVal.toFixed(2)) : "—";
    sectCell.textContent = sectVal != null ? (isMarginOrYield ? fmtPct(sectVal, 2) : sectVal.toFixed(2)) : "—";
    avg5yCell.textContent = avg5yVal != null ? (isMarginOrYield ? fmtPct(avg5yVal, 2) : avg5yVal.toFixed(2)) : "—";

    // Diferencia vs Sector
    const diffSec = fmtDiff(compVal, sectVal);
    if (diffSec !== "—") {
      diffSectCell.textContent = diffSec.text;
      const isGreen = isMarginOrYield ? diffSec.val >= 0 : diffSec.val <= 0;
      diffSectCell.className = "text-right " + (isGreen ? "up" : "down");
    } else {
      diffSectCell.textContent = "—";
      diffSectCell.className = "text-right";
    }

    // Diferencia vs 5Y Avg
    const diff5y = fmtDiff(compVal, avg5yVal);
    if (diff5y !== "—") {
      diff5yCell.textContent = diff5y.text;
      const isGreen = isMarginOrYield ? diff5y.val >= 0 : diff5y.val <= 0;
      diff5yCell.className = "text-right " + (isGreen ? "up" : "down");
    } else {
      diff5yCell.textContent = "—";
      diff5yCell.className = "text-right";
    }
  };

  const populateRowRight = (rowId, metricData, isRoe = false, isMultipleOrDebt = false) => {
    const row = $(rowId);
    if (!row) return;
    const compVal = metricData.val;
    const avg5yVal = metricData.avg5y;

    const compCell = row.querySelector(".val-company");
    const avg5yCell = row.querySelector(".val-5y");
    const diffCell = row.querySelector(".val-diff");

    compCell.textContent = compVal != null ? (isRoe ? fmtPct(compVal, 2) : compVal.toFixed(2)) : "—";
    avg5yCell.textContent = avg5yVal != null ? (isRoe ? fmtPct(avg5yVal, 2) : avg5yVal.toFixed(2)) : "—";

    const diff = fmtDiff(compVal, avg5yVal);
    if (diff !== "—") {
      diffCell.textContent = diff.text;
      const isGreen = isMultipleOrDebt ? diff.val <= 0 : (isRoe ? diff.val >= 0 : diff.val >= 0);
      diffCell.className = "text-right " + (isGreen ? "up" : "down");
    } else {
      diffCell.textContent = "—";
      diffCell.className = "text-right";
    }
  };

  // Rellenar tabla izquierda
  populateRowLeft("row-tbl-pe", r.pe);
  populateRowLeft("row-tbl-pb", r.pb);
  populateRowLeft("row-tbl-ps", r.ps);
  populateRowLeft("row-tbl-pcf", r.pcf);
  populateRowLeft("row-tbl-margin", r.netMargin, true);
  populateRowLeft("row-tbl-yield", r.divYield, true);

  // Rellenar tabla derecha
  populateRowRight("row-tbl-peg", r.peg);
  populateRowRight("row-tbl-quick", r.quick);
  populateRowRight("row-tbl-cash", r.cash);
  populateRowRight("row-tbl-de", r.debtToEquity, false, true);
  populateRowRight("row-tbl-roe", r.roe, true);
  populateRowRight("row-tbl-fcfps", r.fcfPs);

  // Rellenar tabla 3 (Calidad y Eficiencia)
  populateRowRight("row-tbl-roc", r.roc, true);
  populateRowRight("row-tbl-evebitda", r.evEbitda, false, true);
  populateRowRight("row-tbl-grossm", r.grossMargin, true);
  populateRowRight("row-tbl-opm", r.opMargin, true);
  populateRowRight("row-tbl-roa", r.roa, true);

  // Rellenar checks superiores
  const updateCheckRow = (rowId, lblId, valId, iconId, pass, valText, labelPrefix) => {
    if (labelPrefix) {
      $(lblId).textContent = labelPrefix;
    }
    $(valId).textContent = valText;
    const iconCell = $(iconId);
    iconCell.textContent = pass ? "👍" : "👎";
    iconCell.style.color = pass ? "#10b981" : "#ef4444";
  };

  // 1. P/E Ratio < Sector PE
  const pePass = r.pe.val != null && r.pe.sector != null && r.pe.val < r.pe.sector;
  updateCheckRow("chk-pe-row", "chk-pe-lbl", "chk-pe-val", "chk-pe-icon", pePass, 
                 r.pe.val != null ? r.pe.val.toFixed(2) : "—", 
                 `P/E Ratio < ${r.pe.sector != null ? r.pe.sector.toFixed(2) : '—'}`);

  // 2. Current Ratio 1-3
  const currRatio = d.current.currentRatio;
  const currPass = currRatio != null && currRatio >= 1.0 && currRatio <= 3.0;
  updateCheckRow("chk-curr-row", null, "chk-curr-val", "chk-curr-icon", currPass,
                 currRatio != null ? currRatio.toFixed(2) : "—");

  // 3. Debt Ratio < 0.6
  let debtRatio = null;
  if (d.annuals && d.annuals.length > 0) {
    const lastA = d.annuals[d.annuals.length - 1];
    if (lastA.totalDebt != null && lastA.assets) {
      debtRatio = lastA.totalDebt / lastA.assets;
    }
  }
  const debtPass = debtRatio != null && debtRatio < 0.6;
  updateCheckRow("chk-debt-row", null, "chk-debt-val", "chk-debt-icon", debtPass,
                 debtRatio != null ? debtRatio.toFixed(2) : "—");

  // 4. Payout Ratio < 50% (N/A si la empresa no paga dividendo)
  const divYield = d.current.divYield;
  const payoutRaw = d.current.payout;
  const hasDividend = divYield != null && divYield > 0.001;
  const payout = payoutRaw != null ? payoutRaw * 100 : 0.0;
  let payoutPass, payoutValText;
  if (!hasDividend) {
    payoutPass = null; // N/A
    payoutValText = "Sin dividendo";
  } else {
    payoutPass = payout < 50.0;
    payoutValText = fmtPct(payout, 0);
  }
  updateCheckRow("chk-payout-row", null, "chk-payout-val", "chk-payout-icon", payoutPass,
                 payoutValText);
  // Actualizar icono para N/A
  if (!hasDividend) {
    $("chk-payout-icon").textContent = "—";
    $("chk-payout-icon").style.color = "var(--muted)";
  }

  // 5. ROIC Avg 5 Yrs > 10%
  const roicAvg = r.roic10yAvg;
  const roicPass = roicAvg != null && roicAvg > 10.0;
  updateCheckRow("chk-roic-row", null, "chk-roic-val", "chk-roic-icon", roicPass,
                 roicAvg != null ? fmtPct(roicAvg, 2) : "—");

  // 6. Revenue Growth (CAGR 5 Yrs)
  let revCAGR = null;
  const revGrowth = d.growthTable.find(g => g.metric === "Ingresos");
  if (revGrowth && revGrowth.cagr5 != null) {
    revCAGR = revGrowth.cagr5;
  }
  const revPass = revCAGR != null && revCAGR > 0;
  updateCheckRow("chk-revg-row", "chk-revg-lbl", "chk-revg-val", "chk-revg-icon", revPass,
                 revCAGR != null ? fmtPct(revCAGR, 1) : "—",
                 "Revenue Growth 5 Yrs (CAGR)");

  // 7. Net Income Growth (CAGR 5 Yrs)
  let niCAGR = null;
  const niGrowth = d.growthTable.find(g => g.metric === "Utilidad neta");
  if (niGrowth && niGrowth.cagr5 != null) {
    niCAGR = niGrowth.cagr5;
  }
  const niPass = niCAGR != null && niCAGR > 0;
  updateCheckRow("chk-netg-row", "chk-netg-lbl", "chk-netg-val", "chk-netg-icon", niPass,
                 niCAGR != null ? fmtPct(niCAGR, 1) : "—",
                 "Net Income Growth 5 Yrs (CAGR)");

  // 8. FCF Growth (CAGR 5 Yrs)
  let fcfCAGR = null;
  const fcfGrowth = d.growthTable.find(g => g.metric === "Flujo de caja libre");
  if (fcfGrowth && fcfGrowth.cagr5 != null) {
    fcfCAGR = fcfGrowth.cagr5;
  }
  const fcfPass = fcfCAGR != null && fcfCAGR > 0;
  updateCheckRow("chk-fcfg-row", "chk-fcfg-lbl", "chk-fcfg-val", "chk-fcfg-icon", fcfPass,
                 fcfCAGR != null ? fmtPct(fcfCAGR, 1) : "—",
                 "Free Cash Flow Growth 5 Yrs (CAGR)");
}

/* -------------------------------------------------- sidebar favoritos */
const SB_KEY = "sb_hidden";

function sbSetHidden(hidden) {
  $("sidebar").classList.toggle("hidden", hidden);
  $("sb-open").classList.toggle("hidden", !hidden);
  document.body.classList.toggle("with-sidebar", !hidden);
  localStorage.setItem(SB_KEY, hidden ? "1" : "0");
  requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
}

function sparkSvg(values, color) {
  if (!values || values.length < 2) return "";
  const w = 72, h = 26, min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) =>
    `${(i / (values.length - 1) * w).toFixed(1)},${(h - 2 - (v - min) / span * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5"/></svg>`;
}

function sparkSvgSmall(values, color) {
  if (!values || values.length < 2) return "";
  const w = 36, h = 14, min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) =>
    `${(i / (values.length - 1) * w).toFixed(1)},${(h - 2 - (v - min) / span * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.2"/></svg>`;
}

function renderEpsEstimatesChart(est) {
  const container = $("est-eps-chart");
  if (!container || !est) return;
  const rows = est.earningsEstimate || [];
  if (!rows.length) { container.innerHTML = '<p class="muted" style="text-align:center; padding:40px;">Sin datos de estimaciones EPS.</p>'; return; }

  const periodLabel = p => p === '0q' ? 'Trim. Actual' : p === '+1q' ? 'Próx. Trimestre' : p === '0y' ? 'Año Actual' : 'Próx. Año';
  const labels = rows.map(r => periodLabel(r.period));
  const estAvg = rows.map(r => r.avg != null ? parseFloat(r.avg.toFixed(2)) : null);
  const yearAgo = rows.map(r => r.yearAgoEps != null ? parseFloat(r.yearAgoEps.toFixed(2)) : null);
  const estHigh = rows.map(r => r.high != null ? parseFloat(r.high.toFixed(2)) : null);
  const estLow = rows.map(r => r.low != null ? parseFloat(r.low.toFixed(2)) : null);

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#475569';
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';

  let ch = charts['est-eps-chart'];
  if (!ch) {
    ch = echarts.init(container, null, { renderer: 'svg' });
    charts['est-eps-chart'] = ch;
  }

  ch.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['EPS Estimado (consenso)', 'EPS Año Anterior'], textStyle: { color: textColor, fontSize: 11 }, top: 4 },
    grid: { left: 40, right: 20, top: 40, bottom: 30, containLabel: false },
    xAxis: { type: 'category', data: labels, axisLabel: { color: textColor, fontSize: 11 }, axisLine: { lineStyle: { color: gridColor } } },
    yAxis: { type: 'value', axisLabel: { color: textColor, fontSize: 11, formatter: v => '$' + v.toFixed(2) }, splitLine: { lineStyle: { color: gridColor } } },
    series: [
      {
        name: 'EPS Estimado (consenso)',
        type: 'bar',
        data: estAvg,
        itemStyle: { color: '#10b981', borderRadius: [4,4,0,0] },
        label: { show: true, position: 'top', formatter: v => v.value != null ? '$' + v.value.toFixed(2) : '', fontSize: 10, color: textColor },
        markArea: {
          silent: true,
          data: rows.map((r, i) => estLow[i] != null && estHigh[i] != null ? [
            { xAxis: labels[i], yAxis: estLow[i], itemStyle: { color: 'rgba(16,185,129,0.1)' } },
            { xAxis: labels[i], yAxis: estHigh[i] }
          ] : null).filter(Boolean)
        }
      },
      {
        name: 'EPS Año Anterior',
        type: 'bar',
        data: yearAgo,
        itemStyle: { color: '#94a3b8', borderRadius: [4,4,0,0] },
        label: { show: true, position: 'top', formatter: v => v.value != null ? '$' + v.value.toFixed(2) : '', fontSize: 10, color: textColor }
      }
    ]
  }, true);
}

async function refreshSidebar() {
  try {
    const { symbols } = await (await fetch("/api/watchlist/symbols")).json();
    const list = $("sb-list");
    if (!symbols.length) {
      list.innerHTML = `<p class="muted" style="padding:12px;font-size:12.5px">Agrega acciones con ☆ Seguir para verlas aquí.</p>`;
      return;
    }
    const { quotes } = await (await fetch(`/api/quotes?symbols=${symbols.join(",")}`)).json();
    list.innerHTML = quotes.map(q => {
      const up = q.changePct >= 0;
      const color = up ? "#10b981" : "#ef4444";
      return `<div class="sb-item" onclick="go('${q.symbol}')">
        <div class="sb-sym">${q.symbol}</div>
        ${sparkSvg(q.spark, color)}
        <div class="sb-quote">
          <div class="sb-price">${fmtNum(q.price, q.price >= 1000 ? 0 : 2)}</div>
          <div class="sb-chg ${up ? "up" : "down"}">${fmtPct(q.changePct, 2, true)}</div>
        </div>
      </div>`;
    }).join("");
  } catch { /* red caída */ }
}

$("sb-close").addEventListener("click", () => sbSetHidden(true));
$("sb-open").addEventListener("click", () => { sbSetHidden(false); refreshSidebar(); });

sbSetHidden(localStorage.getItem(SB_KEY) === "1");
refreshSidebar();
setInterval(refreshSidebar, 120000);

/* ----------------------------------------------------- estimates & insiders */
function renderGrowthEstimatesGrid(grid) {
  const subtextEl = $("est-growth-subtext");
  const theadEl = $("est-growth-thead");
  const tbodyEl = $("est-growth-tbody");

  if (!grid || !grid.years || !grid.rows || !grid.rows.length) {
    if (tbodyEl) tbodyEl.innerHTML = '<tr><td colspan="12" style="text-align:center; padding:20px; color:var(--muted);">Sin datos de estimaciones de crecimiento</td></tr>';
    return;
  }

  const curr = grid.currency || state.data?.profile?.currency || "USD";
  if (subtextEl) {
    subtextEl.textContent = `Currency in ${curr}. All numbers in millions.`;
  }

  // Header row
  let headHtml = `<tr>
    <th style="text-align:left; font-weight:700; min-width:140px; padding:12px 16px; background:var(--panel);">Year</th>`;
  grid.years.forEach(y => {
    const isProjected = String(y).endsWith('E');
    headHtml += `<th style="text-align:right; padding:12px 14px; font-weight:700; background:var(--panel); ${isProjected ? 'color:var(--primary);' : ''}">${y}</th>`;
  });
  headHtml += `<th style="text-align:right; padding:12px 16px; font-weight:700; background:var(--panel); color:var(--text);">Growth</th></tr>`;
  if (theadEl) theadEl.innerHTML = headHtml;

  // Body rows
  let bodyHtml = "";
  grid.rows.forEach(row => {
    const isFwdPe = row.label === "Forward PE";
    
    // Main Metric Row
    bodyHtml += `<tr class="growth-row-main" style="border-top:1px solid var(--border);">
      <td style="font-weight:700; color:var(--text); padding:12px 16px;">${row.label}</td>`;
    
    row.values.forEach((v, idx) => {
      const isProj = String(grid.years[idx]).endsWith('E');
      let formatted = "—";
      if (v != null) {
        if (isFwdPe) {
          formatted = Number(v).toFixed(2);
        } else if (row.label === "EPS" || row.label === "Dividends") {
          formatted = Number(v).toFixed(2);
        } else {
          formatted = Number(v).toLocaleString("en-US");
        }
      }
      bodyHtml += `<td class="num" style="padding:12px 14px; font-weight:600; ${isProj ? 'color:var(--text); font-weight:700;' : ''}">${formatted}</td>`;
    });

    // Growth / CAGR column for main row
    let cagrVal = "—";
    if (!isFwdPe && row.cagr != null) {
      cagrVal = fmtPct(row.cagr, 2, false);
    }
    bodyHtml += `<td class="num" style="padding:12px 16px; font-weight:700; color:var(--muted);">${isFwdPe ? '—' : ''}</td></tr>`;

    // YoY Sub-Row (if not Forward PE)
    if (!isFwdPe) {
      bodyHtml += `<tr class="growth-row-yoy" style="background:rgba(255,255,255,0.015); font-size:12px;">
        <td style="color:var(--muted); padding:4px 16px 12px 24px; font-weight:500;">% Change YoY</td>`;
      
      row.yoy.forEach(yoyVal => {
        if (yoyVal == null) {
          bodyHtml += `<td class="num" style="padding:4px 14px 12px 14px; color:var(--muted);">—</td>`;
        } else {
          const colorClass = yoyVal >= 0 ? 'up' : 'down';
          const sign = yoyVal > 0 ? '' : '';
          bodyHtml += `<td class="num ${colorClass}" style="padding:4px 14px 12px 14px; font-weight:600;">${sign}${yoyVal.toFixed(2)}%</td>`;
        }
      });

      // Growth column for YoY sub-row
      const cagrFormatted = row.cagr != null ? `${row.cagr.toFixed(2)}%` : '—';
      const cagrClass = row.cagr != null && row.cagr >= 0 ? 'up' : 'down';
      bodyHtml += `<td class="num ${cagrClass}" style="padding:4px 16px 12px 16px; font-weight:700;">${cagrFormatted}</td></tr>`;
    }
  });

  if (tbodyEl) tbodyEl.innerHTML = bodyHtml;
}

function renderEpsValuationCalculator(d) {
  if (!d) return;

  const currentPrice = d.quote?.price || 0;
  const curr = d.profile?.currency || "USD";
  const peStats = d.history?.peStats || {};
  const fwdPe = d.current?.forwardPe;
  let rawPe = peStats.median ? Number(peStats.median) : (d.current?.pe || 20);
  let isAdjusted = false;
  if (rawPe > 80 || (fwdPe && rawPe > 3 * fwdPe)) {
    rawPe = (fwdPe && fwdPe > 0 && fwdPe <= 80) ? fwdPe : 25;
    isAdjusted = true;
  }
  let medianPe = rawPe;

  let eps2030 = null;
  const grid = d.estimates?.growthGrid;
  if (grid && grid.rows) {
    const epsRow = grid.rows.find(r => r.label === "EPS");
    if (epsRow && epsRow.values && epsRow.values.length) {
      eps2030 = epsRow.values[epsRow.values.length - 1];
    }
  }
  
  if (!eps2030 || eps2030 <= 0) {
    let growthEst = d.current?.earningsGrowth || d.current?.revenueGrowth || 0.10;
    if (growthEst > 0.40) growthEst = 0.20;
    if (growthEst < -0.05) growthEst = 0.03;
    const cleanPe = (d.current?.pe && d.current.pe > 0 && d.current.pe <= 80) ? d.current.pe : null;
    const cleanFpe = (d.current?.forwardPe && d.current.forwardPe > 0 && d.current.forwardPe <= 80) ? d.current.forwardPe : null;
    const epsCurrent = cleanPe ? (currentPrice / cleanPe) : null;
    const epsFwd = cleanFpe ? (currentPrice / cleanFpe) : null;
    const epsBase = epsFwd ? epsFwd : (epsCurrent ? epsCurrent * (1 + growthEst) : null);
    if (epsBase && epsBase > 0) {
      eps2030 = epsBase * Math.pow(1 + growthEst, 4);
    }
  }
  
  if (!eps2030 || eps2030 <= 0 || !currentPrice) {
    if ($("est-pe-cons-price")) $("est-pe-cons-price").textContent = "—";
    if ($("est-pe-base-price")) $("est-pe-base-price").textContent = "—";
    if ($("est-pe-opt-price")) $("est-pe-opt-price").textContent = "—";
    return;
  }

  // Base PE = Historical Median PE (or fallback to current PE)
  const basePe = medianPe;
  // Conservative PE = 20% below Historical Median PE
  const consPe = Math.max(5, basePe * 0.80);
  // Optimistic PE = 20% above Historical Median PE
  const optPe = basePe * 1.20;

  function calcReturn(targetPe) {
    const targetPrice = eps2030 * targetPe;
    const totalReturnPct = ((targetPrice - currentPrice) / currentPrice) * 100;
    const cagrPct = currentPrice > 0 && targetPrice > 0 ? ((targetPrice / currentPrice) ** (1 / 4) - 1) * 100 : 0;
    return { targetPrice, totalReturnPct, cagrPct };
  }

  const consRes = calcReturn(consPe);
  const baseRes = calcReturn(basePe);
  const optRes = calcReturn(optPe);

  if ($("est-pe-cons-label")) $("est-pe-cons-label").textContent = `Conservador (-20%: ${consPe.toFixed(1)}x)`;
  if ($("est-pe-cons-price")) $("est-pe-cons-price").textContent = fmtPrice(consRes.targetPrice, curr);
  if ($("est-pe-cons-ret")) $("est-pe-cons-ret").innerHTML = `<span class="${consRes.totalReturnPct >= 0 ? 'up' : 'down'}">${fmtPct(consRes.totalReturnPct, 1, true)}</span> <span style="font-size:11px; font-weight:400; color:var(--muted);">(${fmtPct(consRes.cagrPct, 1, true)}/año)</span>`;

  const labelBaseText = isAdjusted ? `★ Base (Fwd PER: ${basePe.toFixed(1)}x)` : `★ Base (Mediana Histórica: ${basePe.toFixed(1)}x)`;
  if ($("est-pe-base-label")) $("est-pe-base-label").textContent = labelBaseText;
  if ($("est-pe-base-price")) $("est-pe-base-price").textContent = fmtPrice(baseRes.targetPrice, curr);
  if ($("est-pe-base-ret")) $("est-pe-base-ret").innerHTML = `<span class="${baseRes.totalReturnPct >= 0 ? 'up' : 'down'}">${fmtPct(baseRes.totalReturnPct, 1, true)}</span> <span style="font-size:11px; font-weight:400; color:var(--muted);">(${fmtPct(baseRes.cagrPct, 1, true)}/año)</span>`;

  if ($("est-pe-opt-label")) $("est-pe-opt-label").textContent = `Optimista (+20% Mediana: ${optPe.toFixed(1)}x)`;
  if ($("est-pe-opt-price")) $("est-pe-opt-price").textContent = fmtPrice(optRes.targetPrice, curr);
  if ($("est-pe-opt-ret")) $("est-pe-opt-ret").innerHTML = `<span class="${optRes.totalReturnPct >= 0 ? 'up' : 'down'}">${fmtPct(optRes.totalReturnPct, 1, true)}</span> <span style="font-size:11px; font-weight:400; color:var(--muted);">(${fmtPct(optRes.cagrPct, 1, true)}/año)</span>`;

  const slider = $("est-pe-slider");
  if (slider) {
    slider.value = basePe.toFixed(1);
    
    function updateCustomValuation() {
      const customPe = parseFloat(slider.value) || 20;
      if ($("est-pe-val")) $("est-pe-val").textContent = customPe.toFixed(1) + "x";
      const customRes = calcReturn(customPe);
      
      if ($("est-pe-custom-price")) $("est-pe-custom-price").textContent = fmtPrice(customRes.targetPrice, curr);
      
      const totEl = $("est-pe-custom-tot");
      if (totEl) {
        totEl.textContent = fmtPct(customRes.totalReturnPct, 1, true);
        totEl.className = customRes.totalReturnPct >= 0 ? 'up font-bold' : 'down font-bold';
      }
      
      const cagrEl = $("est-pe-custom-cagr");
      if (cagrEl) {
        cagrEl.textContent = fmtPct(customRes.cagrPct, 1, true);
        cagrEl.className = customRes.cagrPct >= 0 ? 'up font-bold' : 'down font-bold';
      }
    }

    slider.oninput = updateCustomValuation;
    updateCustomValuation();
  }
}

function renderEstimates(est) {
  if (!est) return;

  // Render main Growth Estimates Grid
  if (est.growthGrid) {
    renderGrowthEstimatesGrid(est.growthGrid);
  }

  // Render automatic EPS x PER 2030E Valuation Calculator
  if (state.data) {
    renderEpsValuationCalculator(state.data);
  }
  
  // Recommendations
  const recsBox = $("est-recs-box");
  if (recsBox && est.recommendations) {
    const r = est.recommendations;
    recsBox.innerHTML = `
      <span class="badge" style="background:#059669; color:#fff; padding:6px 12px; border-radius:6px; font-weight:700;">Fuerte Compra: ${r.strongBuy || 0}</span>
      <span class="badge" style="background:#10b981; color:#fff; padding:6px 12px; border-radius:6px; font-weight:700;">Compra: ${r.buy || 0}</span>
      <span class="badge" style="background:#f59e0b; color:#fff; padding:6px 12px; border-radius:6px; font-weight:700;">Mantener: ${r.hold || 0}</span>
      <span class="badge" style="background:#ef4444; color:#fff; padding:6px 12px; border-radius:6px; font-weight:700;">Venta: ${r.sell || 0}</span>
      <span class="badge" style="background:#991b1b; color:#fff; padding:6px 12px; border-radius:6px; font-weight:700;">Fuerte Venta: ${r.strongSell || 0}</span>
    `;
  }

  // Price targets
  const targetsBox = $("est-targets-box");
  if (targetsBox && est.priceTargets) {
    const pt = est.priceTargets;
    const curr = state.data?.profile?.currency || "USD";
    targetsBox.innerHTML = `
      <div style="text-align:center;">
        <span style="font-size:11px; color:var(--muted);">Mínimo</span>
        <div style="font-size:16px; font-weight:700; color:var(--red);">${pt.low != null ? fmtPrice(pt.low, curr) : '—'}</div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:11px; color:var(--muted);">Promedio Wall St.</span>
        <div style="font-size:20px; font-weight:800; color:var(--primary);">${pt.mean != null ? fmtPrice(pt.mean, curr) : '—'}</div>
      </div>
      <div style="text-align:center;">
        <span style="font-size:11px; color:var(--muted);">Máximo</span>
        <div style="font-size:16px; font-weight:700; color:var(--green);">${pt.high != null ? fmtPrice(pt.high, curr) : '—'}</div>
      </div>
    `;
  }

  // EPS estimates table
  const epsBody = $("est-eps-tbody");
  if (epsBody) {
    const rows = est.earningsEstimate || [];
    epsBody.innerHTML = rows.length ? rows.map(r => `
      <tr>
        <td><b>${r.period === '0q' ? 'Trimestre Actual' : r.period === '+1q' ? 'Próximo Trimestre' : r.period === '0y' ? 'Año Fiscal Actual' : 'Próximo Año Fiscal'}</b></td>
        <td class="num font-bold">${r.avg != null ? '$' + r.avg.toFixed(2) : '—'}</td>
        <td class="num muted">${r.low != null ? '$' + r.low.toFixed(2) : '—'}</td>
        <td class="num muted">${r.high != null ? '$' + r.high.toFixed(2) : '—'}</td>
        <td class="num">${r.yearAgoEps != null ? '$' + r.yearAgoEps.toFixed(2) : '—'}</td>
        <td class="num">${r.analysts != null ? r.analysts : '—'}</td>
        <td class="num ${r.growth != null && r.growth >= 0 ? 'up' : 'down'}">${r.growth != null ? fmtPct(r.growth * 100, 1, true) : '—'}</td>
      </tr>
    `).join('') : '<tr><td colspan="7" class="num muted" style="text-align:center;">Sin estimaciones disponibles</td></tr>';
  }

  // Revenue estimates table
  const revBody = $("est-rev-tbody");
  if (revBody) {
    const rows = est.revenueEstimate || [];
    const curr = state.data?.profile?.currency || "USD";
    revBody.innerHTML = rows.length ? rows.map(r => `
      <tr>
        <td><b>${r.period === '0q' ? 'Trimestre Actual' : r.period === '+1q' ? 'Próximo Trimestre' : r.period === '0y' ? 'Año Fiscal Actual' : 'Próximo Año Fiscal'}</b></td>
        <td class="num font-bold">${r.avg != null ? fmtBig(r.avg, curr) : '—'}</td>
        <td class="num muted">${r.low != null ? fmtBig(r.low, curr) : '—'}</td>
        <td class="num muted">${r.high != null ? fmtBig(r.high, curr) : '—'}</td>
        <td class="num">${r.yearAgoRevenue != null ? fmtBig(r.yearAgoRevenue, curr) : '—'}</td>
        <td class="num">${r.analysts != null ? r.analysts : '—'}</td>
        <td class="num ${r.growth != null && r.growth >= 0 ? 'up' : 'down'}">${r.growth != null ? fmtPct(r.growth * 100, 1, true) : '—'}</td>
      </tr>
    `).join('') : '<tr><td colspan="7" class="num muted" style="text-align:center;">Sin estimaciones disponibles</td></tr>';
  }

  // Mini bar chart EPS estimados vs año anterior
  renderEpsEstimatesChart(est);
}

function renderInsidersHolders(ih) {
  if (!ih) return;

  $("ins-pct-val").textContent = ih.insiderPercent != null ? fmtPct(ih.insiderPercent, 2) : "—";
  $("inst-pct-val").textContent = ih.institutionPercent != null ? fmtPct(ih.institutionPercent, 2) : "—";

  // Insiders Table
  const insBody = $("ins-tbody");
  if (insBody) {
    const rows = ih.insiders || [];
    insBody.innerHTML = rows.length ? rows.map(r => {
      const txn = r.transaction && r.transaction.trim() ? r.transaction : '—';
      const isBuy = txn.toLowerCase().includes('purchase') || txn.toLowerCase().includes('buy') || txn.toLowerCase().includes('compra');
      const isSell = txn.toLowerCase().includes('sale') || txn.toLowerCase().includes('sell') || txn.toLowerCase().includes('venta');
      const txnColor = isBuy ? 'color:var(--green); font-weight:700;' : isSell ? 'color:var(--red); font-weight:700;' : '';
      return `
        <tr>
          <td>${r.date || '—'}</td>
          <td><b>${r.insider}</b></td>
          <td>${r.position || '—'} <span style="${txnColor}">${txn !== '—' ? '· ' + txn : ''}</span></td>
          <td class="num">${r.shares != null ? Math.round(r.shares).toLocaleString() : '—'}</td>
          <td class="num">${r.value != null ? '$' + Math.round(r.value).toLocaleString() : '—'}</td>
        </tr>
      `;
    }).join('') : '<tr><td colspan="5" class="num muted" style="text-align:center;">Sin registros recientes de directivos</td></tr>';
  }

  // Institutional Holders Table
  const hBody = $("holders-tbody");
  if (hBody) {
    const rows = ih.holders || [];
    hBody.innerHTML = rows.length ? rows.map(r => `
      <tr>
        <td><b>${r.holder}</b></td>
        <td class="num">${r.shares != null ? Math.round(r.shares).toLocaleString() : '—'}</td>
        <td class="num">${r.value != null ? '$' + Math.round(r.value).toLocaleString() : '—'}</td>
        <td class="num ${r.pctChange != null && r.pctChange >= 0 ? 'up' : 'down'}">${r.pctChange != null ? fmtPct(r.pctChange * 100, 2, true) : '—'}</td>
        <td>${r.date || '—'}</td>
      </tr>
    `).join('') : '<tr><td colspan="5" class="num muted" style="text-align:center;">Sin registros recientes de fondos institucionales</td></tr>';
  }
}

/* ----------------------------------------------------- financial statement explorer */
let currentFinStmt = "income";
let currentFinFreq = "annual";

function renderFinancialStatements(d, stmtType = currentFinStmt, freqType = currentFinFreq) {
  currentFinStmt = stmtType;
  currentFinFreq = freqType;
  
  const series = freqType === "annual" ? (d.annuals || []) : (d.quarterlies || []);
  const periods = series.map(a => freqType === "annual" ? a.year : new Date(a.endDate).toISOString().split('T')[0]);
  const cur = d.profile.currency || "USD";

  // Botones activos de estado
  document.querySelectorAll(".fin-stmt-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.stmt === stmtType);
    btn.onclick = () => renderFinancialStatements(d, btn.dataset.stmt, currentFinFreq);
  });

  // Botones activos de frecuencia
  const btnAnnual = $("tg-freq-annual");
  const btnQuarter = $("tg-freq-quarter");
  if (btnAnnual && btnQuarter) {
    btnAnnual.classList.toggle("active", freqType === "annual");
    btnQuarter.classList.toggle("active", freqType === "quarterly");
    btnAnnual.onclick = () => renderFinancialStatements(d, currentFinStmt, "annual");
    btnQuarter.onclick = () => renderFinancialStatements(d, currentFinStmt, "quarterly");
  }

  const headEl = $("fin-stmt-thead");
  const bodyEl = $("fin-stmt-tbody");
  if (!headEl || !bodyEl) return;

  headEl.innerHTML = `<tr><th>Concepto</th>${periods.map(p => `<th class="num" style="font-size:11px;">${p}</th>`).join('')}</tr>`;

  let rows = [];
  if (stmtType === "income") {
    rows = [
      ["Ingresos Totales (Revenue)", a => fmtBig(a.revenue, cur)],
      ["Ganancia Bruta (Gross Profit)", a => (a.revenue && a.grossMargin != null) ? fmtBig(a.revenue * a.grossMargin / 100, cur) : "—"],
      ["Margen Bruto (%)", a => a.grossMargin != null ? fmtPct(a.grossMargin, 1) : "—"],
      ["Beneficio Operativo (Operating Income)", a => (a.revenue && a.opMargin != null) ? fmtBig(a.revenue * a.opMargin / 100, cur) : "—"],
      ["Margen Operativo (%)", a => a.opMargin != null ? fmtPct(a.opMargin, 1) : "—"],
      ["Utilidad Neta (Net Income)", a => fmtBig(a.netIncome, cur)],
      ["Margen Neto (%)", a => a.netMargin != null ? fmtPct(a.netMargin, 1) : "—"],
      ["EBITDA", a => fmtBig(a.ebitda, cur)],
      ["Beneficio Por Acción (EPS)", a => a.eps != null ? fmtPrice(a.eps, cur) : "—"],
      ["Dividendos Pagados (DPS)", a => a.dividendPS != null ? fmtPrice(a.dividendPS, cur) : "—"]
    ];
  } else if (stmtType === "balance") {
    rows = [
      ["Activos Totales", a => fmtBig(a.assets, cur)],
      ["Efectivo y Equivalentes", a => fmtBig(a.cash, cur)],
      ["Deuda Total", a => fmtBig(a.totalDebt, cur)],
      ["Patrimonio de Accionistas", a => fmtBig(a.equity, cur)],
      ["Capital de Trabajo (Working Cap.)", a => a.workingCapital != null ? fmtBig(a.workingCapital, cur) : "—"],
      ["Acciones en Circulación", a => a.shares != null ? fmtBig(a.shares, "") : "—"],
      ["Deuda / Patrimonio", a => a.debtToEquity != null ? fmtRatio(a.debtToEquity, 2) : "—"],
      ["Razón Corriente (Current Ratio)", a => a.currentRatio != null ? fmtRatio(a.currentRatio, 2) : "—"],
    ];
  } else if (stmtType === "cashflow") {
    rows = [
      ["Flujo de Caja Operativo", a => fmtBig(a.ocf, cur)],
      ["Gastos de Capital (CapEx)", a => {
        if (a.capex == null || !isFinite(a.capex)) return "—";
        const formatted = fmtBig(a.capex, cur);
        return `<span class="down" title="El CapEx negativo es normal: indica inversión de capital en activos productivos.">${formatted}</span>`;
      }],
      ["Flujo de Caja Libre (FCF)", a => {
        if (a.fcf == null || !isFinite(a.fcf)) return "—";
        return `<span class="${a.fcf >= 0 ? 'up' : 'down'}">${fmtBig(a.fcf, cur)}</span>`;
      }],
      ["FCF Por Acción", a => (a.fcf && a.sharesOut) ? fmtPrice(a.fcf / a.sharesOut, cur) : "—"],
    ];
  }

  bodyEl.innerHTML = rows.map(([label, fn]) => {
    return `
      <tr>
        <td style="font-weight:500">${label}</td>
        ${series.map(a => `<td class="num">${fn(a)}</td>`).join('')}
      </tr>
    `;
  }).join('');
}

/* ----------------------------------------------------- sistema de alertas */
const ALERTS_KEY = "stock_alerts_v1";

function getAlerts() {
  try { return JSON.parse(localStorage.getItem(ALERTS_KEY)) || []; } catch { return []; }
}
function saveAlerts(arr) {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(arr));
}

$("btn-alerts").onclick = () => {
  $("alert-in-sym").value = state.symbol || "NVDA";
  renderAlertsList();
  $("modal-alerts").classList.remove("hidden");
};
$("modal-alerts-close").onclick = () => {
  $("modal-alerts").classList.add("hidden");
};

$("form-alert-add").onsubmit = e => {
  e.preventDefault();
  const sym = $("alert-in-sym").value.toUpperCase();
  const type = $("alert-in-type").value;
  const target = parseFloat($("alert-in-target").value);
  if (!sym || isNaN(target)) return;

  const alerts = getAlerts();
  alerts.push({ id: Date.now(), symbol: sym, type, target });
  saveAlerts(alerts);
  $("alert-in-target").value = "";
  renderAlertsList();
  toast(`✓ Alerta guardada para ${sym}`);
};

function deleteAlert(id) {
  const alerts = getAlerts().filter(a => a.id !== id);
  saveAlerts(alerts);
  renderAlertsList();
}

function renderAlertsList() {
  const listEl = $("alerts-list");
  if (!listEl) return;
  const alerts = getAlerts();
  if (!alerts.length) {
    listEl.innerHTML = `<p class="muted" style="font-size:12px;">No tienes alertas activas.</p>`;
    return;
  }
  listEl.innerHTML = alerts.map(a => {
    let lbl = "";
    if (a.type === "price_below") lbl = `Precio < $${a.target}`;
    else if (a.type === "price_above") lbl = `Precio > $${a.target}`;
    else if (a.type === "mos_above") lbl = `Margen de Seg. > ${a.target}%`;

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:var(--bg); border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:12.5px; font-weight:600; color:var(--text);">${a.symbol}: ${lbl}</span>
        <button class="btn-x" onclick="deleteAlert(${a.id})" title="Eliminar">✕</button>
      </div>
    `;
  }).join("");
}

function checkStockAlerts(d) {
  if (!d) return;
  const alerts = getAlerts().filter(a => a.symbol === d.symbol);
  const px = d.quote.price;
  const mos = d.valuation.marginOfSafety;

  alerts.forEach(a => {
    let triggered = false;
    let msg = "";
    if (a.type === "price_below" && px <= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: ${d.symbol} cayó a $${px.toFixed(2)} (Objetivo: < $${a.target})`;
    } else if (a.type === "price_above" && px >= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: ${d.symbol} subió a $${px.toFixed(2)} (Objetivo: > $${a.target})`;
    } else if (a.type === "mos_above" && mos != null && mos >= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: Margen de Seguridad de ${d.symbol} alcanzó ${mos.toFixed(1)}% (Objetivo: > ${a.target}%)`;
    }
    if (triggered) {
      toast(msg);
    }
  });
}

/* ----------------------------------------------------- standalone valuation & historical panes */
function renderEpsFv(d) {
  const container = $("eps-fv-details");
  if (!container) return;
  const cur = d.profile.currency || "USD";
  const eps = d.current.eps;
  const peMed = d.history.peStats ? d.history.peStats.median : null;
  const fv = (eps && peMed) ? eps * peMed : null;
  const px = d.quote.price;
  const mos = (fv && px) ? ((fv - px) / fv * 100) : null;

  container.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px;">
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">EPS TTM</span>
        <div style="font-size:22px; font-weight:800; color:var(--text); margin-top:4px;">${eps != null ? '$' + eps.toFixed(2) : '—'}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">P/E Mediana Histórica (5Y)</span>
        <div style="font-size:22px; font-weight:800; color:var(--gold); margin-top:4px;">${peMed != null ? peMed.toFixed(1) + 'x' : '—'}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Fair Value P/E Estimado</span>
        <div style="font-size:22px; font-weight:800; color:var(--primary); margin-top:4px;">${fv != null ? fmtPrice(fv, cur) : '—'}</div>
      </div>
    </div>
    <div style="padding:16px; background:var(--panel); border:1px solid var(--border); border-radius:var(--radius);">
      <p style="font-size:13px; color:var(--text); margin-bottom:8px;"><b>Fórmula aplicable:</b> <code>Valor Intrínseco = EPS (TTM) × P/E Mediana Histórica</code></p>
      <p style="font-size:12.5px; color:var(--muted);">Basado en el precio actual de <b>${fmtPrice(px, cur)}</b>, este modelo indica un Margen de Seguridad del <b class="${mos >= 0 ? 'up' : 'down'}">${mos != null ? fmtPct(mos, 1, true) : '—'}</b>.</p>
    </div>
  `;
}

function renderDcfFv(d) {
  const container = $("dcf-fv-details");
  if (!container) return;
  const cur = d.profile.currency || "USD";
  // Extraer el modelo DCF desde el array de modelos
  const dcfModel = (d.valuation.models || []).find(m => m.id === "dcf");
  const dcfVal = dcfModel ? dcfModel.fair : null;
  const px = d.quote.price;
  const mos = (dcfVal && px) ? ((dcfVal - px) / dcfVal * 100) : null;
  const inputs = d.valuation.dcfInputs || {};

  container.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px;">
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Precio Actual</span>
        <div style="font-size:22px; font-weight:800; color:var(--text); margin-top:4px;">${fmtPrice(px, cur)}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Valor Intrínseco DCF</span>
        <div style="font-size:22px; font-weight:800; color:var(--primary); margin-top:4px;">${dcfVal != null ? fmtPrice(dcfVal, cur) : '—'}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Margen de Seguridad DCF</span>
        <div style="font-size:22px; font-weight:800; color:${mos != null && mos >= 0 ? 'var(--green)' : 'var(--red)'}; margin-top:4px;">${mos != null ? fmtPct(mos, 1, true) : dcfVal == null ? 'No aplica' : '—'}</div>
      </div>
    </div>
    ${dcfVal == null ? `<div style="padding:14px; background:var(--gold-soft); border:1px solid var(--gold-border); border-radius:var(--radius); font-size:12.5px; color:var(--gold-text);">ℹ️ El modelo DCF de FCF no aplica para esta empresa (puede ser financiera o tener FCF negativo). Se usa el modelo DDM para el consenso.</div>` : `<p class="muted" style="font-size:12.5px;">Supuestos usados: Crecimiento FCF base <b>${inputs.growth != null ? fmtPct(inputs.growth * 100, 1) : '—'}</b>, WACC <b>${inputs.discount != null ? fmtPct(inputs.discount * 100, 1) : '—'}</b>, Tasa terminal <b>${inputs.terminal != null ? fmtPct(inputs.terminal * 100, 1) : '—'}</b>. Puedes ajustarlos en la pestaña <b>⚖️ Ratios &amp; Growth</b>.</p>`}
  `;
}

function renderDdmFv(d) {
  const container = $("ddm-fv-details");
  if (!container) return;
  const cur = d.profile.currency || "USD";
  // Extraer el modelo DDM desde el array de modelos (solo existe para empresas financieras/dividendo)
  const ddmModel = (d.valuation.models || []).find(m => m.id === "ddm");
  const ddmVal = ddmModel ? ddmModel.fair : null;
  const divYield = d.current.divYield;
  const px = d.quote.price;
  const mos = (ddmVal && px) ? ((ddmVal - px) / ddmVal * 100) : null;
  const lastDividend = (d.annuals && d.annuals.length) ? d.annuals[d.annuals.length - 1].dividendPS : null;

  container.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px;">
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Dividend Yield (TTM)</span>
        <div style="font-size:${divYield ? '22' : '14'}px; font-weight:800; color:var(--primary); margin-top:4px;">${divYield != null ? fmtPct(divYield, 2) : 'No paga dividendo'}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Dividendo Por Acción (Último Año)</span>
        <div style="font-size:22px; font-weight:800; color:var(--text); margin-top:4px;">${lastDividend != null ? fmtPrice(lastDividend, cur) : '—'}</div>
      </div>
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); text-align:center;">
        <span style="font-size:12px; color:var(--muted); font-weight:600;">Valor Intrínseco DDM (Gordon Growth)</span>
        <div style="font-size:22px; font-weight:800; color:var(--primary); margin-top:4px;">${ddmVal != null ? fmtPrice(ddmVal, cur) : '—'}</div>
      </div>
    </div>
    ${ddmVal == null ? `<div style="padding:14px; background:var(--cyan-soft); border:1px solid var(--border); border-radius:var(--radius); font-size:12.5px; color:var(--muted);">ℹ️ El modelo DDM (Gordon Growth) solo aplica para empresas del sector financiero o bancos con dividendos predecibles. Para esta empresa el consenso usa el modelo DCF de Flujo de Caja Libre.</div>` : `<p class="muted" style="font-size:12.5px; margin-top:8px;">Margen de Seguridad DDM: <b class="${mos >= 0 ? 'up' : 'down'}">${fmtPct(mos, 1, true)}</b> respecto al precio actual de ${fmtPrice(px, cur)}.</p>`}
  `;
}

function renderHistoricalRatios(d) {
  const headEl = $("hist-ratios-thead");
  const bodyEl = $("hist-ratios-tbody");
  if (!headEl || !bodyEl) return;
  // Mostrar solo los últimos 10 años, del más reciente al más antiguo
  const annuals = [...(d.annuals || [])].reverse().slice(0, 10).reverse();
  const years = annuals.map(a => a.year);
  const cur = d.profile.currency || "USD";

  headEl.innerHTML = `<tr><th>Métrica</th>${years.map(y => `<th class="num">${y}</th>`).join('')}</tr>`;

  const rows = [
    ["Ingresos (Revenue)", a => fmtBig(a.revenue, cur)],
    ["Utilidad Neta (Net Income)", a => fmtBig(a.netIncome, cur)],
    ["EPS Diluido", a => a.eps != null ? fmtPrice(a.eps, cur) : '—'],
    ["Margen Bruto (%)", a => a.grossMargin != null ? fmtPct(a.grossMargin, 1) : '—'],
    ["Margen Operativo (%)", a => a.opMargin != null ? fmtPct(a.opMargin, 1) : '—'],
    ["Margen Neto (%)", a => a.netMargin != null ? fmtPct(a.netMargin, 1) : '—'],
    ["ROE (%)", a => a.roe != null ? fmtPct(a.roe, 1) : '—'],
    ["ROIC (%)", a => a.roic != null ? fmtPct(a.roic, 1) : '—'],
    ["Deuda / Patrimonio", a => a.debtToEquity != null ? fmtRatio(a.debtToEquity, 2) : '—'],
    ["Razón Corriente", a => a.currentRatio != null ? fmtRatio(a.currentRatio, 2) : '—'],
    ["Flujo de Caja Operativo (OCF)", a => fmtBig(a.ocf, cur)],
    ["Gastos de Capital (CapEx)", a => fmtBig(a.capex, cur)],
    ["Flujo de Caja Libre (FCF)", a => fmtBig(a.fcf, cur)],
    ["Dividendo Por Acción (DPS)", a => a.dividendPS != null ? fmtPrice(a.dividendPS, cur) : '—'],
  ];

  bodyEl.innerHTML = rows.map(([label, fn]) => `
    <tr>
      <td><b>${label}</b></td>
      ${annuals.map(a => `<td class="num">${fn(a)}</td>`).join('')}
    </tr>
  `).join('');

  /* Botón de descarga CSV */
  const csvWrap = $('hist-ratios-csv-wrap');
  if (csvWrap && !csvWrap.dataset.bound) {
    csvWrap.dataset.bound = '1';
    csvWrap.innerHTML = `<button class="btn btn-sm" id="hist-ratios-csv-btn" style="margin-top:10px; gap:5px; display:inline-flex; align-items:center;">
      <span style="font-size:14px;">⬇</span> Exportar CSV
    </button>`;
    csvWrap.querySelector('#hist-ratios-csv-btn').onclick = () => {
      const esc = s => `"${String(s ?? '').replace(/"/g, '""')}"`;
      const header = ['Métrica', ...years].map(esc).join(';');
      const lines = [header, ...rows.map(([label, fn]) =>
        [esc(label), ...annuals.map(a => esc(fn(a).replace(/<[^>]+>/g, '')))] .join(';')
      )].join('\n');
      const blob = new Blob(['\uFEFF' + lines], { type: 'text/csv;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${state.symbol}_ratios_historicos_${new Date().toISOString().slice(0,10)}.csv`;
      a.click(); URL.revokeObjectURL(a.href);
    };
  }
}

function renderAdditional(d) {
  const container = $("additional-details");
  if (!container) return;
  const p = d.profile;
  const q = d.quote;

  let filingsHtml = '<span class="muted" style="font-size:12px;">Sin documentos recientes</span>';
  if (p.secFilings) {
    if (Array.isArray(p.secFilings)) {
      filingsHtml = p.secFilings.map(f => `<a href="${f.url}" target="_blank" class="btn btn-sm">${f.form} (${f.date})</a>`).join('');
    } else if (typeof p.secFilings === 'object') {
      filingsHtml = Object.entries(p.secFilings).map(([type, url]) => 
        `<a href="${url}" target="_blank" class="btn btn-sm">${type === 'annual' ? '📄 10-K Anual (SEC)' : '📄 10-Q Trimestral (SEC)'}</a>`
      ).join('');
    }
  }

  container.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);">
        <h4 style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:10px;">Perfil de la Empresa</h4>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Nombre:</b> ${p.name}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Sector:</b> ${p.sector || '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Industria:</b> ${p.industry || '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>País:</b> ${p.country || '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Bolsa:</b> ${p.exchange || '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Empleados:</b> ${p.employees ? p.employees.toLocaleString() : '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Sitio Web:</b> <a href="${p.website}" target="_blank" style="color:var(--primary); text-decoration:underline;">${p.website || '—'}</a></p>
      </div>

      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);">
        <h4 style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:10px;">Datos de Mercado y Archivos SEC</h4>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Próximos Resultados:</b> ${p.nextEarnings || 'Por confirmar'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Volumen Diario:</b> ${q.volume ? q.volume.toLocaleString() : '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Volumen Promedio:</b> ${q.avgVolume ? q.avgVolume.toLocaleString() : '—'}</p>
        <h5 style="font-size:13px; font-weight:700; color:var(--text); margin-top:14px; margin-bottom:6px;">Documentos Oficiales SEC EDGAR</h5>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          ${filingsHtml}
        </div>
      </div>
    </div>
  `;
}

/* ----------------------------------------------------------------- init */
route();
