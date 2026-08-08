/* Render del análisis: encabezado, summary, gráfico de precio, notas
   cualitativas, scorecard Buffett, tabla de crecimiento, sidebar y
   orquestación de pestañas de acción. */

import { $, toast, apiFetch } from "./dom.js";
import { state, currentPeriodYears, currentMultiplesRange, setCurrentMultiplesRange } from "./state.js";
import { fmtPrice, fmtPct, fmtBig, fmtNum, fmtRatio, escHtml, pctClass } from "./format.js";
import { termify } from "./glossary.js";
import { chartPrice, chartRatio, chartDividends, chartEps, chartEarningsSurprise, renderAllCharts, renderPriceOverlay, renderKoyfinLayout, C, charts } from "./charts.js";

import { checkStockAlerts } from "./alerts.js";
import {
  renderValuationCard, renderRatiosGrid, renderEstimates, renderEpsEstimatesChart,
  renderInsidersHolders, renderFinancialStatements, renderEpsFv, renderDcfFv,
  renderDdmFv, renderHistoricalRatios, renderAdditional, renderScenarios, renderFcfHistory,
} from "./valuation.js";

/* ---------------------------------------------------------- render */
export function renderAnalysis(d) {
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
  safeCall(renderScenarios, d);
  safeCall(renderFcfHistory, d);
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
  safeCall(renderKoyfinBar, d);
  safeCall(renderWidgetBoard, d);

  try { loadNotes(d.symbol); } catch(e){}
  try { setStarState(d.inWatchlist); } catch(e){}

  safeCall(triggerTabSpecificActions, state.activeTab);

  if ($("co-summary")) $("co-summary").textContent = d.profile.summary || "";
  if (analysisBox) analysisBox.classList.remove("hidden");
}

/* ----------------------------------------------- render summary */
export function renderSummary(d) {
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
    peMedRow.classList.remove("d-none");
  } else if (peMedRow) {
    peMedRow.classList.add("d-none");
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

export function renderNews(news) {
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
      <a href="${escHtml(link)}" target="_blank" style="display:flex; gap:16px; padding:12px; border:1px solid var(--border); border-radius:var(--radius); text-decoration:none; color:inherit; transition:all 0.2s; background:var(--surface);" class="hover-card">
        ${thumb ? `<img src="${escHtml(thumb)}" alt="thumbnail" style="width:100px; height:70px; object-fit:cover; border-radius:4px;">` : `<div style="width:100px; height:70px; background:var(--bg); border-radius:4px; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:10px;">Sin Imagen</div>`}
        <div style="display:flex; flex-direction:column; justify-content:space-between; flex:1;">
          <h4 style="margin:0; font-size:14px; font-weight:600; line-height:1.3; color:var(--text);">${escHtml(n.title || 'Noticia')}</h4>
          <div style="font-size:11px; color:var(--muted); margin-top:6px; display:flex; justify-content:space-between;">
            <span style="font-weight:600; color:var(--primary);">${escHtml(publisher)}</span>
            <span>${escHtml(date)}</span>
          </div>
        </div>
      </a>
    `;
  }).join('');
}

/* -------------------------------------------- chart price summary */
export function chartPriceSummary(d) {
  if (!d || !d.history || !d.history.price) return;
  const pts = d.history.price;

  // Filtrar según período en años
  const cutoff = Date.now() - (currentPeriodYears * 365 * 24 * 60 * 60 * 1000);
  const filteredPts = pts.filter(pt => pt[0] >= cutoff);

  chartPrice(d, "summary-price-chart", filteredPts);
}

export function updateCagrModal() {
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

/* ------------------------------------------------ avisos de datos */
export function renderWarnings(warnings) {
  const box = $("data-warnings");
  if (!warnings || !warnings.length) return box.classList.add("hidden");

  const summary = $("warnings-summary");
  const list = $("warnings-list");

  if (summary && list) {
    // Nueva UI colapsable
    summary.innerHTML = `⚠️ ${warnings.length} aviso${warnings.length > 1 ? 's' : ''} de calidad de datos <span style="font-size:11px; font-weight:400; color:var(--muted); margin-left:4px;">(haz clic para expandir)</span>`;
    list.innerHTML = warnings.map(w => `<li style="margin-bottom:4px; line-height:1.5;">${escHtml(w)}</li>`).join("");
  } else {
    // Fallback para compatibilidad
    box.innerHTML = `<details><summary style="cursor:pointer; font-weight:700;">⚠️ ${warnings.length} aviso${warnings.length > 1 ? 's' : ''} de calidad de datos</summary><ul style="margin:6px 0 0 18px; padding:0;">${warnings.map(w => `<li>${escHtml(w)}</li>`).join("")}</ul></details>`;
  }
  box.classList.remove("hidden");
}

/* ------------------------------------------- seguridad del dividendo */
export function renderDividendSafety(ds) {
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

/* --------------------------------------------- notas cualitativas */
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

export async function loadNotes(symbol) {
  noteSymbol = symbol;
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(symbol.replace(/\//g, '-'))}`);
    if (!r.ok) throw new Error(`Error ${r.status}`);
    const note = await r.json();
    const moats = Array.isArray(note.moats) ? note.moats : [];
    if (noteSymbol !== symbol) return; // navegó a otro símbolo mientras cargaba
    $("moat-checks").innerHTML = MOATS.map(([id, label, desc]) => `
      <label class="moat ${moats.includes(id) ? "on" : ""}" title="${escHtml(desc)}">
        <input type="checkbox" value="${id}" ${moats.includes(id) ? "checked" : ""}> ${escHtml(label)}
      </label>`).join("");
    $("note-thesis").value = note.thesis || "";
    $("note-risks").value = note.risks || "";

    $("moat-checks").querySelectorAll("input").forEach(cb =>
      cb.onchange = () => { cb.closest(".moat").classList.toggle("on", cb.checked); saveNotes(); });
    $("note-thesis").oninput = saveNotesDebounced;
    $("note-risks").oninput = saveNotesDebounced;
  } catch {
    if (noteSymbol === symbol) $("note-status").textContent = "⚠ no se pudo cargar";
  }
}

export function saveNotesDebounced() {
  clearTimeout(noteTimer);
  $("note-status").textContent = "escribiendo…";
  noteTimer = setTimeout(saveNotes, 900);
}

export async function saveNotes() {
  if (!noteSymbol) return;
  const moats = [...$("moat-checks").querySelectorAll("input:checked")].map(cb => cb.value);
  try {
    const r = await apiFetch(`/api/notes/${encodeURIComponent(noteSymbol.replace(/\//g, '-'))}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thesis: $("note-thesis").value, risks: $("note-risks").value, moats }),
    });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    $("note-status").textContent = "guardado ✓";
  } catch (e) {
    $("note-status").textContent = "⚠ error de guardado";
  }
}

/* ------------------------------------------ buffett scorecard */
export function renderBuffettScorecard(sc) {
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
      return `<div class="check ${cls}" title="${escHtml(ch.desc)}">
        <span class="icon">${icon}</span>
        <div><div class="name">${escHtml(ch.name)}</div><div class="val">${escHtml(ch.desc)}${val}</div></div>
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
              <span class="scorecard-item-name">${escHtml(c.name)}</span>
              <span class="scorecard-item-desc">${escHtml(c.desc)}</span>
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

/* ----------------------------------------------- tabla crecimiento */
export function renderGrowthTable(d) {
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
        <td>${escHtml(r.metric)}</td>
        <td class="num">${r.metric.includes("EPS") || r.metric.includes("Dividendo") ? fmtNum(r.current, 2) : fmtBig(r.current, d.profile.currency)}</td>
        ${cell(r.cagr1)}${cell(r.cagr3)}${cell(r.cagr5)}${cell(r.cagr10)}
      </tr>`).join("")}</tbody>`;
}

/* ---------------------------------------------------------- watch star */
export function setStarState(inWatchlist) {
  const b = $("btn-watch");
  b.classList.toggle("active", !!inWatchlist);
  b.classList.toggle("starred", !!inWatchlist);
  b.innerHTML = `<svg class="h-ico "><use href="#i-star"/></svg>${inWatchlist ? "Siguiendo" : "Seguir"}`;
  b.title = inWatchlist ? "Quitar de la watchlist" : "Agregar a watchlist (objetivo: MoS ≥ 25%)";
}

/* --------------------------------------------- múltiplos históricos */
export function renderRatiosCharts(d, range = "all") {
  setCurrentMultiplesRange(range);
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
  const pcfPairs = filterPairs(d.history.pcfTtm);

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
  chartRatio("ch-pcf", pcfPairs, getStats(pcfPairs), C.amber, "P/Cash Flow");
  requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
}

export function triggerTabSpecificActions(tab) {
  if (tab === "summary") {
    chartPriceSummary(state.data);
  } else if (tab === "valuation") {
    renderEstimates(state.data?.estimates);
    renderEpsEstimatesChart(state.data?.estimates);
    requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
  } else if (tab === "financials-hub" || tab === "financials" || tab === "ratios") {
    renderAllCharts(state.data);
    renderRatiosCharts(state.data, currentMultiplesRange);
    renderPriceOverlay(state.data);
    renderKoyfinLayout(state.data);
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

/* --------------------------------------------- sidebar favoritos */
const SB_KEY = "sb_hidden";

export function sbSetHidden(hidden) {
  $("sidebar").classList.toggle("hidden", hidden);
  $("sb-open").classList.toggle("hidden", !hidden);
  document.body.classList.toggle("with-sidebar", !hidden);
  localStorage.setItem(SB_KEY, hidden ? "1" : "0");
  requestAnimationFrame(() => Object.values(charts).forEach(ch => ch.resize()));
}

export function sparkSvg(values, color) {
  if (!values || values.length < 2) return "";
  const w = 72, h = 26, min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) =>
    `${(i / (values.length - 1) * w).toFixed(1)},${(h - 2 - (v - min) / span * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5"/></svg>`;
}

export function sparkSvgSmall(values, color) {
  if (!values || values.length < 2) return "";
  const w = 36, h = 14, min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) =>
    `${(i / (values.length - 1) * w).toFixed(1)},${(h - 2 - (v - min) / span * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.2"/></svg>`;
}

export async function refreshSidebar() {
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
      return `<div class="sb-item" data-symbol="${escHtml(q.symbol)}">
        <div class="sb-sym">${escHtml(q.symbol)}</div>
        ${sparkSvg(q.spark, color)}
        <div class="sb-quote">
          <div class="sb-price">${fmtNum(q.price, q.price >= 1000 ? 0 : 2)}</div>
          <div class="sb-chg ${up ? "up" : "down"}">${fmtPct(q.changePct, 2, true)}</div>
        </div>
      </div>`;
    }).join("");
  } catch { /* red caída */ }
}

/* ────────────────────────── barra de KPIs estilo Koyfin ───────────── */
function _kpi(label, value, cls = "") {
  return `<div class="k-kpi"><span class="k-kpi-lab">${label}</span><b class="k-kpi-val ${cls}">${value || "—"}</b></div>`;
}

function _priceCagr(pts, n) {
  if (!pts || pts.length < 5) return null;
  const last = pts[pts.length - 1][0];
  const target = last - n * 365.25 * 86400000;
  let i = 0;
  for (let k = 0; k < pts.length; k++) {
    if (pts[k][0] >= target) { i = k > 0 ? k - 1 : 0; break; }
  }
  const v0 = pts[i][1], v1 = pts[pts.length - 1][1];
  if (!v0 || !v1 || v0 <= 0) return null;
  return (Math.pow(v1 / v0, 1 / n) - 1) * 100;
}

export function renderKoyfinBar(d) {
  const el = $("k-kpis");
  if (!el || !d) return;
  const p = d.profile || {}, q = d.quote || {}, c = d.current || {};
  const pts = (d.history && d.history.price) || [];
  const mkt = q.marketCap != null ? fmtBig(q.marketCap) : null;
  const cagr3 = _priceCagr(pts, 3), cagr10 = _priceCagr(pts, 10);
  let nextStr = p.nextEarnings ? String(p.nextEarnings) : null;
  try {
    if (nextStr) nextStr = new Date(nextStr + "T00:00:00").toLocaleDateString("es-CL", { weekday: "short", day: "2-digit", month: "short" });
  } catch (e) {}
  el.innerHTML = [
    _kpi("Sector", escHtml(p.sector || "—")),
    _kpi("Industry", escHtml(p.industry || "—")),
    _kpi("Dividend Yield", c.divYield != null ? `${fmtNum(c.divYield, 2)}%` : "—", "k-mono"),
    _kpi("Market Cap", mkt, "k-mono"),
    _kpi("P/E Trailing", c.pe ? `${fmtRatio(c.pe, 1)}x` : "—", "k-mono"),
    _kpi("P/E Forward", c.forwardPe ? `${fmtRatio(c.forwardPe, 1)}x` : "—", "k-mono"),
    _kpi("CAGR 3Y", cagr3 != null ? fmtPct(cagr3, 1, true) : "—", cagr3 != null ? pctClass(cagr3) : ""),
    _kpi("CAGR 10Y", cagr10 != null ? fmtPct(cagr10, 1, true) : "—", cagr10 != null ? pctClass(cagr10) : ""),
    _kpi("Próximos Earnings", nextStr || "—"),
  ].join("");
}

/* ──────────────────────── widget board estilo Koyfin ──────────────── */
function _sparkInit(id, option) {
  const el = document.getElementById(id);
  if (!el) return;
  const inst = echarts.getInstanceByDom(el);
  if (inst) inst.dispose();
  echarts.init(el).setOption(option);
}

export function renderWidgetBoard(d) {
  const el = $("kw-grid");
  if (!el || !d) return;
  const ih = d.insidersHolders || {};
  const est = d.estimates || {};
  const rec = est.recommendations || {};
  const cards = [];
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const cc = { text: isDark ? "#e6ebf2" : "#1c2430", muted: isDark ? "#8996a9" : "#5e6b7d", green: isDark ? "#1ca58d" : "#0f9c8a", red: isDark ? "#f4555c" : "#e54850" };

  const buy = (rec.strongBuy || 0) + (rec.buy || 0);
  const hold = rec.hold || 0;
  const sell = (rec.sell || 0) + (rec.strongSell || 0);
  const tot = buy + hold + sell;

  if (tot > 0) {
    const pt = est.priceTargets || {};
    const cur = d.quote && d.quote.price;
    const ups = cur && pt.mean ? ((pt.mean / cur) - 1) * 100 : null;
    cards.push(`<div class="kw-card">
      <h4>Consenso de Analistas</h4>
      <div id="kw-donut" style="height:118px"></div>
      <div class="kw-legend">
        <span><i style="background:#1ca58d"></i>Comprar ${buy}</span>
        <span><i style="background:#94a3b8"></i>Mantener ${hold}</span>
        <span><i style="background:#f4555c"></i>Vender ${sell}</span>
      </div>
      ${pt.mean ? `<div class="kw-tgt"><span style="color:${cc.muted}">Objetivo medio</span><b class="k-mono">${fmtPrice(pt.mean)}${ups != null ? ` <span class="${pctClass(ups)}">${fmtPct(ups, 1, true)}</span>` : ""}</b></div>` : ""}
    </div>`);
  }



  const peSeries = (d.history && d.history.peTtm) || [];
  if (peSeries.length > 20) {
    const tail = peSeries.slice(-130);
    const vals = tail.map(p => p[1]).filter(v => v != null);
    const last = vals[vals.length - 1];
    const mn = Math.min(...vals), mx = Math.max(...vals);
    cards.push(`<div class="kw-card">
      <h4>P/E Trailing <span class="kw-sub">últimos ${tail.length} pts</span></h4>
      <div id="kw-pe" style="height:84px"></div>
      <div class="kw-legend"><span style="color:${cc.muted}">rango</span><b class="k-mono">${fmtRatio(mn, 1)}x – ${fmtRatio(mx, 1)}x</b></div>
    </div>`);
    setTimeout(() => _sparkInit("kw-pe", {
      animationDuration: 400,
      grid: { left: 6, right: 6, top: 8, bottom: 6 },
      xAxis: { type: "time", show: false },
      yAxis: { type: "value", show: false, scale: true },
      tooltip: { trigger: "axis", backgroundColor: cc.panel || "#101720", borderColor: "#2a3441", borderWidth: 1, textStyle: { color: cc.text, fontSize: 11, fontFamily: "Inter" }, formatter: p => `${new Date(p[0].value[0]).toLocaleDateString("es-CL", { month: "short", year: "2-digit" })} · ${fmtRatio(p[0].value[1], 1)}x` },
      series: [{ type: "line", data: tail, showSymbol: false, lineStyle: { color: "#4f8df7", width: 1.6 }, areaStyle: { color: "rgba(79,141,247,0.12)" } }],
    }));
  }

  el.innerHTML = cards.join("");

  if (tot > 0) {
    _sparkInit("kw-donut", {
      animationDuration: 400,
      tooltip: { trigger: "item", backgroundColor: cc.panel || "#101720", borderColor: "#2a3441", borderWidth: 1, textStyle: { color: cc.text, fontSize: 11, fontFamily: "Inter" } },
      series: [{
        type: "pie", radius: ["62%", "88%"], center: ["50%", "50%"],
        itemStyle: { borderColor: cc.panel || "#101720", borderWidth: 2, borderRadius: 4 },
        label: { show: false },
        data: [
          { value: buy, name: "Comprar", itemStyle: { color: "#1ca58d" } },
          { value: hold, name: "Mantener", itemStyle: { color: "#94a3b8" } },
          { value: sell, name: "Vender", itemStyle: { color: "#f4555c" } },
        ],
        graphic: [],
      }],
      title: { show: true, text: `${fmtNum(buy / tot * 100, 0)}%`, subtext: "Buy", left: "center", top: "33%", textStyle: { color: "#1ca58d", fontSize: 16, fontWeight: 700, fontFamily: "Inter" }, subtextStyle: { color: cc.muted, fontSize: 10 } },
    });
  }
}
