/* Portafolio: posiciones, concentración por sector y respaldo de datos. */

import { toast, apiFetch } from "./dom.js?v=77";
import { fmtBig, fmtNum, fmtPct, fmtPrice, escHtml, pctClass } from "./format.js?v=77";
import { getChartColors } from "./charts.js?v=77";
import { refreshSidebar } from "./analysis.js?v=77";
import { wlInvalidate } from "./watchlist.js?v=77";

let pfLoaded = false;
let pfSectorChartInstance = null;

export async function loadPortfolio(refresh = false) {
  if (pfLoaded && !refresh) return;
  document.getElementById("pf-loading").classList.remove("hidden");
  document.getElementById("pf-table").classList.add("hidden");
  document.getElementById("pf-empty").classList.add("hidden");
  document.getElementById("pf-summary-grid").classList.add("hidden");
  document.getElementById("pf-sector-card").classList.add("hidden");
  try {
    const r = await fetch("/api/portfolio");
    const data = await r.json();
    pfLoaded = true;
    renderPortfolio(data);
  } catch (e) {
    toast("⚠ Error cargando portafolio: " + e.message);
  } finally {
    document.getElementById("pf-loading").classList.add("hidden");
  }
}

function renderPortfolio({ positions, totals }) {
  if (!positions.length) {
    document.getElementById("pf-empty").classList.remove("hidden");
    document.getElementById("pf-summary-grid").classList.add("hidden");
    document.getElementById("pf-sector-card").classList.add("hidden");
    return;
  }

  // Actualizar resumen del portafolio
  if (totals) {
    document.getElementById("pf-sum-val").textContent = fmtBig(totals.value, "USD");
    document.getElementById("pf-sum-inv").textContent = "Invertido: " + fmtBig(totals.invested, "USD");
    
    const profit = totals.value - totals.invested;
    const profitEl = document.getElementById("pf-sum-profit");
    profitEl.textContent = (profit >= 0 ? "+" : "") + fmtBig(profit, "USD");
    profitEl.className = "card-value " + (profit >= 0 ? "up" : "down");
    
    const profitPctEl = document.getElementById("pf-sum-profit-pct");
    profitPctEl.textContent = fmtPct(totals.return, 1, true);
    profitPctEl.className = "card-subtext " + (totals.return >= 0 ? "up" : "down");
    
    const alphaEl = document.getElementById("pf-sum-alpha");
    if (totals.alpha != null) {
      alphaEl.textContent = fmtPct(totals.alpha, 1, true);
      alphaEl.className = "card-value " + (totals.alpha >= 0 ? "up" : "down");
      document.getElementById("pf-sum-alpha-lbl").textContent = totals.alpha >= 0 ? "Ganando al S&P 500 ✓" : "S&P 500 rinde más";
    }
    
    // Posición Top por valor
    const sortedByVal = [...positions].sort((a, b) => (b.value || 0) - (a.value || 0));
    const topPos = sortedByVal[0];
    if (topPos) {
      const pct = totals.value > 0 ? ((topPos.value / totals.value) * 100).toFixed(1) : "0.0";
      document.getElementById("pf-sum-top").textContent = topPos.symbol;
      document.getElementById("pf-sum-top-val").textContent = fmtBig(topPos.value, "USD") + ` (${pct}%)`;
    }
    document.getElementById("pf-sum-count").textContent = positions.length;
    document.getElementById("pf-summary-grid").classList.remove("hidden");
  }

  // Renderizar gráfico de distribución por sector si ECharts está listo
  renderPortfolioSectorChart(positions, totals);

  const tbody = document.querySelector("#pf-table tbody");
  tbody.innerHTML = positions.map(p => {
    // Badge de % del portafolio
    const pct = p.pctOfPortfolio;
    let pctBg = 'rgba(16,185,129,0.12)', pctFg = 'var(--green)';
    if (pct > 25) { pctBg = 'rgba(239,68,68,0.12)'; pctFg = 'var(--red)'; }
    else if (pct > 15) { pctBg = 'rgba(217,119,6,0.12)'; pctFg = 'var(--gold)'; }
    const pctCell = pct != null
      ? `<td class="num"><span style="padding:2px 7px; border-radius:5px; font-size:11px; font-weight:700; background:${pctBg}; color:${pctFg}">${pct.toFixed(1)}%${p.overConcentrated ? ' ⚠' : ''}</span></td>`
      : `<td class="num">—</td>`;

    return `<tr${p.overConcentrated ? ' style="background:rgba(239,68,68,0.03)"' : ''}>
      <td class="sym" data-symbol="${escHtml(p.symbol)}" style="cursor:pointer;">${escHtml(p.symbol)}</td>
      <td>${escHtml(p.date)}</td>
      <td class="num">${fmtNum(p.price, 2)}</td>
      <td class="num">${p.priceNow != null ? fmtNum(p.priceNow, 2) : "—"}</td>
      <td class="num">${fmtNum(p.shares, p.shares % 1 ? 2 : 0)}</td>
      <td class="num">${p.value != null ? fmtBig(p.value, "USD") : "—"}</td>
      ${pctCell}
      <td class="num ${pctClass(p.return)}"><b>${fmtPct(p.return, 1, true)}</b></td>
      <td class="num ${pctClass(p.spyReturn)}">${fmtPct(p.spyReturn, 1, true)}</td>
      <td class="num"><span class="alpha-chip ${p.alpha == null ? "" : p.alpha >= 0 ? "hi" : "lo"}">${fmtPct(p.alpha, 1, true)}</span></td>
      <td class="pf-note-cell" title="${escHtml(p.note || "")}">${escHtml(p.note || "—")}</td>
      <td><button class="btn-x" data-pf-remove="${p.id}" title="Eliminar">✕</button></td>
    </tr>`;
  }).join("");

  const tfoot = document.querySelector("#pf-table tfoot");
  tfoot.innerHTML = totals ? `
    <tr class="pf-totals">
      <td colspan="5"><b>Total</b> · invertido ${fmtBig(totals.invested, "USD")}</td>
      <td class="num"><b>${fmtBig(totals.value, "USD")}</b></td>
      <td></td>
      <td class="num ${pctClass(totals.return)}"><b>${fmtPct(totals.return, 1, true)}</b></td>
      <td class="num ${pctClass(totals.spyReturn)}">${fmtPct(totals.spyReturn, 1, true)}</td>
      <td class="num"><span class="alpha-chip ${totals.alpha == null ? "" : totals.alpha >= 0 ? "hi" : "lo"}"><b>${fmtPct(totals.alpha, 1, true)}</b></span></td>
      <td colspan="2">${totals.alpha != null ? (totals.alpha >= 0 ? "le estás ganando al índice ✓" : "el índice te está ganando — Buffett recomendaría el ETF") : ""}</td>
    </tr>` : "";
  document.getElementById("pf-table").classList.remove("hidden");
}

function renderPortfolioSectorChart(positions, totals) {
  const chartEl = document.getElementById("pf-sector-chart");
  const cardEl = document.getElementById("pf-sector-card");
  if (!chartEl || !cardEl || !positions.length) return;

  // Agrupar por SECTOR (no por símbolo)
  const bySector = {};
  positions.forEach(p => {
    const sec = p.sector || p.symbol; // fallback a símbolo si no hay sector
    bySector[sec] = (bySector[sec] || 0) + (p.value || 0);
  });

  const total = Object.values(bySector).reduce((a, b) => a + b, 0);
  const chartData = Object.entries(bySector)
    .map(([name, value]) => ({ name, value: +value.toFixed(2) }))
    .sort((a, b) => b.value - a.value);

  // Alertas de concentración > 25%
  const overConc = positions.filter(p => p.overConcentrated);
  const alertDiv = document.getElementById("pf-concentration-alert");
  if (alertDiv) {
    if (overConc.length > 0) {
      alertDiv.innerHTML = `⚠️ <b>Concentración alta:</b> ${overConc.map(p =>
        `<span style="font-weight:700; color:var(--gold)">${escHtml(p.symbol)} (${p.pctOfPortfolio?.toFixed(1)}%)</span>`
      ).join(", ")} supera el 25% del portafolio. Considera diversificar.`;
      alertDiv.classList.remove("hidden");
    } else {
      alertDiv.classList.add("hidden");
    }
  }

  cardEl.classList.remove("hidden");
  if (typeof echarts === "undefined") return;
  if (!pfSectorChartInstance) {
    pfSectorChartInstance = echarts.init(chartEl);
  }
  const cc = typeof getChartColors === "function" ? getChartColors() : { muted: "#64748b", panel: "#ffffff" };

  const SECTOR_COLORS = {
    "Technology": "#3b82f6", "Consumer Cyclical": "#f59e0b", "Healthcare": "#10b981",
    "Financial Services": "#8b5cf6", "Communication Services": "#0ea5e9",
    "Industrials": "#64748b", "Consumer Defensive": "#d97706", "Energy": "#ef4444",
    "Basic Materials": "#6b7280", "Real Estate": "#ec4899", "Utilities": "#14b8a6", "Otro": "#94a3b8"
  };

  pfSectorChartInstance.setOption({
    tooltip: {
      trigger: "item",
      formatter: p => `${p.name}<br/><b>$${p.value.toLocaleString("es-CL", {maximumFractionDigits:0})}</b> (${p.percent.toFixed(1)}%)`
    },
    legend: {
      orient: "vertical", right: 10, top: "center",
      textStyle: { color: cc.muted, fontSize: 11 }
    },
    series: [{
      name: "Sector",
      type: "pie",
      radius: ["42%", "72%"],
      center: ["38%", "50%"],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 6,
        borderColor: cc.panel || "#fff",
        borderWidth: 2,
        color: p => SECTOR_COLORS[p.name] || "#94a3b8"
      },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: "bold" } },
      data: chartData,
    }]
  }, true);
}

export async function pfRemove(id) {
  try {
    const r = await apiFetch(`/api/portfolio/${id}`, { method: "DELETE" });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    toast("Posición eliminada");
  } catch (e) {
    toast("⚠ No se pudo eliminar: " + e.message);
  }
  loadPortfolio(true);
}

document.getElementById("pf-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    symbol: document.getElementById("pf-symbol").value.trim().toUpperCase(),
    date: document.getElementById("pf-date").value,
    price: parseFloat(document.getElementById("pf-price").value),
    shares: parseFloat(document.getElementById("pf-shares").value),
    note: document.getElementById("pf-note").value,
  };
  if (!body.symbol || !body.date || !isFinite(body.price) || !isFinite(body.shares)) return;
  try {
    const r = await apiFetch("/api/portfolio", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    e.target.reset();
    toast(`Compra de ${body.symbol} registrada`);
  } catch (err) {
    toast("⚠ No se pudo registrar: " + err.message);
  }
  loadPortfolio(true);
});

document.getElementById("pf-refresh").addEventListener("click", () => loadPortfolio(true));

/* Exportar Portafolio a CSV */
document.getElementById("pf-csv").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/portfolio");
    const { positions } = await r.json();
    if (!positions || !positions.length) return toast("No hay posiciones para exportar");
    const esc = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
    const headers = ["Símbolo", "Fecha", "Precio Compra", "Precio Actual", "Cantidad", "Valor Total", "Retorno %", "Retorno S&P 500 %", "Alfa %", "Nota"];
    const rows = positions.map(p => [
      esc(p.symbol), esc(p.date), esc(p.price), esc(p.priceNow), esc(p.shares),
      esc(p.value), esc(p.return), esc(p.spyReturn), esc(p.alpha), esc(p.note)
    ]);
    const csvContent = [headers.map(esc).join(";"), ...rows.map(r => r.join(";"))].join("\n");
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `portafolio_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Portafolio exportado a CSV ✓");
  } catch (err) {
    toast("⚠ Error exportando CSV: " + err.message);
  }
});

/* -------------------------------------------------- respaldo de datos */
document.getElementById("pf-export").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/backup");
    if (!r.ok) throw new Error(`Error ${r.status}`);
    const data = await r.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `inversor_respaldo_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Respaldo exportado (watchlist + portafolio + notas) ✓");
  } catch (err) {
    toast("⚠ Error exportando respaldo: " + err.message);
  }
});

document.getElementById("pf-import").addEventListener("click", () =>
  document.getElementById("pf-import-file").click());

document.getElementById("pf-import-file").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    const r = await apiFetch("/api/restore", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error("respuesta " + r.status);
    toast("Respaldo restaurado ✓");
    wlInvalidate(); pfLoaded = false;
    loadPortfolio(true);
    refreshSidebar();
  } catch (err) {
    toast("⚠ Archivo de respaldo inválido: " + err.message);
  } finally {
    e.target.value = "";
  }
});

document.addEventListener("click", e => {
  const rm = e.target.closest("[data-pf-remove]");
  if (rm) pfRemove(Number(rm.getAttribute("data-pf-remove")));
});
