# Backlog ejecutable para Sol

Leer [producto](02-producto-y-ux.md), [arquitectura](03-arquitectura-y-contratos.md), [motores](05-motores-financieros.md) y [validación](06-migracion-y-validacion.md). Las rutas de esta tabla son propuestas relativas al nuevo worktree, no archivos ya implementados. Cada ID representa una entrega acotada; dividirla si no puede revisarse de forma independiente. Los IDs Axx remiten a la matriz de aceptación del documento 06.

Reglas de trabajo: implementar una tarea o un conjunto pequeño de dependencias inmediatas; no modificar archivos compartidos desde agentes en paralelo; registrar desviaciones antes de propagar contratos. Cada entrega incluye diff, pruebas y demostración. Un test que sólo fija el valor incorrecto del legado es caracterización, no aceptación del rework.

## M0 · Congelar semántica y referencia

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R00 | — | `docs/rework/baseline.md`, configuración del worktree | Registrar HEAD, cambios previos, puertos, runtime y ubicación de datos. Incorporar este paquete al worktree de rework sin sobrescribir main. | Estado de ambos checkouts registrado; app anterior funciona; directorio v2 separado. |
| R01 | R00 | `tests/v2/fixtures/manifest.json`, `tests/v2/acceptance/` | Convertir A01–A14 en casos mínimos con entradas y resultados razonados. Guardar reproducción legada separada. | Suite legada ejecutada y reportada; ejemplos de fallos reproducibles sin depender de precios actuales. |
| R02 | R01 | `backend/v2/domain/`, `backend/v2/api/schemas/`, `tests/v2/contract/` | Implementar contratos Fact, identidad, Snapshot, Assessment, Scenario y errores. Resolver restricciones semánticas de `contracts/README.md`; generar OpenAPI. | Ejemplos válidos aceptados; negativos rechazados con causa; null no se transforma en cero. Revisión financiera/arquitectura M0. |
| R03 | R00, R02 | `pyproject.toml`, archivo de bloqueo Python, `web/package.json`, lockfile, `.github/workflows/`, `docs/development.md` | Fijar versiones compatibles y comandos únicos; esqueleto FastAPI v2 y frontend compilable. Verificar SQLite enlazado y correcciones vigentes. | Instalación reproducible en entorno limpio; CI ejecuta contratos y build, sin credenciales ni red de proveedores. |

## M1 · Construir la base de datos verificable

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R04 | R02, R03 | `domain/instruments.py`, `adapters/persistence/migrations/`, `repositories.py` | Emisor, instrumento, listing, símbolos vigentes y relación ADR. Crear migraciones numeradas y repositorios transaccionales. | Dos plazas/clases no colisionan; renombre conserva identidad; FK impide referencias huérfanas. A24. |
| R05 | R04 | `adapters/persistence/raw_store.py`, `domain/facts.py`, `observations.py` | Guardar crudo por hash, documento, observaciones y linaje; separar escala original/canónica. | Importación repetida no duplica; evidencia recuperable; originales inmutables; A01/A04. |
| R06 | R05 | `application/select_facts.py`, `application/reconcile.py`, `domain/policies.py` | Selección por contexto y modo histórico; conservar candidatos y resolución. | Conflicto material bloquea dependientes; revisiones posteriores no aparecen antes de publicarse; A23. |
| R07 | R06 | `application/snapshots.py`, `api/snapshots.py`, `api/facts.py` | Snapshot de hechos seleccionados y evidencia consultable; identidad de listing/precio. | Replay sin red; GET no altera estado económico; misma entrada/política produce mismo hash. A16. |
| R08 | R05 | `ports/providers.py`, `jobs/worker.py`, `jobs/policies.py`, `api/jobs.py` | Trabajos persistentes, leases, cancelación, límites, caché por recurso y último dato válido. | Interrumpir y reiniciar recupera trabajo; 429 respeta Retry-After; error no sustituye snapshot válido; encolado idempotente. A15. |

## M2 · Fuente primaria de EE.UU. y precios identificados

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R09 | R04, R05, R08 | `adapters/providers/sec.py`, `tests/v2/fixtures/sec/` | Resolver CIK y descargar submissions/companyfacts con identificación, rate limit y crudo conservado. | Recupera accession, publicación, taxonomía, unidad y períodos; USD no es única unidad admitida. No peticiones SEC desde navegador. |
| R10 | R06, R09 | `adapters/providers/sec_mapping.py`, `engines/periods.py` | Mapear conceptos iniciales y derivar trimestres/YTD/TTM con contexto. Fallar explícitamente con extensiones/dimensiones no soportadas. | MSFT y NFLX conciliados en ingresos, EBIT, utilidad, CFO, capex, caja, deuda y acciones. A02/A03/A06/A10. |
| R11 | R08 | `adapters/providers/yahoo.py`, `domain/market_data.py` | Obtener precio, sesión, calendario y acciones corporativas como capacidades separadas; rotular Yahoo. | Distinguir precio bruto, split-adjusted y total-return; no llamar Nasdaq equivalente por defecto; caída conserva cierre anterior. |
| R12 | R10, R11, R07 | `application/ingest.py`, `application/capabilities.py`, `docs/rework/provider-pilot.md` | Publicar primer snapshot EE.UU.; informe de capacidad documentada vs probada. | Lectura de hechos desde API con fuente exacta; ninguna etiqueta global «100% auditado»; prueba sin red y smoke test fechado separados. |

## M3 · Chile y monedas

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R13 | R05, R08 | `adapters/providers/cmf.py`, `tests/v2/fixtures/cmf/`, `docs/rework/cmf-spike.md` | Prueba acotada de descubrimiento y extracción de documentos no bancarios de tres emisores. Registrar acceso, taxonomía, formatos y fallos. | Extraer/confrontar cifras prioritarias de COPEC, CENCOSUD y QUIÑENCO o concluir con evidencia qué no se pudo automatizar. No bloquear todo el hito por scraping. |
| R14 | R13, R06 | `adapters/providers/document_import.py`, `api/imports.py`, `web/src/features/data/import/` | Ruta de importación de archivo/tabla oficial con período, moneda, escala y ubicación; previsualizar y aplicar por token de validación. | Rechazar archivo inválido y duplicado; preservar documento original; una cifra manual importada sigue siendo reportada si se transcribe con evidencia. A04. |
| R15 | R13, R14 | `adapters/providers/cmf_banks.py`, `domain/capabilities.py` | Separar capacidad bancaria CMF de corporativa; resolver CHILE.SN y conceptos de balance/resultado bancario. | Banco muestra datos propios y bloqueo del DCF industrial; no se generaliza API de bancos a todas las empresas. |
| R16 | R08, R11 | `adapters/providers/bcch.py`, `engines/currency.py`, `tests/v2/fixtures/fx/` | FX diario documentado y motor de compatibilidad; tasas por fecha, regla para día sin publicación, reportes conservan moneda. | CLP/USD nunca sumados; EPS USD convertido a base CLP fechada cuando corresponde; A05/A19; secreto ausente de logs/exportaciones. |
| R17 | R12, R14, R15, R16 | `application/capabilities.py`, `docs/rework/provider-pilot.md` | Cerrar matriz del piloto: capacidad por emisor/dato, cobertura histórica real, faltantes y vía de resolución. | COPEC consultable aunque no tenga SEC; no afirmar cobertura universal ni consenso gratuito asegurado. Revisión M3 con documentos. |

## M4 · Motores financieros centrales

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R18 | R10, R17 | `engines/normalization.py`, `domain/adjustments.py`, `api/normalization.py` | Libro de ajustes con impuestos, recurrencia, autor y evidencia; puente reportado→normalizado. | Revertir ajuste crea revisión; SBC/extraordinario afecta input efectivo; no eliminar pérdidas ni añadir SBC por D&A. |
| R19 | R18 | `engines/quality.py`, `engines/periods.py` | ROIC, ROE, conversiones, márgenes, deuda, dilución y crecimiento; requisitos de historia por métrica. | A01/A02/A10/A12; denominador no positivo explica no interpretabilidad; crecimiento adquirido/FX no llamado orgánico. |
| R20 | R02, R18, R16 | `engines/valuation/fcff.py`, `domain/scenarios.py`, `tests/v2/unit/test_fcff.py` | FCFF por drivers, fechas de descuento, terminal con reinversión y puente equity; base accionaria explícita. | Oráculo numérico de contratos coincide; deuda se resta una vez; WACC≤g bloqueado; futuro no incluye flujos realizados. Revisión de fórmula antes de conectar UI. |
| R21 | R20 | `engines/valuation/reverse.py`, `sensitivity.py` | Resolver una variable realmente activa con intervalo/tolerancia/residual; sensibilidad usa mismo motor. | A08/A09; precio sintético recupera growth conocido; sin cruce/variable plana no produce una solución falsa. |
| R22 | R20, R21 | `engines/valuation/scenarios.py`, `engines/returns.py` | Escenarios compatibles, MoS separado de upside, precio de salida y flujos del inversor; benchmark manual documentado. | A07/A11/A13/A19; retorno nominal distinguido de real; cero/múltiples IRR explicados; no usar WACC como retorno esperado del accionista. |
| R23 | R19, R22 | `application/assess.py`, `api/assessments.py`, `api/simulations.py` | Única evaluación versionada; simulación pura con requestId y linaje. Validación de inputs críticos y modelo aplicable. | Snapshot+revisiones reproducen resultado sin red. Cambiar supuesto actualiza todos sus dependientes. A16/A18/A22. |

## M5 · Primer expediente completo

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R24 | R03, R07, R23 | `web/src/api/`, `web/src/routes/`, `web/src/components/` | Cliente tipado generado, rutas `/v2/`, estados y componentes dato/evidencia/cobertura. | Types/build pasan; sin fetch duplicado al renderizar; cancelación y reintento real; evidencia en ≤2 interacciones. |
| R25 | R24, R17 | `web/src/features/company/`, `web/src/features/data/` | Negocio, estados, calidad y puente de normalización; distinguir fuente, estimación, frescura y conflicto. | MSFT/COPEC muestran moneda nativa y faltantes concretos; no totalizan campos desconocidos como cero. |
| R26 | R24, R23 | `web/src/features/valuation/` | Editor de escenarios con supuestos justificados, DCF/reverse/sensibilidad y comparación ETF coherentes. | A07/A18; no fórmulas financieras en JS; cálculo pendiente no muestra como vigente una conclusión anterior. |
| R27 | R24, R05 | `application/theses.py`, `api/theses.py`, `web/src/features/research/` | Tesis, motores, competidores, riesgos, invalidaciones, evidencia y revisión con control de concurrencia. | A17; guardar sin evidencia no otorga puntos; 409 no pisa cambios; reload conserva contenido y revisión. |
| R28 | R19, R22, R27 | `engines/scoring.py`, `domain/scoring_policy.py`, `web/src/features/company/scorecard.tsx` | Implementar política 09 con subtotal, cobertura, pendientes y motivos. Etiquetar financial/personal. | Suma de máximos100; ejemplos de09; A14; ninguna plantilla industrial aplicada a bancos/REIT sin revisión. |
| R29 | R25, R26, R27, R28 | `tests/v2/acceptance/`, `web/e2e/`, `api/exports.py` | Demostrar recorrido MSFT y COPEC de evidencia a decisión y exportar revisión exacta. | A17/A18; abrir A luego B exporta B; datos vacíos/proveedor lento/teclado funcionan. Revisión de producto M5. |

## M6 · Modelos apropiados por negocio

Antes de activar cada modelo, su tarea entrega contrato tipado, fórmula completa, criterio de aplicabilidad, inputs críticos, ejemplo calculado independientemente y política de score sectorial. La sección sectorial de05 define el punto de partida; no copiar un ratio industrial para llenar todos los campos. Si falta una variable, la ficha puede utilizar importación con evidencia y conservar el modelo pendiente.

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R30 | R23, R15 | `domain/model_policy.py`, `engines/valuation/bank.py`, `contracts/bank/` | Clasificador económico editable/versionado; banco DDM y residual con puente patrimonial/capital. | Ejemplo05; descuento a ke; patrimonio/distribuciones coherentes; sin capital sostenible, A22. Aseguradoras permanecen bajo contrato específico pendiente. |
| R31 | R23, R14 | `engines/valuation/reit.py`, `contracts/reit/` | Conciliación FFO→AFFO, valores por múltiplo documentado y NAV por activos. | Reproduce ejemplo05; capex recurrente y reclamaciones no duplicados; VICI con evidencia o faltantes precisos. |
| R32 | R23 | `engines/valuation/cyclical.py`, `contracts/cyclical/` | Ciclo medio mediante volumen/precio/costo/reinversión, sin reemplazar pérdidas por promedio positivo. | Ejemplo05 y sensibilidad de precio; pico y ciclo medio separados. Horizonte documentado, muestra insuficiente bloqueada. |
| R33 | R23, R30, R31, R32 | `engines/valuation/sotp.py`, `contracts/sotp/` | Suma de partes con participaciones y puente holding, métodos compatibles por segmento. | Ejemplo05; no restar deuda de subsidiaria dos veces; falta de segmento material impide total concluyente. |
| R34 | R30–R33, R28 | `domain/sector_scoring_policy.py`, `web/src/features/valuation/`, `tests/v2/acceptance/` | Plantillas sectoriales revisadas y presentación de modelos; puntuación comparable sólo dentro de políticas aprobadas. | Auditoría financiera por plantilla, pesos 100 y evidencia mínima. Un método no soportado no genera recomendación industrial. |

## M7 · Ranking, cartera y seguimiento

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R35 | R28, R29 | `application/screen.py`, `application/compare.py`, `api/screener.py`, `web/src/features/research/` | Consultar evaluaciones existentes con filtros de modelo/moneda/modo/cobertura/versiones. Mostrar ranking y comparación consistente. | Mismo assessmentId ⇒ mismos valores en todas las vistas; A14; no comparaciones de monedas implícitas ni forecast nuevo al pintar una fila. |
| R36 | R22, R16, R11 | `engines/benchmark.py`, `web/src/features/research/benchmark.tsx` | VT y VOO separados: historial observado, hipótesis futura, horizonte y prima exigida. Datos de retorno con política de ajustes. | Dividendos no duplicados; retorno CLP requiere escenario FX; umbral personal nunca rotulado consenso. |
| R37 | R04, R05 | `domain/ledger.py`, `application/transactions.py`, `api/portfolio.py`, `web/src/features/portfolio/` | Ledger transaccional con correcciones y preview de importación; compras/ventas/caja/comisiones/dividendos. | A20; saldos por moneda, no unidades sumadas; eventos idempotentes y trazables, ausencia de movimientos no interpretada como éxito del proveedor. |
| R38 | R37, R36 | `engines/portfolio.py`, `engines/returns.py`, `application/personal_assess.py` | TWR/XIRR, exposición y encaje personal; simulación de posición limitada por política explícita. | Fixture de aportes separa TWR de XIRR; ledger incompleto bloquea alfa/tamaño; solapamiento ETF desconocido visible. |
| R39 | R27, R08, R23 | `application/monitor.py`, `domain/alerts.py`, `web/src/features/research/reviews.tsx` | Revisión de tesis por fechas/condiciones; jobs al abrir/usar app y alertas persistentes. | Evento no se duplica al reiniciar; diferencia alerta de dato vs tesis; interfaz informa que no monitoriza con app cerrada. |
| R40 | R37, R39, R27 | `adapters/persistence/backup.py`, `application/restore.py`, `api/backups.py` | Backup consistente DB+documentos+revisiones+alertas; restauración validada a directorio alternativo. | A21, permisos de archivos y hashes; secretos excluidos; backup parcial se rechaza con explicación. |

## M8 · Migración y cierre

| ID | Dependencias | Archivos principales | Trabajo y resultado esperado | Validación / terminado |
|---|---|---|---|---|
| R41 | R40 | `compatibility/legacy_import.py`, `web/src/features/data/legacy_export/`, `docs/migration.md` | Inventario de backend/localStorage, exportación por origen, preview y ensayo de migración. | Cantidades/notas/alertas completas y duplicados resueltos; evaluaciones v1 etiquetadas legadas, no verificadas v2. |
| R42 | R35, R36, R38, R39, R41 | `web/e2e/`, `tests/v2/acceptance/`, `docs/rework/acceptance-report.md` | Recorrer matriz A01–A24 y piloto por capacidades; medir carga local. | Cada criterio aprobado, limitado con causa o con tarea correctiva; ningún P0/P1 abierto sobre datos, valoración, guardado o migración. |
| R43 | R42 | `backend/v2/bootstrap.py`, scripts de inicio, `README.md`, redirecciones frontend | Distribución local con un inicio, assets compilados y rutas antiguas resueltas. | Arranque desde entorno documentado, sin Node para uso final; no servidor obligatorio de terceros; origen local protegido. |
| R44 | R43 | `compatibility/`, archivos legados reemplazados, `docs/rework/cutover.md` | Corte final siguiendo06 y retirada gradual de fórmulas/almacenes duplicados. | Respaldo final y reversión ensayados; evaluación nueva reproducible; antiguo checkout y datos previos preservados. Revisión Astra final. |

## Cómo demostrar terminado

Cada tarea registra: ID, base y commit/diff, archivos modificados, resultado visible o fixture, pruebas ejecutadas, fallos conocidos y siguiente ID habilitado. Si se cambia semántica, actualizar primero contrato y ejemplo de aceptación en el mismo diff. No afirmar «datos confiables» como un estado universal: informar qué conceptos se conciliaron, con qué documentos y en qué fecha.

La revisión financiera de R20/R21/R28/R30–R34 puede hacerse con una segunda revisión independiente del código y los ejemplos. Un documento de diseño no obliga a activar un modelo que no supera sus pruebas. El criterio para detener una parte es una dependencia concreta o un resultado incorrecto; se continúa con las tareas independientes que sigan autorizadas.

## Fuera de este backlog inicial

Ejecución de órdenes, conexión a broker, distribución comercial, feed en tiempo real garantizado, suscripciones, consenso masivo y backtest de estrategia con universo histórico libre de supervivencia. FCFE, aseguradoras y escenarios de liquidación tienen extensión posterior con contratos propios; mientras tanto muestran aplicabilidad/limitación. Estas exclusiones no impiden leer estados ni documentar tesis de esos negocios.
