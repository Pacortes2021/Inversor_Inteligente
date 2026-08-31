/* Sistema de alertas de precios / margen de seguridad (localStorage). */

import { $, toast } from "./dom.js?v=79";

const ALERTS_KEY = "stock_alerts_v1";

export function getAlerts() {
  try { return JSON.parse(localStorage.getItem(ALERTS_KEY)) || []; } catch { return []; }
}
export function saveAlerts(arr) {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(arr));
}

export function deleteAlert(id) {
  const alerts = getAlerts().filter(a => a.id !== id);
  saveAlerts(alerts);
  renderAlertsList();
}

export function renderAlertsList() {
  const listEl = $("alerts-list");
  if (!listEl) return;
  const alerts = getAlerts();
  if (!alerts.length) {
    listEl.innerHTML = `<p class="muted" style="font-size:12px;">No tienes alertas activas.</p>`;
    return;
  }
  listEl.innerHTML = alerts.map(a => {
    let lbl = "";
    if (a.type === "price_below") lbl = `Precio < $${a.target}`;
    else if (a.type === "price_above") lbl = `Precio > $${a.target}`;
    else if (a.type === "mos_above") lbl = `Margen de Seg. > ${a.target}%`;

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:var(--bg); border-radius:6px; border:1px solid var(--border);">
        <span style="font-size:12.5px; font-weight:600; color:var(--text);">${a.symbol}: ${lbl}</span>
        <button class="btn-x" data-alert-id="${a.id}" title="Eliminar">✕</button>
      </div>
    `;
  }).join("");
}

document.addEventListener("click", e => {
  const btn = e.target.closest("[data-alert-id]");
  if (btn) deleteAlert(Number(btn.getAttribute("data-alert-id")));
});

export function checkStockAlerts(d) {
  if (!d) return;
  const alerts = getAlerts().filter(a => a.symbol === d.symbol);
  const px = d.quote.price;
  const mos = d.valuation.marginOfSafety;

  alerts.forEach(a => {
    let triggered = false;
    let msg = "";
    if (a.type === "price_below" && px <= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: ${d.symbol} cayó a $${px.toFixed(2)} (Objetivo: < $${a.target})`;
    } else if (a.type === "price_above" && px >= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: ${d.symbol} subió a $${px.toFixed(2)} (Objetivo: > $${a.target})`;
    } else if (a.type === "mos_above" && mos != null && mos >= a.target) {
      triggered = true;
      msg = `🔔 ALERTA: Margen de Seguridad de ${d.symbol} alcanzó ${mos.toFixed(1)}% (Objetivo: > ${a.target}%)`;
    }
    if (triggered) {
      toast(msg);
    }
  });
}
