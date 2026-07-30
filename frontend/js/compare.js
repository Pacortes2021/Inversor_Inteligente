/* Comparador de empresas: hasta 4 lado a lado con gráficos superpuestos. */

const cmp = { symbols: [], payloads: {} };
const CMP_COLORS = ["#d4af37", "#3b82f6", "#22c55e", "#8b5cf6"];

async function cmpAdd(inputStr) {
  if (!inputStr) return;
  const syms = inputStr.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
  for (const symbol of syms) {
    if (cmp.symbols.includes(symbol)) continue;
    if (cmp.symbols.length >= 4) {
      toast("Máximo 4 empresas — quita una primero");
      break;
    }

    document.getElementById("cmp-loading").classList.remove("hidden");
    try {
      const r = await fetch(`/api/stock/${encodeURIComponent(symbol)}`);
      if (!r.ok) throw new Error(`No se encontró '${symbol}'`);
      cmp.payloads[symbol] = await r.json();
      cmp.symbols.push(symbol);
    } catch (e) {
      toast("⚠ " + e.message);
    } finally {
      document.getElementById("cmp-loading").classList.add("hidden");
    }
  }
  renderCompare();
}

function cmpRemove(symbol) {
  cmp.symbols = cmp.symbols.filter(s => s !== symbol);
  delete cmp.payloads[symbol];
  renderCompare();
}

const CMP_ROWS = [
  ["Precio", d => fmtPrice(d.quote.price, d.profile.currency)],
  ["Capitalización", d => fmtBig(d.quote.marketCap, d.profile.currency)],
  ["Sector", d => d.profile.sector || "—"],
  ["PE (TTM)", d => fmtRatio(d.current.pe)],
  ["PE forward", d => fmtRatio(d.current.forwardPe)],
  ["PE mediana hist.", d => d.history.peStats ? fmtRatio(d.history.peStats.median) : "—"],
  ["PE vs mediana", d => spanPct(d.history.peStats ? d.history.peStats.vsMedian : null, false)],
  ["P/Ventas", d => fmtRatio(d.current.ps)],
  ["P/Libro", d => fmtRatio(d.current.pb, 2)],
  ["EV/EBITDA", d => fmtRatio(d.current.evEbitda)],
  ["Margen bruto", d => d.current.grossMargin != null ? fmtPct(d.current.grossMargin * 100) : "—"],
  ["Margen neto", d => d.current.netMargin != null ? fmtPct(d.current.netMargin * 100) : "—"],
  ["ROE (TTM)", d => d.current.roe != null ? fmtPct(d.current.roe * 100) : "—"],
  ["ROIC (5Y Avg.)", d => d.ratios && d.ratios.roic10yAvg != null ? fmtPct(d.ratios.roic10yAvg, 1) : "—"],
  ["ROC (Greenblatt)", d => d.ratios && d.ratios.roc && d.ratios.roc.val != null ? fmtPct(d.ratios.roc.val, 1) : "—"],
  ["Deuda/Patrimonio", d => d.current.debtToEquity != null ? fmtRatio(d.current.debtToEquity / 100, 2) : "—"],
  ["FCF yield", d => fmtPct(d.current.fcfYield, 2)],
  ["Div. yield", d => fmtPct(d.current.divYield, 2)],
  ["Crec. ingresos (yoy)", d => spanPct(d.current.revenueGrowth != null ? d.current.revenueGrowth * 100 : null)],
  ["CAGR Ingresos (5Y)", d => { const g = d.growthTable ? d.growthTable.find(x => x.metric === "Ingresos") : null; return g && g.cagr5 != null ? fmtPct(g.cagr5, 1) : "—"; }],
  ["CAGR FCF (5Y)", d => { const g = d.growthTable ? d.growthTable.find(x => x.metric === "Flujo de caja libre") : null; return g && g.cagr5 != null ? fmtPct(g.cagr5, 1) : "—"; }],
  ["Altman Z-Score", d => d.current.altmanZ != null ? `${d.current.altmanZ.toFixed(2)} (${d.current.altmanZ >= 3 ? 'Seguro' : d.current.altmanZ >= 1.8 ? 'Atención' : 'Riesgo'})` : "—"],
  ["Piotroski F-Score", d => d.current.fScore != null ? `${d.current.fScore} / 9` : "—"],
  ["Scorecard Buffett", d => `${d.scorecard.passed}/${d.scorecard.evaluated}`],
  ["Valor intrínseco", d => d.valuation.consensus != null ? fmtPrice(d.valuation.consensus, d.profile.currency) : "—"],
  ["Margen de seguridad", d => spanPct(d.valuation.marginOfSafety, true)],
];

function spanPct(v, signed = false) {
  if (v == null) return "—";
  return `<span class="${pctClass(signed ? v : -v) || ""}">${fmtPct(v, 1, true)}</span>`;
}

function renderCompare() {
  const chips = document.getElementById('cmp-chips');
  chips.innerHTML = cmp.symbols.map((s, i) =>
    `<span class="cmp-chip" style="border-color:${CMP_COLORS[i]}66;color:${CMP_COLORS[i]}">
       ${escHtml(s)} <b onclick="cmpRemove('${escHtml(s)}')" title="Quitar">✕</b></span>`).join('');

  const content = document.getElementById('cmp-content');
  const chartsWrap = document.getElementById('cmp-charts');
  if (!cmp.symbols.length) {
    content.classList.add('hidden');
    chartsWrap.style.display = 'none';
    return;
  }

  const ds = cmp.symbols.map(s => cmp.payloads[s]);

  /* ---- filas de la tabla de comparación ---- */
  const head = `<thead><tr><th></th>${cmp.symbols.map((s, i) =>
    `<th class="num" style="color:${CMP_COLORS[i]}">${escHtml(s)}</th>`).join('')}</tr></thead>`;

  /* Métricas numéricas donde "mejor" = mayor (retornos, márgenes, crecimiento) */
  const HIGHER_IS_BETTER = new Set(['Margen bruto','Margen neto','ROE (TTM)','ROIC (5Y Avg.)','ROC (Greenblatt)','FCF yield','Div. yield','CAGR Ingresos (5Y)','CAGR FCF (5Y)','Scorecard Buffett','Margen de seguridad']);
  /* "mejor" = menor (múltiplos, deuda) */
  const LOWER_IS_BETTER  = new Set(['PE (TTM)','PE forward','PE mediana hist.','PE vs mediana','P/Ventas','P/Libro','EV/EBITDA','Deuda/Patrimonio']);

  const body = CMP_ROWS.map(([label, fn]) => {
    const rawVals = ds.map(d => { try { return fn(d); } catch { return '—'; } });

    /* Intentar extraer valores numéricos para comparación */
    const nums = rawVals.map(v => {
      if (typeof v === 'number') return v;
      if (typeof v === 'string') {
        const cleaned = v.replace(/<[^>]+>/g, '').replace(/[%x$,\s]/g,'');
        const n = parseFloat(cleaned);
        return isNaN(n) ? null : n;
      }
      return null;
    });

    let bestIdx = -1, worstIdx = -1;
    const validNums = nums.filter(n => n != null);
    if (validNums.length > 1 && (HIGHER_IS_BETTER.has(label) || LOWER_IS_BETTER.has(label))) {
      const best  = HIGHER_IS_BETTER.has(label) ? Math.max(...validNums) : Math.min(...validNums);
      const worst = HIGHER_IS_BETTER.has(label) ? Math.min(...validNums) : Math.max(...validNums);
      bestIdx  = nums.indexOf(best);
      worstIdx = nums.indexOf(worst);
      if (bestIdx === worstIdx) worstIdx = -1; /* empate: no marcar */
    }

    const cells = rawVals.map((v, i) => {
      const highlight = i === bestIdx  ? 'background:rgba(16,185,129,0.12); border-radius:4px;' :
                        i === worstIdx ? 'background:rgba(239,68,68,0.10); border-radius:4px;' : '';
      return `<td class="num" style="${highlight}">${v}</td>`;
    }).join('');

    return `<tr><td class="cmp-label">${label}</td>${cells}</tr>`;
  }).join('');

  document.getElementById('cmp-table').innerHTML = head + `<tbody>${body}</tbody>`;
  content.classList.remove('hidden');

  chartsWrap.style.display = '';
  renderCompareCharts(cmp.symbols, cmp.payloads, CMP_COLORS);
  requestAnimationFrame(() => ['cmp-price', 'cmp-pe', 'cmp-margins'].forEach(id => charts[id] && charts[id].resize()));
}


document.getElementById("cmp-add").addEventListener("click", () => {
  cmpAdd(document.getElementById("cmp-input").value);
  document.getElementById("cmp-input").value = "";
});
document.getElementById("cmp-input").addEventListener("keydown", e => {
  if (e.key === "Enter") { cmpAdd(e.target.value); e.target.value = ""; }
});
