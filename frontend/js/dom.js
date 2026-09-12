/* Helpers de DOM y fetch con autenticación para endpoints que mutan datos. */

import { API_KEY } from "./config.js?v=90";

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
  const mutating = method.toUpperCase() !== "GET";
  const localHost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
  let apiKey = sessionStorage.getItem("inversor_api_key") || API_KEY || "";
  if (mutating && !localHost && !apiKey) {
    apiKey = window.prompt("Ingresa la clave local configurada en INVERSOR_API_KEY:") || "";
    if (apiKey) sessionStorage.setItem("inversor_api_key", apiKey);
  }
  if (mutating && apiKey) h["X-API-Key"] = apiKey;
  const opts = { method, headers: h };
  if (body != null) {
    if (typeof body === "string") {
      opts.body = body;
    } else {
      h["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  let response = await fetch(url, opts);
  if (mutating && !localHost && response.status === 401) {
    sessionStorage.removeItem("inversor_api_key");
    const retryKey = window.prompt("La clave no es válida. Ingresa nuevamente INVERSOR_API_KEY:") || "";
    if (retryKey) {
      sessionStorage.setItem("inversor_api_key", retryKey);
      h["X-API-Key"] = retryKey;
      response = await fetch(url, opts);
    }
  }
  return response;
}
