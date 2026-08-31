/* Watchlist: acciones seguidas con margen de seguridad objetivo. */

import { $, toast, apiFetch } from "./dom.js?v=79";
import { state } from "./state.js?v=79";
import { setStarState } from "./analysis.js?v=79";
import { fmtBig, fmtPrice, fmtPct, escHtml } from "./format.js?v=79";

export let wlLoaded = false;
let wlItems = [];
let wlPeriod = '1D';

export async function loadWatchlist(refresh = false) {
  if (wlLoaded && !refresh) return;
  document.getElementById("wl-loading").classList.remove("hidden");
  document.getElementById("wl-table").classList.add("hidden");
  document.getElementById("wl-empty").classList.add("hidden");
  try {
    const r = await fetch("/api/watchlist");
    const { items } = await r.json();
    wlLoaded = true;
    wlItems = items || [];
    renderWatchlist();
  } catch (e) {
    toast("⚠ Error cargando watchlist: " + e.message);
  } finally {
    document.getElementById("wl-loading").classList.add("hidden");
  }
}

let wlSortCol = 'marketCap';
let wlSortAsc = false;

export function wlSort(col) {
  if (wlSortCol === col) {
    wlSortAsc = !wlSortAsc;
  } else {
    wlSortCol = col;
    wlSortAsc = false;
  }
  renderWatchlist();
}

function updateSortHeaders() {
  const cols = ['symbol', 'price', 'perf', 'marketCap', 'rsi', 'pe', 'forwardPe', 'divYield', 'targetBase', 'targetPessimistic', 'targetOpt'];
  cols.forEach(c => {
    const el = document.getElementById('sort-' + c);
    if (el) el.innerText = (wlSortCol === c) ? (wlSortAsc ? ' ▲' : ' ▼') : '';
  });
}

function getDivAccumulated4y(it) {
  const px = it.price || 0;
  const y = it.divYield || 0;
  if (y <= 0.05 || px <= 0) return 0;
  const annualDiv = px * (y / 100);
  let acc = 0;
  let cur = annualDiv;
  for (let i = 1; i <= 4; i++) {
    cur *= 1.05;
    acc += cur;
  }
  return acc;
}

function renderWatchlist() {
  const items = wlItems;
  if (!items || !items.length) {
    document.getElementById("wl-empty").classList.remove("hidden");
    document.getElementById("wl-table").classList.add("hidden");
    return;
  }

  const chkWlDivs = document.getElementById("wl-chk-divs");
  if (chkWlDivs && !chkWlDivs.dataset.bound) {
    chkWlDivs.dataset.bound = "true";
    chkWlDivs.addEventListener("change", () => renderWatchlist());
  }
  const includeDivs = chkWlDivs ? chkWlDivs.checked : false;
  
  // Lógica de ordenamiento segura sin mutación descontrolada
  const sortedItems = [...items].sort((a, b) => {
    let valA, valB;
    if (wlSortCol === 'perf') {
      valA = a.perf?.[wlPeriod] ?? -999999;
      valB = b.perf?.[wlPeriod] ?? -999999;
    } else if (wlSortCol === 'rsi') {
      valA = a.perf?.RSI ?? -999999;
      valB = b.perf?.RSI ?? -999999;
    } else if (wlSortCol === 'symbol') {
      valA = a.symbol || "";
      valB = b.symbol || "";
    } else {
      valA = a[wlSortCol] ?? -999999;
      valB = b[wlSortCol] ?? -999999;
    }
    
    if (typeof valA === 'string' && typeof valB === 'string') {
      return wlSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    const numA = Number(valA) || -999999;
    const numB = Number(valB) || -999999;
    return wlSortAsc ? (numA - numB) : (numB - numA);
  });
  
  updateSortHeaders();
  const tbody = document.querySelector("#wl-table tbody");
  if (!tbody) return;
  tbody.innerHTML = sortedItems.map(it => {
    const cur = it.currency || "USD";
    const px = it.price;
    const mcap = it.marketCap ? fmtBig(it.marketCap, cur) : "—";
    const pe = it.pe ? it.pe.toFixed(1) : "—";
    const fpe = it.forwardPe ? it.forwardPe.toFixed(1) : "—";
    const divYieldVal = it.divYield != null && it.divYield > 0.05 ? `${it.divYield.toFixed(2)}%` : "—";
    const divYieldHtml = divYieldVal !== "—" 
      ? `<span style="color:var(--primary, #10b981); font-weight:700;">${divYieldVal}</span>`
      : `<span class="muted">—</span>`;
    const div4y = getDivAccumulated4y(it);
    
    // Rendimiento actual según wlPeriod
    const perfData = it.perf || {};
    const perfVal = perfData[wlPeriod];
    const perfHtml = perfVal != null 
        ? `<span style="color:${perfVal >= 0 ? 'var(--green)' : 'var(--red)'}; font-weight:700;">${perfVal > 0 ? '+' : ''}${perfVal.toFixed(2)}%</span>`
        : `<span class="muted">—</span>`;
        
    const rsi = perfData.RSI;
    let rsiHtml = `<span class="muted">—</span>`;
    if (rsi != null) {
        let rsiColor = 'var(--text)';
        if (rsi < 30) rsiColor = 'var(--green)';
        if (rsi > 70) rsiColor = 'var(--red)';
        rsiHtml = `<span style="color:${rsiColor}; font-weight:600;">${rsi.toFixed(1)}</span>`;
    }

    // Targets por escenario con badge de retorno anualizado (CAGR %/año) para fácil comparación con S&P 500 (~10%/a)
    const tgtCell = (val) => {
      if (val == null || px == null || px <= 0) return `<td class="num">—</td>`;
      const finalVal = includeDivs ? (val + div4y) : val;
      const totalReturnPct = ((finalVal - px) / px) * 100;

      let cagrPct = 0;
      if (finalVal > 0 && px > 0) {
        cagrPct = (Math.pow(finalVal / px, 0.25) - 1) * 100;
      } else {
        cagrPct = totalReturnPct;
      }

      const isAbove = cagrPct >= 0;
      const titleAttr = includeDivs && div4y > 0 
        ? `Retorno Total 4A: ${totalReturnPct > 0 ? '+' : ''}${totalReturnPct.toFixed(1)}% | Precio 2030E (${fmtPrice(val, cur)}) + Dividendos (${fmtPrice(div4y, cur)})` 
        : `Retorno Acumulado 4A: ${totalReturnPct > 0 ? '+' : ''}${totalReturnPct.toFixed(1)}% | Precio Objetivo 2030E (${fmtPrice(val, cur)})`;

      return `<td class="num" style="white-space:nowrap;" title="${escHtml(titleAttr)}">
        <span style="font-weight:700;">${fmtPrice(finalVal, cur)}</span>
        <span style="font-size:10.5px; margin-left:3px; padding:2px 5px; border-radius:4px; font-weight:700;
          background:${isAbove ? 'rgba(16,185,129,0.14)' : 'rgba(239,68,68,0.14)'};
          color:${isAbove ? 'var(--green)' : 'var(--red)'}">
          ${isAbove ? '+' : ''}${cagrPct.toFixed(1)}%/a
        </span>
      </td>`;
    };

    return `<tr style="transition: background 0.2s; cursor:default;" class="hover-row">
      <td data-symbol="${escHtml(it.symbol)}">
          <div style="font-weight:800; font-size:15px; color:var(--text); cursor:pointer;">${escHtml(it.symbol)}</div>
          <div style="font-size:11px; color:var(--muted); max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escHtml(it.name || "—")}</div>
      </td>
      <td class="num" style="font-weight:700; font-size:14px;">${fmtPrice(px, cur)}</td>
      <td class="num">${perfHtml}</td>
      <td class="num" style="font-size:12px;">${mcap}</td>
      <td class="num">${rsiHtml}</td>
      <td class="num" style="font-size:13px; font-weight:600;">${pe}</td>
      <td class="num" style="font-size:13px; font-weight:600;">${fpe}</td>
      <td class="num" style="font-size:13px;">${divYieldHtml}</td>
      ${tgtCell(it.targetBase)}
      ${tgtCell(it.targetPessimistic)}
      ${tgtCell(it.targetOpt)}
      <td class="center">
          <button style="background:transparent; border:none; cursor:pointer; color:var(--muted); padding:6px; border-radius:50%; transition:all 0.2s;" 
                  onmouseover="this.style.background='var(--hover)'; this.style.color='var(--red)';"
                  onmouseout="this.style.background='transparent'; this.style.color='var(--muted)';"
                  data-wl-remove="${escHtml(it.symbol)}" title="Dejar de seguir">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </button>
      </td>
    </tr>`;
  }).join("");
  document.getElementById("wl-table").classList.remove("hidden");
}

/* Delegación de Eventos para Toggles de Periodo */
document.addEventListener("click", e => {
  const btn = e.target.closest('#wl-perf-toggles .tg-btn');
  if (btn) {
    document.querySelectorAll('#wl-perf-toggles .tg-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    wlPeriod = btn.getAttribute('data-period') || '1D';
    renderWatchlist();
  }
});

export async function wlAdd(symbol, targetMos = 25) {
  try {
    const r = await apiFetch("/api/watchlist", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, targetMos }),
    });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    wlLoaded = false;
    toast(`★ ${symbol} agregada a Favoritos. ¿Quieres ajustar el MoS objetivo?`);
  } catch (e) {
    toast("⚠ No se pudo agregar: " + e.message);
  }
}

export async function wlRemove(symbol) {
  try {
    const r = await apiFetch(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    wlLoaded = false;
    toast(`${symbol} eliminada de la watchlist`);
    if (state.data && state.data.symbol === symbol) setStarState(false);
  } catch (e) {
    toast("⚠ No se pudo eliminar: " + e.message);
  }
  loadWatchlist(true);
}

export async function wlSetTarget(symbol, value) {
  const t = parseFloat(value);
  if (!isFinite(t)) return;
  try {
    const r = await apiFetch("/api/watchlist", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, targetMos: t }),
    });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    wlLoaded = false;
    toast(`Objetivo de ${symbol} actualizado a MoS ≥ ${t}%`);
  } catch (e) {
    toast("⚠ No se pudo actualizar: " + e.message);
  }
  // loadWatchlist(true); // Omitimos recarga forzada para no perder el foco
}

/* Permite a otros módulos invalidar la caché de la watchlist. */
export function wlInvalidate() { wlLoaded = false; }

document.getElementById("wl-refresh").addEventListener("click", () => loadWatchlist(true));

/* Exportar Watchlist a CSV */
document.getElementById("wl-csv").addEventListener("click", async () => {
  try {
    const items = wlItems;
    if (!items || !items.length) return toast("No hay acciones en la watchlist");
    const esc = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
    const headers = ["Símbolo", "Empresa", "Precio", "Rendimiento 1D", "RSI", "MoS Actual %", "MoS Objetivo %", "En Zona de Compra"];
    const rows = items.map(it => [
      esc(it.symbol), esc(it.name), esc(it.price), esc(it.perf?.['1D']), esc(it.perf?.RSI), esc(it.mos),
      esc(it.targetMos), esc(it.inBuyZone ? "SÍ" : "NO")
    ]);
    const csvContent = [headers.map(esc).join(";"), ...rows.map(r => r.join(";"))].join("\n");
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `watchlist_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Watchlist exportada a CSV ✓");
  } catch (err) {
    toast("⚠ Error exportando CSV: " + err.message);
  }
});

document.addEventListener("click", e => {
  const rm = e.target.closest("[data-wl-remove]");
  if (rm) wlRemove(rm.getAttribute("data-wl-remove"));
});

/* Orden de columnas: los <th> de la tabla estática llevan data-k="col". */
document.addEventListener("click", e => {
  const th = e.target.closest("#wl-table th[data-k]");
  if (th) wlSort(th.dataset.k);
});
