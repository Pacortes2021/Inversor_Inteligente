/* Tema claro/oscuro persistido en localStorage. */

import { $ } from "./dom.js?v=77";

export function initTheme() {
  const stored = localStorage.getItem("theme") || "light";
  setTheme(stored);
}

export function setTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("theme", t);
  const btn = $("theme-toggle");
  if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = $("theme-toggle");
  if (btn) {
    btn.onclick = () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(current === "dark" ? "light" : "dark");
      document.dispatchEvent(new CustomEvent("theme-changed"));
    };
  }
  initTheme();
});
