/* Dashboard / Home: carga datos del mercado, watchlist, oversold, movers, portafolio. */

import { $ } from "./dom.js?v=78";
import { fmtPct, fmtNum, fmtPrice, fmtBig, escHtml } from "./format.js?v=78";

const dash = { loaded: false };
const IDX_ICONS = { "^GSPC": "i-trend-up", "^IXIC": "i-chart", "^DJI": "i-landmark", "^N225": "i-flag", "^VIX": "i-flame" };

function dashRetry() { dash.loaded = false; }

export async function loadDashboard() {
  if (dash.loaded) return;
  dash.loaded = true;

  loadIndices();
  loadDashWatchlist();
  loadOversold();
  loadMovers();
  loadDashPortfolio();
  setupDashSearch();
}

/* ---- Índices ---- */
async function loadIndices() {
  const el = $("dash-indices");
  try {
    const r = await fetch("/api/dashboard/indices");
    const d = await r.json();
    if (!d.indices || !d.indices.length) {
      el.innerHTML = '<p class="muted">No se pudieron cargar los índices.</p>';
      return;
    }
    el.innerHTML = d.indices.map(idx => {
      const cls = idx.changePct != null ? (idx.changePct >= 0 ? "up" : "down") : "";
      const chgText = idx.changePct != null ? fmtPct(idx.changePct, 2, true) : "—";
      const sparkId = `spark-${idx.symbol.replace(/[^A-Z0-9]/g, "")}`;
      return `
        <div class="dash-index-card" data-symbol="${escHtml(idx.symbol)}">
          <div class="dash-index-head">
            <span class="dash-index-icon"><svg class="h-ico"><use href="#${IDX_ICONS[idx.symbol] || "i-chart"}"/></svg></span>
            <span class="dash-index-name">${escHtml(idx.name)}</span>
          </div>
          <div class="dash-index-price">${fmtNum(idx.price, 2)}</div>
          <div class="dash-index-chg ${cls}">${chgText}</div>
          ${idx.spark && idx.spark.length > 5 ? `<div id="${sparkId}" class="dash-spark"></div>` : ""}
        </div>`;
    }).join("");

    if (d.updatedAt) {
      const el2 = $("market-updated");
      if (el2) el2.textContent = "Actualizado: " + new Date(d.updatedAt).toLocaleTimeString("es-CL");
    }

    requestAnimationFrame(() => {
      d.indices.forEach(idx => {
        if (!idx.spark || idx.spark.length < 5) return;
        const sparkId = `spark-${idx.symbol.replace(/[^A-Z0-9]/g, "")}`;
        const container = document.getElementById(sparkId);
        if (!container || typeof echarts === "undefined") return;
        const ch = echarts.init(container, null, { renderer: "canvas" });
        const color = idx.changePct != null && idx.changePct >= 0 ? "#10b981" : "#ef4444";
        ch.setOption({
          grid: { top: 2, right: 0, bottom: 2, left: 0 },
          xAxis: { show: false, data: idx.spark.map((_, i) => i) },
          yAxis: { show: false, min: "dataMin", max: "dataMax" },
          series: [{
            type: "line", data: idx.spark, symbol: "none", smooth: true,
            lineStyle: { color, width: 1.5 },
            areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: color + "33" }, { offset: 1, color: color + "05" }] } }
          }]
        });
      });
    });
  } catch {
    el.innerHTML = '<p class="muted">Error de conexión.</p>';
    dashRetry();
  }
}

/* ---- Watchlist ---- */
async function loadDashWatchlist() {
  const el = $("dash-watchlist");
  const section = $("dash-watchlist-section");
  try {
    const r = await fetch("/api/watchlist");
    const d = await r.json();
    const items = d.items || [];
    if (!items.length) {
      section.classList.add("hidden");
      return;
    }
    el.innerHTML = `<div class="dash-wl-table-wrap"><table class="dash-wl-table">
      <thead><tr>
        <th>Empresa</th><th class="num">Precio</th><th class="num">Cambio</th>
        <th class="num">RSI</th><th class="num">PE</th><th class="num">★ MoS</th>
        <th class="center">Estado</th>
      </tr></thead>
      <tbody>${items.slice(0, 6).map(it => {
        const cur = it.currency || "USD";
        const perf = it.perf || {};
        const p1d = perf["1D"];
        const cls = p1d != null ? (p1d >= 0 ? "up" : "down") : "";
        const rsi = perf.RSI;
        let rsiCls = "";
        if (rsi != null) { if (rsi < 30) rsiCls = "up"; else if (rsi > 70) rsiCls = "down"; }
        const zone = it.inBuyZone === true
          ? '<span class="zone-chip buy">EN ZONA</span>'
          : it.inBuyZone === false ? '<span class="zone-chip wait">Esperando</span>' : '<span class="zone-chip na">—</span>';
        return `<tr data-symbol="${escHtml(it.symbol)}" class="hover-row" style="cursor:pointer;">
          <td><div style="font-weight:700;">${escHtml(it.symbol)}</div><div class="muted" style="font-size:11px;">${escHtml(it.name || "")}</div></td>
          <td class="num" style="font-weight:700;">${fmtPrice(it.price, cur)}</td>
          <td class="num ${cls}" style="font-weight:700;">${p1d != null ? fmtPct(p1d, 2, true) : "—"}</td>
          <td class="num ${rsiCls}" style="font-weight:600;">${rsi != null ? rsi.toFixed(0) : "—"}</td>
          <td class="num">${it.pe ? it.pe.toFixed(1) : "—"}</td>
          <td class="num" style="font-weight:700; color:${it.mos != null && it.mos >= 0 ? "var(--green)" : "var(--text)"};">${it.mos != null ? fmtPct(it.mos, 0, true) : "—"}</td>
          <td class="center">${zone}</td>
        </tr>`;
      }).join("")}</tbody></table></div>`;
  } catch {
    section.classList.add("hidden");
    dashRetry();
  }
}

/* ---- Sobrevendidas ---- */
async function loadOversold() {
  const el = $("dash-oversold");
  try {
    const r = await fetch("/api/dashboard/oversold");
    const d = await r.json();
    if (!d.items || !d.items.length) {
      el.innerHTML = '<p class="muted" style="padding:12px;">No hay acciones sobrevendidas en este momento.</p>';
      return;
    }
    el.innerHTML = d.items.map(it => `
      <div class="dash-mover-card" data-symbol="${escHtml(it.symbol)}">
        <div class="dash-mover-sym">${escHtml(it.symbol)}</div>
        <div class="dash-mover-name">${escHtml(it.name || "")}</div>
        <div class="dash-mover-rsi">${it.rsi}</div>
        <div class="dash-mover-chg ${it.changePct >= 0 ? "up" : "down"}">${fmtPct(it.changePct, 1, true)}</div>
      </div>`).join("");
  } catch {
    el.innerHTML = '<p class="muted">Error al cargar.</p>';
    dashRetry();
  }
}

/* ---- Movers ---- */
async function loadMovers() {
  const elG = $("dash-gainers");
  const elL = $("dash-losers");
  try {
    const r = await fetch("/api/dashboard/movers");
    const d = await r.json();
    elG.innerHTML = (d.gainers || []).map(it => moverRow(it)).join("") || '<p class="muted">Sin datos</p>';
    elL.innerHTML = (d.losers || []).map(it => moverRow(it)).join("") || '<p class="muted">Sin datos</p>';
  } catch {
    elG.innerHTML = elL.innerHTML = '<p class="muted">Error al cargar.</p>';
    dashRetry();
  }
}

function moverRow(it) {
  const cls = it.changePct >= 0 ? "up" : "down";
  return `<div class="dash-mover-row" data-symbol="${escHtml(it.symbol)}">
    <span class="dash-mover-sym">${escHtml(it.symbol)}</span>
    <span class="dash-mover-price">${fmtPrice(it.price, "USD")}</span>
    <span class="dash-mover-chg ${cls}">${fmtPct(it.changePct, 1, true)}</span>
  </div>`;
}

/* ---- Portafolio ---- */
async function loadDashPortfolio() {
  const el = $("dash-portfolio");
  const section = $("dash-portfolio-section");
  try {
    const r = await fetch("/api/portfolio");
    const d = await r.json();
    const t = d.totals;
    if (!t) {
      section.classList.add("hidden");
      return;
    }
    const retCls = t.return >= 0 ? "up" : "down";
    const alphaCls = t.alpha != null ? (t.alpha >= 0 ? "up" : "down") : "";
    el.innerHTML = `
      <div class="dash-pf-summary">
        <div class="dash-pf-stat">
          <span class="dash-pf-label">Valor Total</span>
          <span class="dash-pf-value">${fmtBig(t.value, "USD")}</span>
        </div>
        <div class="dash-pf-stat">
          <span class="dash-pf-label">Invertido</span>
          <span class="dash-pf-value">${fmtBig(t.invested, "USD")}</span>
        </div>
        <div class="dash-pf-stat">
          <span class="dash-pf-label">Retorno</span>
          <span class="dash-pf-value ${retCls}">${fmtPct(t.return, 1, true)}</span>
        </div>
        ${t.alpha != null ? `<div class="dash-pf-stat">
          <span class="dash-pf-label">Alfa vs S&P</span>
          <span class="dash-pf-value ${alphaCls}">${fmtPct(t.alpha, 1, true)}</span>
        </div>` : ""}
      </div>`;
  } catch {
    section.classList.add("hidden");
    dashRetry();
  }
}

/* ---- Búsqueda ---- */
function setupDashSearch() {
  const input = $("dash-search-input");
  const results = $("dash-search-results");
  if (!input || !results) return;
  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 1) { results.classList.add("hidden"); return; }
    timer = setTimeout(async () => {
      try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const { results: items } = await r.json();
        if (!items.length) { results.classList.add("hidden"); return; }
        results.innerHTML = items.map(it =>
          `<div class="dash-search-item" data-symbol="${escHtml(it.symbol)}">
            <span class="sym">${escHtml(it.symbol)}</span>
            <span class="name">${escHtml(it.name)}</span>
          </div>`).join("");
        results.classList.remove("hidden");
      } catch (err) {
        results.innerHTML = `<div class="dash-search-item" style="color:var(--muted);font-size:12px;">⚠ Error de búsqueda — intenta de nuevo</div>`;
        results.classList.remove("hidden");
      }
    }, 250);
  });
  input.addEventListener("blur", () => setTimeout(() => results.classList.add("hidden"), 200));
}
