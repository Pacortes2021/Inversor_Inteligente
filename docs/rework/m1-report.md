# Informe de implementación M1 para revisión

Base: `origin/codex/rework-core` en `bfd05b5`. Rama: `codex/rework-m1`. PR: [#13](https://github.com/Pacortes2021/Inversor_Inteligente/pull/13), con destino `codex/rework-core`. No se modificaron `main`, el checkout principal, los datos legados ni el proceso existente.

## Resultado por tarea

| Tarea | Resultado revisable | Evidencia |
|---|---|---|
| R04 | Identidad canónica persistente para emisor, instrumento, clase, listing, símbolos históricos, ADR y base accionaria. Las claves foráneas rechazan huérfanos y dos plazas con igual símbolo no colisionan. | Migración `0001_identity.sql`, `IdentityRepository`, `test_identity_persistence.py`; commit `0f07670`. |
| R05 | Archivos crudos por SHA-256, publicación atómica sin reemplazo, documentos y observaciones inmutables, evidencia verificable y aristas de linaje. Reimportar el mismo contenido/hecho es idempotente. | Migración `0002_documents_and_facts.sql`, `RawStore`, `FactRepository`, `test_fact_persistence.py`; commit `1b3cae3`. |
| R06 | Selección determinista por identidad, plaza, concepto, unidad, moneda, período y contexto exactos. La fecha de disponibilidad limita consultas históricas; se conservan revisiones y un conflicto material no elige ganador silencioso. | Migración `0003_selection_decisions.sql`, `select_facts.py`, `reconcile.py`, `test_fact_selection.py`; commit `90cf591`. |
| R07 | Snapshots inmutables derivados de hechos y decisiones seleccionadas, con hash estable, precio ligado a instrumento/listing/moneda y replay local. API de snapshot, hechos y metadatos de evidencia sin efectos de escritura en GET. | Migración `0004_snapshots.sql`, `SnapshotRepository`, `snapshots.py`, API y `test_snapshot_replay.py`; commit `8b26962`. |
| R08 | Jobs persistentes con clave idempotente, leases recuperables, cancelación cooperativa, reintento con backoff/jitter y `Retry-After`, historial de intentos y caché que separa último éxito de último error. | Migración `0005_jobs_and_cache.sql`, `JobRepository`, `CacheRepository`, `Worker`, API y `test_persistent_jobs.py`; commit `93cf12a`. |

## Criterios de aceptación activados

- **A15:** un 429 conserva el valor anterior, deja el trabajo reintentable y no reclama antes de `Retry-After`; una respuesta exitosa más antigua tampoco reemplaza una nueva.
- **A16:** dos lecturas del snapshot entregan el mismo contenido, no alteran las tablas económicas y funcionan con la red bloqueada.
- **A23:** una revisión queda fuera del snapshot anterior a su publicación y aparece sólo en un corte elegible.
- **A24:** una cotización de otra clase o listing no entra como candidata por similitud del ticker.
- Los casos A01 y A04 también atraviesan persistencia: deuda faltante vuelve como `null`, y CLP conserva escala original explícita.

## Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `.venv/bin/python -m pytest -q` | 153 aprobadas; dos advertencias deprecadas de TestClient aguas arriba. |
| `.venv/bin/python scripts/export_v2_schemas.py` seguido de pruebas de contrato | OpenAPI regenerado y servido sin divergencia. |
| Pruebas de integración R04–R08 | Identidad/FK, archivos y hechos, corte/conflictos, replay/API y jobs/caché aprobados sin proveedores reales. |

## Decisiones de seguridad e integridad

- El runtime enlaza SQLite 3.50.4 y aún no contiene la corrección WAL-reset exigida. La conexión usa journal rollback (`DELETE`) hasta que `has_wal_reset_fix()` reconozca una versión corregida; no se fuerza WAL inseguro.
- Cada operación de repositorio abre su propia conexión, activa claves foráneas y usa transacciones cortas. El claim de un job y la recuperación de leases se serializan con `BEGIN IMMEDIATE`.
- Los originales, hechos, decisiones, snapshots y membresías ya creadas no se actualizan para “corregirlos”; una revisión crea otra identidad inmutable.
- La API sólo encola por un POST explícito. Leer un hecho, snapshot o job no llama proveedores ni crea snapshots.

## Límites deliberados

- R08 entrega la infraestructura y un worker ejecutable de a un trabajo; no inicia un servicio permanente, reloj del sistema ni adaptadores SEC/CMF/BCCh/Yahoo. Esas integraciones comienzan en M2/M3.
- Una publicación sin hora sólo se habilita con un corte de sesión explícito y versionado para esa identidad/fecha; si falta, usa `firstSeenAt`. Los calendarios que calculan esos cortes por plaza y festivo se incorporan con los adaptadores antes de backtests de mercado intradía.
- La caché conserva el último payload válido, pero la política de retención de crudos, backups completos y cuotas de disco aún no está implementada.
- La API de documentos expone metadatos y la API de hechos expone sus enlaces de evidencia; no sirve archivos crudos arbitrarios.
- No se han probado exactitud ni cobertura de empresas reales. Toda la aceptación de M1 usa datos sintéticos y no constituye una recomendación de inversión.

## Solicitud concreta a Astra

La primera revisión sobre `93cf12a` reprodujo diez huecos materiales o moderados. La corrección posterior añade relaciones coherentes emisor/instrumento/listing/base, vigencias no solapadas, hechos válidos para selección, normalización UTC previa al hash, membresía de emisor completa en snapshots, clave de caché completa, leases validados por propietario/intento/vigencia, `Retry-After` desde recepción y límite terminal de intentos. Astra debe repetir esas reproducciones sobre el commit correctivo, no sólo el total de pruebas. M1 sólo puede avanzar a revisión humana de la rama de integración; esta entrega no autoriza fusionar a `main`.
