# Auditoría de la versión actual

Base: commit `5d36ea3` en `cache/worktrees/data-confiable`. Referencias de líneas corresponden a ese commit. La carpeta principal está en otra revisión y contiene cambios locales; no debe usarse accidentalmente como punto de partida del rework.

## Evidencia y límites

La suite actual se ejecutó de nuevo: **84 pruebas aprobadas**. La inspección cubrió backend, proveedores, persistencia, tests, contratos implícitos y recorridos del frontend. No se hizo una conciliación completa de cifras actuales de todos los emisores. Los hallazgos de fórmulas y estados se apoyan en código y reproducciones sintéticas; las pruebas históricas existentes no convierten en correctos los cálculos que no comprueban.

P0 significa que debe resolverse antes de confiar en el motor nuevo. P1 significa que afecta comparabilidad, evidencia o funcionamiento del flujo. P2 significa deuda de diseño o robustez que debe incorporarse en la migración.

## Hallazgos materiales

| ID | Nivel | Evidencia en repositorio | Hallazgo y consecuencia | Destino |
|---|---|---|---|---|
| F01 | P0 | `backend/valuation.py:12`, `:32`, `:52`, `:574` | Los flujos forward reemplazan la tasa `growth`. El reverse DCF y escenarios intentan variar un parámetro que deja de afectar los flujos. Los límites pueden mostrarse como soluciones. | Motor reverse con diagnóstico de identificabilidad |
| F02 | P0 | `backend/valuation.py:429`, `:466`, `:46`; `backend/metrics.py:327` | CFO menos capex se trata como flujo empresarial, se descuenta a WACC y se añade caja neta. CFO−capex no es automáticamente FCFF ni FCFE completo. | FCFF explícito, puente EV/patrimonio |
| F03 | P0 | `backend/valuation.py:251`, `:274`, `:334`, `:488` | DDM recibe WACC; faltantes de ROE/payout se sustituyen por cifras y crecimiento se fuerza positivo. | DDM/resultado residual a costo de patrimonio |
| F04 | P0 | `backend/providers/factory.py:15`; `backend/data.py:176`; `backend/stock.py:816`; `frontend/js/analysis.js:31` | La presencia de historia SEC cambia una etiqueta sin probar cada cifra; `isFallback` se pierde y la UI afirma datos «100% auditados». | Procedencia por observación y controles efectivamente ejecutados |
| F05 | P0 | `frontend/js/screener.js:212`; `backend/screener.py:460`; `frontend/js/valuation.js:737` | El navegador sobreescribe objetivos del backend con EPS +10% anual y PER de respaldo. Otra calculadora cambia deterioro a crecimiento positivo y presenta defaults como referencias históricas. | Eliminar motores financieros del frontend |
| F06 | P1 | `backend/stock.py:571`, `:743`; `backend/screener.py:435` | Ficha mezcla Yahoo/SEC/FMP; screener profundo usa annuals SEC y omite FMP. Chile sin SEC puede carecer de datos en screener aunque la ficha tenga estados. | `AssessmentService` único y snapshots |
| F07 | P1 | `backend/valuation.py:553`; `frontend/js/valuation.js:145`, `:1141`, `:1172` | «Margen de seguridad» utiliza dos denominadores distintos. Precio aceptable también cambia de definición. | `discountToValue` y `upsideToValue` separados |
| F08 | P1 | `backend/metrics.py:57`, `:98`, `:146` | Ventanas TTM cuentan cuatro registros sin demostrar trimestres independientes consecutivos. Pueden mezclar acumulados o huecos. | Períodos completos y reglas FY/YTD/FQ |
| F09 | P1 | `backend/edgar.py:75`, `:118`; `backend/metrics.py:250`; `backend/stock.py:481` | Se descartan publicación, accession/contexto/revisión; ratios históricos pueden usar antes de publicación cifras corregidas después. Ajustes por split pueden duplicarse. | Historia por disponibilidad y base accionaria |
| F10 | P1 | `backend/stock.py:24`; `backend/edgar.py:55`, `:200` | Se elige por año completo y no por concepto: se pierden campos SEC si Yahoo ya cubre ingresos. Acciones medias diluidas y al cierre comparten `sharesOut`. | Conciliación por métrica y definiciones distintas |
| F11 | P1 | `backend/currency.py:170`, `:189`; `backend/valuation.py:334`, `:653` | FX actual se aplica a toda la historia; CLP utiliza parámetros de tasa USD. Comparación ETF no aclara moneda comparable. | Moneda original, política FX por propósito y tasas coherentes |
| F12 | P1 | `backend/valuation.py:360`; `backend/investment.py:120` | Crecimiento negativo se limita a +2%; SBC aparece restado en auditoría sin cambiar DCF. «Normalización» combina bases de distintos períodos. | Ajustes conectados a flujos e hipótesis explícitas |
| F13 | P1 | `backend/investment.py:220`, `:255`, `:384` | Un año positivo puntúa estabilidad plena; deuda ausente con caja conocida puede dar solidez máxima. La sección riesgo vuelve a usar FCF industrial en financieras. | Evidencia mínima por criterio y plantillas sectoriales |
| F14 | P1 | `frontend/js/analysis.js:364`; `backend/screener.py:482` | Ratings y encaje modifican nota sólo en navegador, sin una revisión común; rating no exige evidencia específica. | Evaluación backend con revisión de tesis/portfolio |
| F15 | P1 | `frontend/js/valuation.js:62`, `:97`; `frontend/js/analysis.js:73` | Sliders cambian algunos resultados y dejan matriz, reverse o benchmark ligados a parámetros previos. | Recalcular respuesta coherente completa |
| F16 | P1 | `backend/portfolio.py:62`, `:225`, `:266` | Fallo de eventos puede convertirse en lista vacía. Totales/encaje pueden usar subconjunto sin reconocer toda la incompletitud. | Ledger, estado de cobertura y comparación condicionada |
| F17 | P1 | `backend/stock.py:756`; `backend/screener.py:507`; `backend/snapshots.py:16` | Lecturas por caminos distintos escriben snapshots diarios sin versión de insumos/método. El último gana. | Runs inmutables; lecturas sin efectos de escritura |
| F18 | P1 | `backend/data.py:116`; `backend/fmp.py:50`; `backend/data.py:293` | Cachés con políticas distintas, errores guardados como ausencia y tasa fija de bono como respaldo silencioso. Cambia semántica de precio ajustado en fallback. | Caché por recurso y errores tipados |
| F19 | P1 | `backend/screener.py:394`, `:513`; `backend/providers/yfinance_provider.py:60` | Escaneos sólo en memoria, sin reanudar; recursos opcionales retrasan consultas; descargas duplicadas SEC. | Trabajos persistentes, deduplicación y plazos |
| F20 | P1 | `backend/data.py:52`; `backend/main.py:458` | Rollback Python multiarquivo no equivale a transacción durable; restore y guardados no comparten control transaccional. | SQLite y backup ensayado |
| F21 | P1 | `frontend/js/analysis.js:579`, `:622`; `frontend/js/valuation.js:1230` | Debounce usa símbolo mutable; exportación puede capturar datos del primer símbolo. Riesgo de guardar/exportar otra empresa. | Estado por instrumento/revisión y concurrencia optimista |
| F22 | P2 | `backend/ratios.py:153`; `frontend/js/charts.js:2044` | Quick ratio estimado como 0,75×current ratio, deuda ausente como cero, calidad no evaluada como moderada. | Faltantes explícitos; retirar pseudoobservaciones |
| F23 | P2 | `backend/stock.py:434`; `backend/data.py:171`; `backend/providers/factory.py:7` | Ciclos `stock→main→stock` y `edgar→data→factory→edgar`; varios módulos reúnen transporte y cálculo. | Límites de dependencias comprobados |
| F24 | P2 | `frontend/js/alerts.js:5`; `frontend/js/valuation.js:46`; `backend/main.py:356` | Alertas/supuestos localStorage fuera del backup; alertas no son monitoreo continuo. | Persistencia de escenarios y seguimiento con estado |
| F25 | P2 | `requirements.txt:1`; `backend/main.py:102`; `frontend/js/loader.js:19` | Sin lock completo ni respuestas API tipadas; carga sin presupuesto/cancelación consistente; fallos del proveedor pueden presentarse como símbolo inexistente. | Entorno fijado, contratos, error/reintento explícitos |

## Reproducciones deterministas

| Caso sintético | Resultado de la versión auditada | Resultado exigido |
|---|---|---|
| FCF 1.000, 100 acciones, forward [1.100, 1.210]; variar growth de −20% a +60% | Mismo FV: aproximadamente 206,26312384; reverse al FV conocido devuelve −20% | Cambiar parámetro conectado o declarar `unidentifiable`; no solución inventada |
| Datos financieros cayendo 20% por año | `estimate_growth` entrega +2% | Conservar contracción o pedir escenario explícito |
| Cuatro flujos Q1,Q2,Q4,Q1 del año siguiente | Se produce TTM a pesar del trimestre ausente | `missing_period` y sin TTM |
| Un único año con margen operativo positivo | 6/6 en estabilidad | No se demuestra estabilidad con una observación |
| Caja conocida y deuda faltante | Puede dar 5/5 en deuda pagable | Deuda faltante; criterio sin evaluar |
| Valor 100 y precio 80 | 25% o 20% bajo etiqueta de margen | Upside 25%; descuento al valor 20% |

Las pruebas anteriores se incorporarán como regresiones en M0/M4, no como comportamiento a preservar. Para fórmulas se usarán referencias independientes y casos algebraicos.

## Qué conservar, reemplazar y retirar

| Componente | Decisión | Condición |
|---|---|---|
| Python, FastAPI, utilidades numéricas | Conservar | Mover dominio a módulos sin IO; fijar entorno |
| Pruebas de monedas, orden de columnas, validación, XSS, persistencia | Conservar y ampliar | Revisar expectativas que sólo reflejen la implementación |
| Monedas de presentación USD/CLP | Conservar | Corregir semántica de conversiones históricas y DCF |
| Datos personales/watchlist/notas | Migrar sin pérdida | Inventario, importación idempotente, backup y reversión |
| EDGAR y Yahoo wrappers | Usar como referencia de integración | Nuevo contrato de hechos y errores; no trasladar heurísticas ciegamente |
| 6 pesos de evaluación | Conservar como preferencia | Plantillas aplicables, evidencia y bloqueos antes de nota |
| DCF, reverse, DDM, score y FX actuales | Reimplementar desde especificación | No aceptar paridad numérica sin coherencia económica |
| Screener y snapshots | Reemplazar | Resumen de runs persistidos, sin segundo motor |
| HTML/JS grandes, CSS superpuesto | Migrar por flujo | Componentes tipados; proteger rutas y datos del usuario |
| Targets de EPS/PER con defaults, bonos fijos silenciosos, sellos «auditado» | Retirar | No sustituidos por otro dato inventado |
| Integraciones muertas y fórmulas duplicadas | Retirar al cerrar migración | Comprobar consumidores antes de borrar |

## Lectura del estado actual

El prototipo logró explorar funciones y detectar necesidades. Aproximadamente 20.000 líneas entre módulos backend, JS, HTML y CSS hacen que cambios locales produzcan inconsistencias entre pantallas. El problema central es la falta de un contrato único de significado y de una evaluación común. Separar archivos sin resolver esas dos cosas no arreglaría el producto.
