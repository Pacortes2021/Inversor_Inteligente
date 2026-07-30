# Cambios para index.html — Refactor de UI/UX

## 1. Agregar CSS additions + Skip-nav + ARIA

En `<head>`, después de `<link rel="stylesheet" href="css/style.css?v=19.0">`:

```html
<!-- CSS Principal -->
<link rel="stylesheet" href="css/style.css?v=20.0">
<link rel="stylesheet" href="css/additions.css?v=1.0">
```

Después de `<body>`, antes del `<header>`:

```html
<a href="#view-analisis" class="skip-nav">Saltar al contenido principal</a>
```

---

## 2. HAMBURGER BUTTON en topbar

Reemplazar el `<header class="topbar">` existente. Agregar el botón hamburger antes del cierre del topbar:

```html
<header class="topbar" role="banner">
  <div class="brand" onclick="location.hash='#/analisis'">
    <span class="brand-icon" aria-hidden="true">◆</span>
    <span class="brand-name">El Inversor <em>Inteligente</em></span>
  </div>

  <nav class="tabs" role="navigation" aria-label="Navegación principal">
    <a href="#/analisis" id="tab-analisis" class="tab active">Análisis</a>
    <a href="#/screener" id="tab-screener" class="tab">Screener</a>
    <a href="#/comparar" id="tab-comparar" class="tab">Comparar</a>
    <a href="#/watchlist" id="tab-watchlist" class="tab">Watchlist</a>
    <a href="#/portafolio" id="tab-portafolio" class="tab">Portafolio</a>
  </nav>

  <div class="search-box" role="search">
    <input id="search-input" type="text" placeholder="Buscar acción… (ej: NVDA, NFLX, AAPL)" autocomplete="off" spellcheck="false" aria-label="Buscar acción">
    <div id="search-results" class="search-results hidden" role="listbox"></div>
  </div>

  <button id="theme-toggle" class="theme-toggle-btn" title="Cambiar Tema (Claro / Oscuro)" aria-label="Cambiar tema">🌙</button>

  <!-- HAMBURGER (visible solo en móvil) -->
  <button id="hamburger-btn" class="hamburger" aria-label="Abrir menú" aria-expanded="false">
    <span></span>
    <span></span>
    <span></span>
  </button>
</header>

<!-- MOBILE NAV OVERLAY -->
<div id="mobile-nav" class="mobile-nav-overlay" role="dialog" aria-label="Menú de navegación">
  <a href="#/analisis" class="mobile-nav-link" data-nav="analisis">📊 Análisis</a>
  <a href="#/screener" class="mobile-nav-link" data-nav="screener">🔍 Screener</a>
  <a href="#/comparar" class="mobile-nav-link" data-nav="comparar">⇄ Comparar</a>
  <a href="#/watchlist" class="mobile-nav-link" data-nav="watchlist">☆ Watchlist</a>
  <a href="#/portafolio" class="mobile-nav-link" data-nav="portafolio">💼 Portafolio</a>
  <input id="mobile-search-input" class="mobile-nav-search" type="text" placeholder="Buscar acción…" autocomplete="off" spellcheck="false" aria-label="Buscar acción">
  <button id="mobile-nav-close" class="mobile-nav-close">Cerrar</button>
</div>
```

---

## 3. Reemplazar INLINE STYLES en action-tabs

**ANTES:**
```html
<nav class="action-tabs" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:8px;">
  <button class="a-tab active" data-pane="summary" style="font-size:13px; font-weight:700; text-align:center; padding:10px 14px;">📊 Resumen Ejecutivo</button>
  <button class="a-tab" data-pane="valuation" style="font-size:13px; font-weight:700; text-align:center; padding:10px 14px;">💎 Centro de Valoración & Proyecciones</button>
  <button class="a-tab" data-pane="financials-hub" style="font-size:13px; font-weight:700; text-align:center; padding:10px 14px;">📈 Financieros & Métricas</button>
  <button class="a-tab" data-pane="ownership" style="font-size:13px; font-weight:700; text-align:center; padding:10px 14px;">👔 Propietarios & Datos Corporativos</button>
</nav>
```

**DESPUÉS:**
```html
<nav class="action-tabs" aria-label="Sub-navegación del análisis">
  <button class="a-tab active" data-pane="summary" aria-selected="true">📊 Resumen Ejecutivo</button>
  <button class="a-tab" data-pane="valuation" aria-selected="false">💎 Centro de Valoración & Proyecciones</button>
  <button class="a-tab" data-pane="financials-hub" aria-selected="false">📈 Financieros & Métricas</button>
  <button class="a-tab" data-pane="ownership" aria-selected="false">👔 Propietarios & Datos Corporativos</button>
</nav>
```

---

## 4. Reemplazar INLINE STYLES en warnings

**ANTES:**
```html
<summary id="warnings-summary" style="cursor:pointer; list-style:none; display:flex; align-items:center; gap:6px; font-weight:700;"></summary>
<ul id="warnings-list" style="margin:6px 0 0 0; padding-left:18px;"></ul>
```

**DESPUÉS:**
```html
<summary id="warnings-summary" class="warnings-details"></summary>
<ul id="warnings-list" class="warnings-list"></ul>
```

---

## 5. Reemplazar INLINE STYLES en DCF price bar

**ANTES:**
```html
<div id="dcf-price-bar-wrap" style="margin-top:10px; display:none;">
  <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--muted); margin-bottom:3px;">
    <span>Precio</span><span id="dcf-bar-pct">—</span><span>DCF FV</span>
  </div>
  <div style="background:var(--border); border-radius:4px; height:6px; position:relative; overflow:hidden;">
    <div id="dcf-price-bar" style="height:100%; background:var(--primary); border-radius:4px; transition:width 0.6s ease;"></div>
  </div>
</div>
```

**DESPUÉS:**
```html
<div id="dcf-price-bar-wrap" class="dcf-bar-wrap" style="display:none;">
  <div class="dcf-bar-labels">
    <span>Precio</span><span id="dcf-bar-pct">—</span><span>DCF FV</span>
  </div>
  <div class="dcf-bar-track">
    <div id="dcf-price-bar" class="dcf-bar-fill"></div>
  </div>
</div>
```

---

## 6. Reemplazar INLINE STYLES en summary cards

**ANTES (cada card del summary):**
```html
<span class="label" style="cursor:help; border-bottom:1px dashed var(--border);">FCF Yield <span style="font-size:10px; opacity:0.6;">ⓘ</span></span>
```

**DESPUÉS:**
```html
<span class="label" style="cursor:help; border-bottom:1px dashed var(--border);">FCF Yield <span class="info-icon">ⓘ</span></span>
```

---

## 7. Reemplazar INLINE STYLES en section headings

Para todas las secciones que usan `style="font-family:'Outfit',sans-serif; font-size:18px; font-weight:700; color:var(--text); margin-bottom:8px;"`:

**ANTES:**
```html
<h2 style="font-family:'Outfit',sans-serif; font-size:18px; font-weight:700; color:var(--text); margin-bottom:8px;">🏆 Evaluador de Calidad</h2>
<p class="card-sub" style="font-size:12.5px; color:var(--muted); margin-bottom:20px;">
```

**DESPUÉS:**
```html
<h2 class="section-heading">🏆 Evaluador de Calidad</h2>
<p class="card-sub section-sub">
```

Para headings con `font-size:20px`:

**ANTES:**
```html
<h2 style="font-family:'Outfit',sans-serif; font-size:20px; font-weight:800; color:var(--text); margin-bottom:6px;">
```

**DESPUÉS:**
```html
<h2 class="section-heading-lg">
```

---

## 8. Reemplazar INLINE STYLES en grids

**ANTES:**
```html
<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px; align-items:start;">
```

**DESPUÉS:**
```html
<div class="earnings-grid">
```

**ANTES:**
```html
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;" class="ratios-checks-grid">
```

**DESPUÉS:**
```html
<div class="ratios-checks-grid grid-2col">
```

---

## 9. Reemplazar INLINE STYLES en scenario cards

**ANTES:**
```html
<span class="badge" id="est-pe-cons-label" style="background:#4b5563; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700;">Conservador</span>
<div id="est-pe-cons-price" style="font-size:22px; font-weight:800; color:var(--text); margin-top:10px;">—</div>
<div id="est-pe-cons-ret" style="font-size:13px; font-weight:700; color:var(--muted); margin-top:4px;">—</div>
```

**DESPUÉS:**
```html
<span class="badge badge-cons" id="est-pe-cons-label">Conservador</span>
<div class="scenario-price-lg" id="est-pe-cons-price">—</div>
<div class="scenario-ret" id="est-pe-cons-ret">—</div>
```

---

## 10. Reemplazar INLINE STYLES en analyst panels

**ANTES:**
```html
<div style="padding:16px; background:var(--panel); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow);">
  <h4 style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:12px;">Desglose de Recomendaciones</h4>
```

**DESPUÉS:**
```html
<div class="analyst-panel">
  <h4>Desglose de Recomendaciones</h4>
```

---

## 11. Reemplazar INLINE STYLES en DCF sliders

**ANTES:**
```html
<label style="font-size:13px; color:var(--text); font-weight:500; display:flex; justify-content:space-between;">Crecimiento FCF <b id="lbl-growth">—</b></label>
```

**DESPUÉS:**
```html
<label class="dcf-slider-label">Crecimiento FCF <b id="lbl-growth">—</b></label>
```

---

## 12. Reemplazar INLINE STYLES en custom scenario box

**ANTES:**
```html
<div style="padding:16px; background:var(--panel); border:1px solid var(--border); border-radius:var(--radius);">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
    <label style="font-size:13.5px; font-weight:700; color:var(--text);">Ajustar Múltiplo PER Objetivo:</label>
    <span id="est-pe-val" style="font-size:16px; font-weight:800; color:var(--primary);">20.0x</span>
  </div>
  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid var(--border);">
    <div>
      <span style="font-size:12px; color:var(--muted);">Precio Proyectado 2030E</span>
      <div id="est-pe-custom-price" style="font-size:20px; font-weight:800; color:var(--text);">—</div>
    </div>
    <div style="text-align:center;">
      <span style="font-size:12px; color:var(--muted);">Retorno Total</span>
      <div id="est-pe-custom-tot" style="font-size:18px; font-weight:800;">—</div>
    </div>
    <div style="text-align:right;">
      <span style="font-size:12px; color:var(--muted);">Ganancia Anualizada (CAGR)</span>
      <div id="est-pe-custom-cagr" style="font-size:18px; font-weight:800;">—</div>
    </div>
  </div>
</div>
```

**DESPUÉS:**
```html
<div class="custom-scenario-box">
  <div class="flex-between" style="margin-bottom:10px;">
    <label class="custom-scenario-label">Ajustar Múltiplo PER Objetivo:</label>
    <span id="est-pe-val" class="custom-scenario-val">20.0x</span>
  </div>
  <input type="range" id="est-pe-slider" min="5" max="60" step="0.5" value="20" style="width:100%; cursor:pointer; accent-color:var(--primary);">
  <div class="flex-justify-between-mt">
    <div>
      <span class="custom-scenario-metric">Precio Proyectado 2030E</span>
      <div id="est-pe-custom-price" class="custom-scenario-price">—</div>
    </div>
    <div style="text-align:center;">
      <span class="custom-scenario-metric">Retorno Total</span>
      <div id="est-pe-custom-tot" class="custom-scenario-metric-val">—</div>
    </div>
    <div style="text-align:right;">
      <span class="custom-scenario-metric">Ganancia Anualizada (CAGR)</span>
      <div id="est-pe-custom-cagr" class="custom-scenario-metric-val">—</div>
    </div>
  </div>
</div>
```

---

## 13. Reemplazar INLINE STYLES en earnings section

**ANTES:**
```html
<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
```

**DESPUÉS:**
```html
<div class="flex-between-baseline" style="margin-bottom:14px;">
```

---

## 14. Reemplazar INLINE STYLES en multiples header

**ANTES:**
```html
<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:12px; margin-bottom:16px;">
```

**DESPUÉS:**
```html
<div class="multiples-header">
```

---

## 15. Reemplazar INLINE STYLES en financial statement header

**ANTES:**
```html
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
  <div>
    <h2 style="font-family:'Outfit',sans-serif; font-size:18px; font-weight:700; color:var(--text); margin:0;">Estados Financieros Desglosados</h2>
    <p class="card-sub" style="font-size:12.5px; color:var(--muted); margin-top:2px;">Revisa las cifras clave reportadas en los últimos períodos.</p>
  </div>
  <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
```

**DESPUÉS:**
```html
<div class="fin-stmt-header">
  <div>
    <h2 class="section-heading">Estados Financieros Desglosados</h2>
    <p class="card-sub fin-stmt-sub">Revisa las cifras clave reportadas en los últimos períodos.</p>
  </div>
  <div class="fin-stmt-controls">
```

---

## 16. Reemplazar INLINE STYLES en growth table header

**ANTES:**
```html
<section class="card growth-card" style="margin-bottom:20px;">
```

**DESPUÉS:**
```html
<section class="card">
```

---

## 17. Reemplazar INLINE STYLES en history table header

**ANTES:**
```html
<div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:4px;">
  <div>
    <h2 style="margin:0;">📜 Histórico de Ratios Financieros (SEC EDGAR)</h2>
    <p class="card-sub" style="margin-top:4px;">Evolución año a año de la rentabilidad, estructura de capital y múltiplos.</p>
  </div>
```

**DESPUÉS:**
```html
<div class="hist-header">
  <div>
    <h2 class="section-heading-lg" style="margin:0;">📜 Histórico de Ratios Financieros (SEC EDGAR)</h2>
    <p class="card-sub hist-sub">Evolución año a año de la rentabilidad, estructura de capital y múltiplos.</p>
  </div>
```

---

## 18. Reemplazar INLINE STYLES en income chart header

**ANTES:**
```html
<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
  <div>
    <h2 style="font-family:'Outfit',sans-serif; font-size:20px; font-weight:800; color:var(--text); margin:0;">
      📊 Gráficos de Múltiplos Históricos (15 Años)
    </h2>
```

**DESPUÉS:**
```html
<div class="multiples-header">
  <div>
    <h2 class="section-heading-lg">
      📊 Gráficos de Múltiplos Históricos (15 Aías)
    </h2>
```

---

## 19. Reemplazar INLINE STYLES en multiples chart grid

**ANTES:**
```html
<div class="charts-grid" style="display:grid; grid-template-columns: repeat(3, 1fr); gap:20px;">
  <div class="chart-card wide" style="grid-column: span 3; padding-top:10px;">
    <h3 style="font-size:13px; font-weight:700; color:var(--text); margin-bottom:8px;">PE histórico</h3>
    <div class="chart" id="ch-pe" style="height:320px; width:100%;"></div>
  </div>
  <div class="chart-card" style="grid-column: span 1.5; padding-top:10px;">
    <h3 style="font-size:13px; font-weight:700; color:var(--text); margin-bottom:8px;">P/Ventas histórico</h3>
    <div class="chart" id="ch-ps" style="height:250px; width:100%;"></div>
  </div>
  <div class="chart-card" style="grid-column: span 1.5; padding-top:10px;">
    <h3 style="font-size:13px; font-weight:700; color:var(--text); margin-bottom:8px;">P/Valor libro histórico</h3>
    <div class="chart" id="ch-pb" style="height:250px; width:100%;"></div>
  </div>
</div>
```

**DESPUÉS:**
```html
<div class="grid-multiples">
  <div class="chart-card chart-wide">
    <h3>PE histórico (TTM) con mediana y banda p25-p75</h3>
    <div class="chart" id="ch-pe" style="height:320px; width:100%;"></div>
  </div>
  <div class="chart-card chart-half">
    <h3>P/Ventas histórico</h3>
    <div class="chart" id="ch-ps" style="height:250px; width:100%;"></div>
  </div>
  <div class="chart-card chart-half">
    <h3>P/Valor libro histórico</h3>
    <div class="chart" id="ch-pb" style="height:250px; width:100%;"></div>
  </div>
</div>
```

---

## 20. Reemplazar INLINE STYLES en earnings surprises

**ANTES:**
```html
<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
  <h2 style="font-family:'Outfit',sans-serif; font-size:20px; font-weight:800; color:var(--text); margin:0;">
    📅 Reportes de Ganancias (Earnings) y Sorpresas EPS
  </h2>
</div>
<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px; align-items:start;">
  <!-- Tarjeta Próximo Reporte -->
  <div class="scenario-card" style="padding:24px; text-align:left; height:100%;">
    <div style="font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:12px;">Próximo Reporte Esperado</div>
```

**DESPUÉS:**
```html
<div class="flex-between-baseline" style="margin-bottom:14px;">
  <h2 class="section-heading-lg">
    📅 Reportes de Ganancias (Earnings) y Sorpresas EPS
  </h2>
</div>
<div class="earnings-grid">
  <div class="scenario-card scenario-card-lg">
    <div style="font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; margin-bottom:12px;">Próximo Reporte Esperado</div>
```

---

## 21. Reemplazar INLINE STYLES en ownership section

**ANTES:**
```html
<section class="card" style="margin-bottom:20px;">
  <h2 style="font-family:'Outfit',sans-serif; font-size:18px; font-weight:700; color:var(--text); margin-bottom:6px;">👔 Estructura de Propiedad Accionaria</h2>
```

**DESPUÉS:**
```html
<section class="card">
  <h2 class="section-heading">👔 Estructura de Propiedad Accionaria</h2>
```

---

## 22. Reemplazar INLINE STYLES en grid-2col sections

Busca todos los `style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;"` y reemplaza con `class="grid-2col"`.

Busca todos los `style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:20px;"` y reemplaza con `class="grid-auto-fit-sm"`.

---

## 23. Reemplazar INLINE STYLES en divs con margin-bottom

Busca todos los `<section class="card" style="margin-bottom:20px;">` y reemplaza con `<section class="card">` (el margin-bottom ya viene del CSS de `.card`).

---

## 24. AGREGAR ARIA a tab panes

Para cada `<div id="pane-*">`:

```html
<div id="pane-summary" class="tab-pane active" role="tabpanel" aria-labelledby="tab-summary">
<div id="pane-valuation" class="tab-pane hidden" role="tabpanel" aria-labelledby="tab-valuation">
<div id="pane-financials-hub" class="tab-pane hidden" role="tabpanel" aria-labelledby="tab-financials">
<div id="pane-ownership" class="tab-pane hidden" role="tabpanel" aria-labelledby="tab-ownership">
```

Y a los botones de action-tabs:
```html
<button class="a-tab active" data-pane="summary" role="tab" aria-selected="true" aria-controls="pane-summary">
<button class="a-tab" data-pane="valuation" role="tab" aria-selected="false" aria-controls="pane-valuation">
<button class="a-tab" data-pane="financials-hub" role="tab" aria-selected="false" aria-controls="pane-financials-hub">
<button class="a-tab" data-pane="ownership" role="tab" aria-selected="false" aria-controls="pane-ownership">
```

---

## 25. Fix: pane-financials-hub-main huérfano

`pane-financials-hub-main` no tiene botón asociado. Opciones:

**Opción A** (recomendada): Fusionar su contenido dentro de `pane-financials-hub`:
- Mover el contenido de `pane-financials-hub-main` al final de `pane-financials-hub`
- Eliminar `pane-financials-hub-main`

**Opción B**: Agregar un botón 5to en action-tabs:
```html
<button class="a-tab" data-pane="financials-hub-main" role="tab">📊 Estados Financieros</button>
```
Y renombrar `financials-hub` a algo más específico como `ratios`.

---

## Resumen de INLINE STYLES restantes (dificiles de eliminar)

Estos inline styles son dinámicos o únicos, se pueden dejar o mover a clases CSS genéricas:

- `style="display:none;"` → se controla por JS, dejar o usar `.hidden`
- `style="width:100%; cursor:pointer; accent-color:var(--primary);"` (sliders) → agregar clase `.slider-input`
- `style="height:220px; width:100%;"` (charts) → usar `.chart` existente
- `style="height:320px; width:100%;"` (PE chart) → agregar clase `.chart-lg`
- `style="height:250px; width:100%;"` (PS/PB charts) → agregar clase `.chart-md`
- `style="height:240px; width:100%; min-width:300px;"` (earnings chart) → clase `.earnings-chart-container`
