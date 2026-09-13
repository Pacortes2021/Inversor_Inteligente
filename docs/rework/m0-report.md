# Informe de implementación M0 para revisión

Base: `origin/codex/rework-core` en `3575d9b2e42e139367b0c810d1654ee563da008e`. Rama: `codex/rework-m0`. Destino de revisión: `codex/rework-core`. Este informe no contiene rutas personales ni inventarios privados.

## Resultado por tarea

| Tarea | Resultado revisable | Evidencia |
|---|---|---|
| R00 | Referencia, checkout principal y puertos inventariados sin tocar el legado; datos v2 separados; utilidad de inventario/respaldo local ignorado por Git. | `baseline.md`, `scripts/v2_inventory.py`; manifest privado con cinco archivos copiados y hashes, no publicado. |
| R01 | A01–A14 tienen entradas, salidas razonadas, estado y hito de activación. Dos defectos prioritarios del legado se reproducen en caracterización separada. | `tests/v2/fixtures/manifest.json`, `tests/v2/acceptance/`, `tests/v2/characterization/`. |
| R02 | Fact, identidad, ShareBasis, Snapshot, Assessment, Scenario, FCFF request, ProviderResult y errores están tipados. Hay validación Draft 2020-12 con formatos y validación semántica con códigos estables. | 13 esquemas generados, `openapi.json`, ejemplos positivos y ocho negativos publicados. |
| R03 | Python/Node y dependencias quedan bloqueados; CI no usa credenciales ni proveedores; FastAPI v2 expone health tipado y React/Vite compila bajo `/v2/`. | `uv.lock`, `package-lock.json`, workflow M0 y `docs/development.md`. |

## Pruebas ejecutadas

| Comando | Resultado |
|---|---|
| `.venv/bin/python -m pytest -q tests/test_*.py` | 84 aprobadas. Suite legada. |
| `.venv/bin/python -m pytest -q tests/v2/characterization` | 2 aprobadas. Sólo caracterización; no aceptación de v2. |
| `.venv/bin/python -m pytest -q tests/v2/acceptance` | 2 aprobadas. Catálogo/oráculos de M0. |
| `.venv/bin/python -m pytest -q tests/v2/contract` | 21 aprobadas; dos advertencias deprecadas de TestClient aguas arriba. |
| `.venv/bin/python -m pytest -q` | 109 aprobadas; mismas dos advertencias. |
| `npm --prefix web run build` | TypeScript y Vite aprobados; 15 módulos transformados. |
| `uv sync --frozen --dev` en entorno temporal vacío y `pytest -q tests/v2` | Instalación reproducible; 25 aprobadas. |
| `python scripts/export_v2_schemas.py` seguido de diff | Generación determinista, sin divergencias. |

Los tests normales no usan red ni proveedores. Los casos sintéticos no verifican datos de una empresa real y la suite histórica no prueba exactitud financiera integral.

## Límites deliberados

- No se implementó motor FCFF, reverse, períodos TTM, FX, scoring, persistencia ni adaptadores. A01–A03 y A05–A14 son oráculos pendientes de su hito, no funcionalidades aprobadas.
- FastAPI ofrece sólo health; el frontend es un límite compilable, no un rediseño funcional.
- El respaldo privado cubre archivos regulares de datos del backend. `localStorage` y sus orígenes se inventarían/exportarían en R41; no se afirma que ya estén respaldados.
- Python 3.12.13 enlaza SQLite 3.50.4. Health informa que falta la corrección WAL-reset incluida desde 3.53.0. No se activa WAL ni persistencia; actualizar ese runtime es puerta de M1.
- La pertenencia de IDs a repositorios, la inmutabilidad durable y la resolución de bindings contra snapshot/revisiones requieren M1.
- Los umbrales de scoring siguen rotulados como política propuesta, no calibración ni capacidad predictiva.

## Solicitud concreta a Astra

Revisar el diff, ejecutar contratos y negativos, y responder los puntos de `m0-decisions.md`: publicación con precisión de fecha, anclaje de períodos FCFF, exclusión mutua de acciones/reclamaciones, bindings y gate SQLite. No validar el hito sólo por el total de pruebas.

La revisión de M0 habilitaría R04, pero M1 permanece sin iniciar y no debe fusionarse a `main` desde esta entrega.
