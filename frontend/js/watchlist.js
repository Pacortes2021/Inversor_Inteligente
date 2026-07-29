/* Watchlist: acciones seguidas con margen de seguridad objetivo. */

let wlLoaded = false;

async function loadWatchlist(refresh = false) {
  if (wlLoaded && !refresh) return;
  document.getElementById("wl-loading").classList.remove("hidden");
  document.getElementById("wl-table").classList.add("hidden");
  document.getElementById("wl-empty").classList.add("hidden");
  try {
    const r = await fetch("/api/watchlist");
    const { items } = await r.json();
    wlLoaded = true;
    renderWatchlist(items);
  } catch (e) {
    toast("⚠ Error cargando watchlist: " + e.message);
  } finally {
    document.getElementById("wl-loading").classList.add("hidden");
  }
}

function renderWatchlist(items) {
  if (!items.length) {
    document.getElementById("wl-empty").classList.remove("hidden");
    return;
  }
  items.sort((a, b) => (b.mos ?? -999) - (a.mos ?? -999));
  const tbody = document.querySelector("#wl-table tbody");
  tbody.innerHTML = items.map(it => {
    const zone = it.inBuyZone === true
      ? `<span class="zone-chip buy">EN ZONA DE COMPRA</span>`
      : it.inBuyZone === false
        ? `<span class="zone-chip wait">Esperando precio</span>`
        : `<span class="zone-chip na">Sin datos</span>`;

    const cur = it.currency || "USD";
    const px = it.price;

    // Targets por escenario con badge de distancia al precio actual
    const tgtCell = (val, cls) => {
      if (val == null || px == null) return `<td class="num">—</td>`;
      const upside = ((val / px) - 1) * 100;
      const isAbove = upside >= 0;
      return `<td class="num" style="white-space:nowrap;">
        <span style="font-weight:700;">${fmtPrice(val, cur)}</span>
        <span style="font-size:10px; margin-left:3px; padding:1px 5px; border-radius:4px; font-weight:700;
          background:${isAbove ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)'};
          color:${isAbove ? 'var(--green)' : 'var(--red)'}">
          ${isAbove ? '+' : ''}${upside.toFixed(0)}%
        </span>
      </td>`;
    };

    const cagrBadge = it.cagrBase != null
      ? `<span style="font-size:10.5px; color:${it.cagrBase >= 8 ? 'var(--green)' : it.cagrBase >= 0 ? 'var(--gold)' : 'var(--red)'}; font-weight:700;">CAGR ${it.cagrBase > 0 ? '+' : ''}${it.cagrBase?.toFixed(1)}%/a</span>`
      : '—';

    return `<tr>
      <td class="sym" onclick="go('${it.symbol}')">${it.symbol}</td>
      <td onclick="go('${it.symbol}')">${it.name || "—"}</td>
      <td class="num">${fmtPrice(px, cur)}</td>
      <td class="num">${it.fairValue != null ? fmtPrice(it.fairValue, cur) : "—"}</td>
      <td class="num ${(it.mos ?? 0) >= 0 ? 'up' : 'down'}"><b>${fmtPct(it.mos, 0, true)}</b></td>
      ${tgtCell(it.targetCons, 'cons')}
      ${tgtCell(it.targetBase, 'base')}
      ${tgtCell(it.targetOpt, 'opt')}
      <td class="num">${cagrBadge}</td>
      <td class="num">
        <input type="number" class="wl-target" value="${it.targetMos}" min="0" max="100" step="5"
               onchange="wlSetTarget('${it.symbol}', this.value)">%
      </td>
      <td>${zone}</td>
      <td><button class="btn-x" onclick="wlRemove('${it.symbol}')" title="Dejar de seguir">✕</button></td>
    </tr>`;
  }).join("");
  document.getElementById("wl-table").classList.remove("hidden");
}

async function wlAdd(symbol, targetMos = 25) {
  await fetch("/api/watchlist", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, targetMos }),
  });
  wlLoaded = false;
  toast(`★ ${symbol} agregada a tu watchlist (objetivo: MoS ≥ ${targetMos}%)`);
}

async function wlRemove(symbol) {
  await fetch(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  wlLoaded = false;
  toast(`${symbol} eliminada de la watchlist`);
  loadWatchlist(true);
  if (state.data && state.data.symbol === symbol) setStarState(false);
}

async function wlSetTarget(symbol, value) {
  const t = parseFloat(value);
  if (!isFinite(t)) return;
  await fetch("/api/watchlist", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, targetMos: t }),
  });
  wlLoaded = false;
  toast(`Objetivo de ${symbol} actualizado a MoS ≥ ${t}%`);
  loadWatchlist(true);
}

document.getElementById("wl-refresh").addEventListener("click", () => loadWatchlist(true));

/* Exportar Watchlist a CSV */
document.getElementById("wl-csv").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/watchlist");
    const { items } = await r.json();
    if (!items || !items.length) return toast("No hay acciones en la watchlist");
    const esc = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
    const headers = ["Símbolo", "Empresa", "Precio", "Valor Justo", "MoS Actual %", "MoS Objetivo %", "En Zona de Compra"];
    const rows = items.map(it => [
      esc(it.symbol), esc(it.name), esc(it.price), esc(it.fairValue), esc(it.mos),
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
