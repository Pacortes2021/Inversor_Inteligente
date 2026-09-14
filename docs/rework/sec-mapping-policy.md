# Política SEC inicial · R10

Versión activa: `sec-us-gaap-r10-v1`.

El adaptador canónico acepta únicamente hechos `us-gaap` sin dimensiones. Conserva CIK, accession, taxonomía, etiqueta, unidad, período, valor original, documento, hash y política de mapeo. Una taxonomía extendida queda `unsupported`; una dimensión, unidad o período no soportado queda `blocked`. No se elige un concepto por similitud textual ni por magnitud.

## Conceptos cubiertos

La tabla ordenada de candidatos vive en `backend/v2/adapters/providers/sec_mapping.py`. Cubre ingresos, resultado operacional, utilidad neta, flujo operacional, capex, caja, deuda corriente/no corriente, acciones medias básicas/diluidas y EPS básico/diluido. El orden es parte de la política versionada. Capex usa convención de desembolso positivo; los motores posteriores lo restarán una sola vez.

Las monedas se extraen de la unidad XBRL (`USD`, `EUR`, etc.); no se presume USD. `shares` y `MON/shares` son unidades distintas. Para acciones y EPS, la base queda `unknown` salvo que la ingesta aporte una base accionaria identificada. Una comparación ya ligada a la misma base ajustada por split se reutiliza sin otro ajuste.

## Períodos y conciliación congelada

Un instante nunca recibe fecha inicial. Los hechos de duración se clasifican como FY, trimestre independiente o YTD usando formulario, período fiscal, frame y duración. TTM exige cuatro trimestres fiscales únicos y consecutivos, o el puente `FY anterior + YTD actual − YTD comparable anterior`; ambas rutas generan linaje tipado con todos sus inputs.

Los fixtures `msft-2025-curated.json` y `nflx-2025-curated.json` contienen sólo observaciones seleccionadas y metas de conciliación, no copias de payloads SEC. Se contrastan con los 10-K oficiales identificados por accession. La deuda total de la prueba es la suma explícita de porción corriente y no corriente; no existe una etiqueta total inventada.
