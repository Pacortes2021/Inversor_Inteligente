/* Routing por hash + búsqueda global + navegación delegada. */

import { $ } from "./dom.js";
import { state } from "./state.js";
import { escHtml } from "./format.js";
import { loadSymbol } from "./loader.js";
import { triggerTabSpecificActions } from "./analysis.js";
import { loadDashboard } from "./dashboard.js";
import { loadScreener } from "./screener.js";
import { loadWatchlist } from "./watchlist.js";
import { loadPortfolio } from "./portfolio.js";

export const VIEWS = ["inicio", "analisis", "screener", "comparar", "watchlist", "portafolio"];
export const UNLOCKED_TABS = ["summary", "valuation", "financials-hub", "ownership", "financials", "ratios", "rating", "estimates", "insiders", "eps-fv", "dcf-fv", "ddm-fv", "historical-ratios", "dividends", "earnings", "qualitative", "additional"];

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

export function hideSearch() {
  const el = $("search-results");
  if (el) el.classList.add("hidden");
}

export function go(symbol) {
  hideSearch();
  $("search-input").value = "";
  location.hash = `#/analisis/${encodeURIComponent(symbol)}/${state.activeTab || "summary"}`;
}

export function route() {
  const hash = location.hash || "#/inicio";
  let current = VIEWS.find(v => hash.startsWith(`#/${v}`)) || "inicio";

  for (const v of VIEWS) {
    $(`view-${v}`).classList.toggle("hidden", v !== current);
    $(`tab-${v}`).classList.toggle("active", v === current);
  }

  if (current === "inicio") loadDashboard();
  else if (current === "screener") loadScreener();
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

window.addEventListener("hashchange", route);

/* -------------------------------------------- búsqueda global */
let searchTimer = null;
let _searchToken = 0;

async function doSearch(q) {
  const token = ++_searchToken;
  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!r.ok) throw new Error(`Error ${r.status}`);
    const { results } = await r.json();
    if (token !== _searchToken) return;
    const box = $("search-results");
    if (!results.length) return hideSearch();
    box.innerHTML = results.map(it =>
      `<div class="search-item" data-symbol="${escHtml(it.symbol)}">
         <span class="sym">${escHtml(it.symbol)}</span>
         <span class="name">${escHtml(it.name)}</span>
         <span class="ex">${escHtml(it.exchange)}</span>
       </div>`).join("");
    box.classList.remove("hidden");
  } catch { if (token === _searchToken) hideSearch(); }
}

const searchInput = $("search-input");
if (searchInput) {
  searchInput.addEventListener("input", e => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    if (q.length < 2) return hideSearch();
    searchTimer = setTimeout(() => doSearch(q), 280);
  });
  searchInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      const q = e.target.value.trim().toUpperCase();
      if (q) go(q);
    }
    if (e.key === "Escape") hideSearch();
  });
}

document.addEventListener("click", e => {
  if (!e.target.closest(".search-box")) hideSearch();
});

document.addEventListener("click", e => {
  const item = e.target.closest(".search-item");
  if (item && item.dataset.symbol) {
    go(item.dataset.symbol);
    return;
  }
  if (!e.target.closest(".search-box")) hideSearch();
});

/* Navegación delegada: cualquier elemento con data-symbol (dashboard, tablas, sidebar). */
document.addEventListener("click", e => {
  const sym = e.target.closest("[data-symbol]");
  if (sym && sym.dataset.symbol) go(sym.dataset.symbol);
});

document.addEventListener("click", e => {
  const item = e.target.closest(".sb-item[data-symbol]");
  if (item) go(item.getAttribute("data-symbol"));
});

/* Accesos rápidos del dashboard: data-go="SYM" → navega al análisis. */
document.addEventListener("click", e => {
  const chip = e.target.closest("[data-go]");
  if (chip && chip.dataset.go) go(chip.dataset.go);
});

/* Logo/brand: data-go-home → vuelve al inicio. */
document.addEventListener("click", e => {
  if (e.target.closest("[data-go-home]")) {
    hideSearch();
    location.hash = "#/inicio";
  }
});
