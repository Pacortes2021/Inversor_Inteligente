/* Valoración (DCF interactivo, modelos, sensibilidad), estimaciones,
   insiders, estados financieros y paneles de valoración standalone. */

import { $, toast } from "./dom.js";
import { state } from "./state.js";
import { fmtPrice, fmtPct, fmtBig, fmtNum, fmtRatio, escHtml, pctClass } from "./format.js";
import { termify } from "./glossary.js";
import { charts } from "./charts.js";

/* ------------------------------------------- valoración + DCF live */
export function dcfJs(inp, growth, discount, terminal) {
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

export function renderValuationCard(d) {
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

export function renderModels(d, dcfLive) {
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

/* ------------------------------------------------ matriz sensibilidad */
export function renderSensitivity(d, g, r, t) {
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
export function renderRatiosGrid(d) {
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

export function renderEpsEstimatesChart(est) {
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

/* -------------------------------------------------- estimates & insiders */
export function renderGrowthEstimatesGrid(grid) {
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
      <td style="font-weight:700; color:var(--text); padding:12px 16px;">${escHtml(row.label)}</td>`;

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

export function renderEpsValuationCalculator(d) {
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

export function renderEstimates(est) {
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

export function renderInsidersHolders(ih) {
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
          <td>${escHtml(r.date || '—')}</td>
          <td><b>${escHtml(r.insider)}</b></td>
          <td>${escHtml(r.position || '—')} <span style="${txnColor}">${txn !== '—' ? '· ' + escHtml(txn) : ''}</span></td>
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
        <td><b>${escHtml(r.holder)}</b></td>
        <td class="num">${r.shares != null ? Math.round(r.shares).toLocaleString() : '—'}</td>
        <td class="num">${r.value != null ? '$' + Math.round(r.value).toLocaleString() : '—'}</td>
        <td class="num ${r.pctChange != null && r.pctChange >= 0 ? 'up' : 'down'}">${r.pctChange != null ? fmtPct(r.pctChange * 100, 2, true) : '—'}</td>
        <td>${escHtml(r.date || '—')}</td>
      </tr>
    `).join('') : '<tr><td colspan="5" class="num muted" style="text-align:center;">Sin registros recientes de fondos institucionales</td></tr>';
  }
}

/* ------------------------------------- financial statement explorer */
let currentFinStmt = "income";
let currentFinFreq = "annual";

export function renderFinancialStatements(d, stmtType = currentFinStmt, freqType = currentFinFreq) {
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

/* --------------------------------- standalone valuation & historical panes */
export function renderEpsFv(d) {
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

export function renderDcfFv(d) {
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

export function renderDdmFv(d) {
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

export function renderHistoricalRatios(d) {
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

export function renderAdditional(d) {
  const container = $("additional-details");
  if (!container) return;
  const p = d.profile;
  const q = d.quote;

  const safeUrl = (u) => {
    if (!u) return "#";
    const s = String(u).trim();
    if (/^(https?:|mailto:)/i.test(s)) return escHtml(s);
    return "#";
  };

  let filingsHtml = '<span class="muted" style="font-size:12px;">Sin documentos recientes</span>';
  if (p.secFilings) {
    if (Array.isArray(p.secFilings)) {
      filingsHtml = p.secFilings.map(f => `<a href="${safeUrl(f.url)}" target="_blank" rel="noopener" class="btn btn-sm">${escHtml(f.form)} (${escHtml(f.date)})</a>`).join('');
    } else if (typeof p.secFilings === 'object') {
      filingsHtml = Object.entries(p.secFilings).map(([type, url]) =>
        `<a href="${safeUrl(url)}" target="_blank" rel="noopener" class="btn btn-sm">${type === 'annual' ? '📄 10-K Anual (SEC)' : '📄 10-Q Trimestral (SEC)'}</a>`
      ).join('');
    }
  }

  container.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);">
        <h4 style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:10px;">Perfil de la Empresa</h4>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Nombre:</b> ${escHtml(p.name)}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Sector:</b> ${escHtml(p.sector || '—')}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Industria:</b> ${escHtml(p.industry || '—')}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>País:</b> ${escHtml(p.country || '—')}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Bolsa:</b> ${escHtml(p.exchange || '—')}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Empleados:</b> ${p.employees ? p.employees.toLocaleString() : '—'}</p>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Sitio Web:</b> <a href="${safeUrl(p.website)}" target="_blank" rel="noopener" style="color:var(--primary); text-decoration:underline;">${escHtml(p.website || '—')}</a></p>
      </div>

      <div style="padding:16px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);">
        <h4 style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:10px;">Datos de Mercado y Archivos SEC</h4>
        <p style="font-size:12.5px; color:var(--text); margin-bottom:6px;"><b>Próximos Resultados:</b> ${escHtml(p.nextEarnings || 'Por confirmar')}</p>
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
