/* Carga del análisis de un símbolo con manejo de carga/error. */

import { $ } from "./dom.js";
import { state } from "./state.js";
import { renderAnalysis } from "./analysis.js";

const LOADING_MSGS = [
  "Descargando fundamentales…",
  "Construyendo series de ratios históricos…",
  "Calculando valor intrínseco…",
  "Aplicando los criterios de Buffett…",
];

let _loadToken = 0;

export async function loadSymbol(symbol) {
  const token = ++_loadToken;
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
    const r = await fetch(`/api/stock/${encodeURIComponent(symbol.replace(/\//g, '-'))}`);
    if (token !== _loadToken) return; // respuesta obsoleta
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${r.status}`);
    }
    state.data = await r.json();
    if (token !== _loadToken) return;
    renderAnalysis(state.data);
  } catch (e) {
    if (token !== _loadToken) return;
    $("error-box").textContent = "⚠ " + (e.message || "No se pudo cargar el símbolo.");
    $("error-box").classList.remove("hidden");
  } finally {
    clearInterval(msgTimer);
    $("loading").classList.add("hidden");
  }
}
