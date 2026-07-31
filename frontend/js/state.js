/* Estado compartido de la aplicación (símbolo activo, datos cargados, pestañas). */

export const state = { symbol: null, data: null, activeTab: "summary" };

export let currentPeriodYears = 1;
export function setCurrentPeriodYears(v) { currentPeriodYears = v; }

export let currentMultiplesRange = "all";
export function setCurrentMultiplesRange(v) { currentMultiplesRange = v; }
