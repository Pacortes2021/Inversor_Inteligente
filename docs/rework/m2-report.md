# Informe M2 · Fuente primaria de EE.UU. y precios identificados

Fecha de cierre local: 2026-09-14. Rama: `codex/rework-m2`. Base de integración permitida: `codex/rework-core`; este hito no se integra directamente en `main`.

## Entregas

| Tarea | Commit | Resultado |
|---|---|---|
| R09 | `ed6b77c` | Captura SEC identificada, limitada, reintentable y conservada por hash para identity, submissions y companyfacts. |
| R10 | `e60734e` | Mapeo US-GAAP explícito, conciliación MSFT/NFLX y derivaciones de períodos con linaje. |
| R11 | `88e1973` | Yahoo mediante yfinance como fuente secundaria, con precio, sesión, cobertura observada y acciones separadas. |
| R12 | `90ccec6` | Primer snapshot USA reproducible sin red y reporte de capacidades por nivel de evidencia. |
| Revisión | `f60b92e` | Correcciones de identidad de capturas SEC, cutoff histórico, calendario fiscal, semántica de `Close`, calidad y ventanas TTM. |
| Revisión | `9716d03` | Bloqueo de YTD comparables que exceden el ejercicio fiscal. |

## Evidencia y alcance comprobado

La fuente SEC conserva CIK, accession, formulario, publicación, taxonomía, etiqueta, unidad, fechas, documento y hash. Los fixtures de Microsoft FY2025 y Netflix FY2025 son extractos curados para conciliación, no copias presentadas como payload crudo. Se contrastaron con los [datos y API EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), el [10-K FY2025 de Microsoft](https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm) y el [10-K 2025 de Netflix](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/nflx-20251231.htm).

El mapper no adivina extensiones, dimensiones, unidades o calendarios fiscales. Los frames SEC se tratan como calendarios; un período no calendario queda bloqueado hasta contar con un calendario fiscal identificado. TTM sólo acepta conceptos aditivos, cuatro FQ únicos de 60–120 días, fechas contiguas, ventana total de 330–380 días y entradas disponibles, válidas y sin conflicto. El puente FY/YTD exige continuidad real, comparables anuales y YTD parciales contenidos en su ejercicio.

Yahoo queda rotulado como fuente secundaria obtenida mediante yfinance. Con `auto_adjust=False`, `Close` se conserva como `split_adjusted` y no se vuelve a dividir por eventos; `Adj Close` queda separado como `total_return`. La integración no afirma disponer de una serie histórica bruta ni de un calendario oficial de bolsa. yfinance declara que no está afiliado ni validado por Yahoo y que la herramienta está orientada a investigación y educación personal: [documentación oficial](https://ranaroussi.github.io/yfinance/) y [README oficial](https://github.com/ranaroussi/yfinance/blob/main/README.md?plain=1).

El snapshot offline identifica emisor, instrumento, listing, MIC, moneda, símbolo vigente, base accionaria, hechos seleccionados y precio. Su lectura por API recupera decisiones, documentos y hashes sin consultar proveedores ni cambiar la fecha económica. El precio del fixture es sintético y sólo demuestra la cadena de datos; no constituye una cotización real.

## Verificación final

- Suite completa: **198 aprobadas, 2 omitidas**.
- Omitidas: smokes en vivo SEC y Yahoo, ambos opt-in y dependientes de red/identificación externa.
- Advertencias: 2 deprecaciones upstream de FastAPI/Starlette TestClient; no son fallos funcionales del hito.
- Interfaz: compilación TypeScript/Vite aprobada.
- Working tree: limpio después de los commits de cierre.

Astra realizó cuatro pasadas adversariales. Detectó problemas de disponibilidad histórica, identidad inmutable SEC, semántica de Yahoo `Close`, calendario fiscal, aditividad, calidad y límites temporales. Todos quedaron reproducidos por regresiones y corregidos. Resultado final: sin hallazgos materiales; aprobado para revisión humana e integración en `codex/rework-core`.

## Limitaciones y estado remoto

No se ejecutaron smokes externos ni se afirma cobertura universal, tiempo real, datos oficiales de bolsa o estado global «100% auditado». La cobertura reconciliada sigue limitada a los extractos FY2025 documentados; extensiones, dimensiones y calendarios fiscales no coincidentes permanecen explícitamente bloqueados.

Los commits posteriores a `ed6b77c` siguen locales. La PR #18 y los issues #14–#17 no deben actualizarse hasta contar con autorización explícita para publicar la rama en `origin`.
