/* Punto de entrada (ES module). Importa todos los módulos con efectos y
   conecta los handlers globales restantes, luego arranca el routing. */

import { $, toast } from "./dom.js?v=75";
import { state, setCurrentPeriodYears } from "./state.js?v=75";
import { priceView } from "./charts.js?v=75";
import { route } from "./router.js?v=75";
import { chartPriceSummary, sbSetHidden, refreshSidebar, setStarState, updateCagrModal, triggerTabSpecificActions } from "./analysis.js?v=75";
import { renderAlertsList, getAlerts, saveAlerts } from "./alerts.js?v=75";
import { wlAdd, wlRemove } from "./watchlist.js?v=75";
import { cmpAdd } from "./compare.js?v=75";

// Módulos con efectos laterales al cargarse (bindings de DOM propios).
import "./theme.js?v=75";
import "./charts.js?v=75";
import "./glossary.js?v=75";
import "./screener.js?v=75";
import "./watchlist.js?v=75";
import "./portfolio.js?v=75";
import "./dashboard.js?v=75";
import "./mobile-nav.js?v=75";

// Compat para consola del desarrollador.
window.state = state;

/* --------------------- red de seguridad global ---------------------
   Cualquier excepción no capturada se muestra como toast y se loguea,
   en vez de dejar la app muerta o en blanco. */
let _lastErrTs = 0;
const _errToast = (msg) => {
  const now = Date.now();
  if (now - _lastErrTs < 4000) return;  // evita cascada de toasts
  _lastErrTs = now;
  console.error("[app]", msg);
  try { toast("⚠ Error interno: " + msg.slice(0, 90)); } catch { /* toast no disponible */ }
};
window.addEventListener("error", (ev) => {
  ev.preventDefault?.();
  _errToast(ev.message || "error de script");
});
window.addEventListener("unhandledrejection", (ev) => {
  ev.preventDefault?.();
  const msg = ev.reason?.message || String(ev.reason || "promesa rechazada");
  _errToast(msg);
});

// Click handlers en los tabs de acción del HTML
document.querySelectorAll(".action-tabs .a-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    const pane = btn.dataset.pane;
    if (state.symbol) {
      location.hash = `#/analisis/${state.symbol}/${pane}`;
    }
  });
});

/* ---------------------------- toggles del gráfico de Summary */
if ($("tg-area")) {
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
  $("tg-trend").onclick = () => {
    priceView.trend = !priceView.trend;
    $("tg-trend").classList.toggle("active", priceView.trend);
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
      setCurrentPeriodYears(parseFloat(btn.dataset.years));
      chartPriceSummary(state.data);
    };
  });
}

/* -------------------------------------------- modales y botones */
if ($("btn-add-note")) {
  $("btn-add-note").onclick = () => {
    location.hash = `#/analisis/${state.symbol}/qualitative`;
  };
}

if ($("cagr-in-principal")) {
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
}

if ($("btn-export-pdf")) $("btn-export-pdf").onclick = () => window.print();

if ($("btn-compare")) {
  $("btn-compare").onclick = () => {
    if (state.data) {
      cmpAdd(state.data.symbol);
      location.hash = "#/comparar";
    }
  };
}

if ($("btn-watch")) {
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
}

/* ------------------------------------------------ alertas */
if ($("btn-alerts")) {
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
}

/* ------------------------------------------------ sidebar favoritos */
if ($("sb-close")) {
  $("sb-close").addEventListener("click", () => sbSetHidden(true));
  $("sb-open").addEventListener("click", () => { sbSetHidden(false); refreshSidebar(); });

  sbSetHidden(localStorage.getItem("sb_hidden") === "1");
  refreshSidebar();
  setInterval(refreshSidebar, 120000);
}

/* Al cambiar el tema, re-renderizar la pestaña activa (gráficos ECharts). */
document.addEventListener("theme-changed", () => {
  if (state.data) triggerTabSpecificActions(state.activeTab);
});

/* ----------------------------------------------------------------- init */
route();
