# El Inversor Inteligente 📊

Herramienta personal de análisis de acciones con mentalidad **value investing** (Warren Buffett / Benjamin Graham). Inspirada en thesmartinvestortool.com, pero hecha a medida.

## Qué hace

**Vista Análisis** (por símbolo, ej: NVDA, KO, AAPL, COPEC.SN):
- Precio, capitalización y ratios actuales (PE, PE forward, P/S, P/B, EV/EBITDA, PEG, ROE, márgenes, deuda…)
- **Gráficos históricos de hasta 16 años** (SEC EDGAR + Yahoo): precio, PE/P S/P B históricos (TTM) con mediana y rango p25-p75, ingresos y utilidad, márgenes, FCF, ROE/ROIC, deuda vs caja, acciones en circulación (recompras), EPS y dividendos. Cada gráfico se puede descargar como PNG.
- **Valor intrínseco** con 3 modelos: DCF de FCF normalizado (sliders interactivos; los supuestos se guardan por acción), reversión al PE mediano histórico (capado a 30x) y Número de Graham. Consenso ponderado → **margen de seguridad** y veredicto.
- **Scorecard Buffett**: 12 criterios cuantitativos (ROE ≥ 15%, margen bruto ≥ 40%, deuda conservadora, FCF siempre positivo, recompras, etc.)
- Comparación earnings yield vs bono del Tesoro a 10 años.

**Vista Screener**: dos universos (EE.UU. ~220 acciones / Chile-IPSA ~30) y dos modos:
- *Rápido*: puntaje de valor (valoración 45%, calidad 30%, salud financiera 15%, contrarian 10%).
- *Profundo*: valoración completa por acción (DCF + reversión al PE de 15 años vía EDGAR + Graham) → **margen de seguridad**, corriendo en segundo plano con barra de progreso.
Con filtros por sector y texto, y exportación a CSV.

**Vista Comparar**: hasta 4 empresas lado a lado (tabla de métricas + retorno normalizado, PE histórico y margen neto superpuestos).

**Vista Watchlist**: acciones seguidas con margen de seguridad objetivo; cuando el MoS actual supera tu objetivo la acción aparece **EN ZONA DE COMPRA**. Persistente en `data/watchlist.json`.

**Vista Portafolio**: registra tus compras reales (con tesis) y compáralas contra el S&P 500 desde cada fecha — retorno, benchmark y **alfa** por posición y total.

**Extras estilo TradingView**: sidebar de favoritos con precio, variación diaria y sparkline de 30 días (sincronizado con la watchlist); **mapa de calor** del universo (tamaño = capitalización, color = margen de seguridad); escala logarítmica y **SMA 50/200** en el gráfico de precio; barra de rango de 52 semanas.

**Análisis avanzado**: **Reverse DCF** (qué crecimiento de FCF descuenta el precio actual), matriz de sensibilidad crecimiento × tasa de descuento, tabla de **CAGR a 1/3/5/10 años**, próxima fecha de resultados y links directos a los 10-K/10-Q en EDGAR, e informe imprimible con el botón ⎙ (o ⌘P).

**Alerta diaria**: `scripts/instalar_alerta.sh` programa (launchd) una revisión de la watchlist los días hábiles a las 9:30 con notificación de macOS si algo entró en zona de compra. Log en `data/alertas.log`.

**Glosario interactivo**: clic en cualquier indicador (PER, ROE, FCF yield, margen de seguridad, EPV…) abre una explicación en español simple con ejemplo — cualquiera puede leer la app sin saber finanzas.

**Confianza y madurez** (ronda 4):
- Suite de **tests** (`pytest tests/` — 24 tests de valoración, métricas, EDGAR y calidad).
- **Avisos de calidad de datos** en cada análisis: FCF deprimido/inflado vs su historia, saltos de utilidad, patrimonio negativo, historial de PE corto, discrepancias Yahoo vs SEC.
- **Historial de margen de seguridad**: cada análisis y escaneo profundo guarda una foto diaria (`data/mos_history.jsonl`) y el análisis muestra cómo evoluciona el MoS en el tiempo.
- **Notas cualitativas por acción**: checklist de moat (marca, costos, red, switching, patentes, escala) + tesis y riesgos, con autoguardado (`data/notes.json`).
- **EPV de Greenwald** como cuarto modelo (valor a cero crecimiento).
- **Seguridad del dividendo**: rachas pagando/subiendo y payout sobre FCF con semáforo.
- Descargas de Yahoo en paralelo (análisis fresco ~3s vs ~15s) y servidor accesible desde el teléfono en la red local (`./run.sh` muestra la URL).
- **Respaldo**: exportar/importar watchlist + portafolio + notas en un JSON (pestaña Portafolio).

## Cómo usarla

```bash
./run.sh
# abre http://127.0.0.1:8756
```

(La primera vez: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`)

## Arquitectura

```
backend/
  main.py       → FastAPI: /api/stock, /api/screener(/deep), /api/watchlist, /api/search
  data.py       → descarga Yahoo Finance (yfinance) + caché en disco (cache/)
  edgar.py      → historia anual larga desde SEC EDGAR (XBRL company facts)
  metrics.py    → series TTM, ratios históricos, ajuste por splits, fusión Yahoo+EDGAR
  valuation.py  → DCF, Graham, reversión PE, scorecard Buffett
  stock.py      → compone el payload completo
  screener.py   → screener rápido y profundo (hilo de fondo con progreso)
  watchlist.py  → watchlist persistente con MoS objetivo
frontend/       → HTML/CSS/JS vanilla + Apache ECharts (CDN)
data/           → watchlist.json (tus datos)
```

## Notas y límites

- **EDGAR solo cubre empresas que reportan a la SEC** (EE.UU. + ADRs); para el resto (ej: bolsa de Santiago) la historia se limita a los ~4-5 años de Yahoo.
- Los EPS históricos de EDGAR se ajustan por splits para calzar con los precios ajustados de Yahoo; los PE > 200 se filtran por no ser señal de valoración.
- Caché: fundamentales 6 h, EDGAR 7 días, screener 24 h. `?refresh=1` o el botón "Actualizar datos" fuerzan recálculo.
- El escaneo profundo la primera vez toma varios minutos (descarga los XBRL de la SEC); después queda cacheado.
- **No es asesoría financiera.** Es una herramienta educativa de apoyo a la decisión.
