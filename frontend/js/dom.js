/* Helpers de DOM y fetch con autenticación para endpoints que mutan datos. */

import { API_KEY } from "./config.js?v=80";

export const $ = id => document.getElementById(id);

let toastTimer = null;
export function toast(msg) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}

/* fetch que inyecta la API key en métodos que modifican datos (POST/DELETE). */
export async function apiFetch(url, options = {}) {
  const { method = "GET", body, headers = {} } = options;
  const h = { ...headers };
  if (method.toUpperCase() !== "GET") h["X-API-Key"] = API_KEY;
  const opts = { method, headers: h };
  if (body != null) {
    if (typeof body === "string") {
      opts.body = body;
    } else {
      h["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  return fetch(url, opts);
}
