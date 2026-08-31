/* Carga del análisis de un símbolo con manejo de carga/error. */

import { $ } from "./dom.js?v=77";
import { state } from "./state.js?v=77";
import { renderAnalysis } from "./analysis.js?v=77";

const LOADING_MSGS = [
  "Descargando fundamentales…",
  "Construyendo series de ratios históricos…",
  "Calculando valor intrínseco…",
  "Aplicando los criterios de Buffett…",
];

const RETRY_DELAYS = [1500, 3500];  // reintentos con backoff antes de rendirse

let _loadToken = 0;

async function fetchStock(symbol, token) {
  const url = `/api/stock/${encodeURIComponent(symbol.replace(/\//g, '-'))}`;
  let lastErr = null;
  for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
    if (attempt > 0) await new Promise(r => setTimeout(r, RETRY_DELAYS[attempt - 1]));
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (token !== _loadToken) return null;
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${r.status}`);
      }
      return r;
    } catch (e) {
      lastErr = e;
      if (token !== _loadToken) return null;
      const isNetwork = e instanceof TypeError;
      if (!isNetwork) throw e;  // error de negocio: no reintentar
    }
  }
  throw lastErr || new Error("No se pudo conectar con el servidor");
}

export async function loadSymbol(symbol) {
  const token = ++_loadToken;
  $("analysis-content").classList.add("hidden");
  $("error-box").classList.add("hidden");
  $("loading").classList.remove("hidden");
  $("loading-msg").textContent = LOADING_MSGS[0];

  let msgIdx = 0;
  const msgTimer = setInterval(() => {
    msgIdx = (msgIdx + 1) % LOADING_MSGS.length;
    $("loading-msg").textContent = LOADING_MSGS[msgIdx];
  }, 2500);

  try {
    const r = await fetchStock(symbol, token);
    if (token !== _loadToken) return;
    const json = await r.json();
    if (token !== _loadToken) return;
    state.symbol = symbol;
    state.data = json;
    renderAnalysis(state.data);
    $("analysis-content").classList.remove("hidden");
  } catch (e) {
    if (token !== _loadToken) return;
    const retryBtn = $("error-box");
    if (retryBtn) {
      retryBtn.innerHTML = `
        <span style="margin-right:8px">⚠ ${e.message || "No se pudo cargar el símbolo."}</span>
        <button class="tg-btn active" style="cursor:pointer" onclick="location.hash = '#/analisis/${encodeURIComponent(symbol)}'">Reintentar</button>`;
      retryBtn.classList.remove("hidden");
    }
  } finally {
    clearInterval(msgTimer);
    $("loading").classList.add("hidden");
  }
}

