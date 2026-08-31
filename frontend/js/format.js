/* Utilidades de formato de números (es-CL friendly, estilo financiero). */

const CUR_SYM = { USD: "US$", EUR: "€", CLP: "CLP$", GBP: "£", JPY: "¥" };

export function fmtBig(x, currency) {
  if (x == null || !isFinite(x)) return "—";
  const sym = currency ? (CUR_SYM[currency] || "") : "";
  const abs = Math.abs(x);
  let v, suf;
  if (abs >= 1e12) { v = x / 1e12; suf = " T"; }
  else if (abs >= 1e9) { v = x / 1e9; suf = " B"; }
  else if (abs >= 1e6) { v = x / 1e6; suf = " M"; }
  else if (abs >= 1e3) { v = x / 1e3; suf = " K"; }
  else { v = x; suf = ""; }
  return sym + v.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: abs >= 1e3 ? 1 : 0 }) + suf;
}

export function fmtPrice(x, currency) {
  if (x == null || !isFinite(x)) return "—";
  const sym = CUR_SYM[currency] || "";
  const d = currency === "CLP" || currency === "JPY" ? 0 : 2;  // sin decimales
  return sym + x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function fmtNum(x, d = 2) {
  if (x == null || !isFinite(x)) return "—";
  return x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function fmtPct(x, d = 1, signed = false) {
  if (x == null || !isFinite(x)) return "—";
  const s = signed && x > 0 ? "+" : "";
  return s + x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + "%";
}

export function fmtRatio(x, d = 1) {
  if (x == null || !isFinite(x)) return "—";
  return fmtNum(x, d) + "x";
}

export function pctClass(x) { return x == null ? "" : x >= 0 ? "up" : "down"; }

export function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function fmtDate(isoStr) {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return String(isoStr);
    return d.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
  } catch (e) {
    return String(isoStr);
  }
}
