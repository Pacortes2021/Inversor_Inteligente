# Desarrollo reproducible de v2

## Requisitos

- `uv` 0.10.10.
- Python 3.12 administrado por `uv`.
- Node 22.23.2 LTS y npm 10.9.8 (también fijados en `.nvmrc` y `package.json`).
- Un `INVERSOR_DATA_DIR` vacío y exclusivo de v2 cuando se pruebe persistencia en M1.

No se requieren credenciales ni red de proveedores para construir o probar M0.

## Preparar y comprobar

```sh
uv sync --frozen --dev
uv run pytest -q
uv run python scripts/export_v2_schemas.py
npm --prefix web ci
npm --prefix web run build
```

Después de exportar esquemas, `git diff --exit-code -- docs/rework/contracts/generated` debe permanecer limpio. Los esquemas generados describen estructura; las reglas cruzadas se comprueban además con validadores semánticos.

## API mínima

Use siempre un directorio de datos de desarrollo separado:

```sh
INVERSOR_DATA_DIR="$PWD/var/dev-data" uv run uvicorn backend.v2.bootstrap:app --host 127.0.0.1 --port 8762
```

La única ruta funcional de M0 es `GET /api/v2/health`. No hay un motor de valoración, puntuación ni proveedor activo.

## SQLite enlazado

```sh
uv run python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

El Python 3.12.13 administrado quedó enlazado localmente con SQLite 3.50.4. La comprobación se expone en health y no se confunde con la versión del ejecutable `sqlite3` del sistema. La documentación oficial ubica la corrección del [defecto de corrupción al reiniciar WAL](https://sqlite.org/wal.html#walresetbug) en SQLite 3.51.3, con backports 3.50.7 y 3.44.6. Por ello M0 no activa WAL y el gate `sqlite_wal_reset_fix` permanece falso en este runtime. M1 deberá usar una de esas revisiones corregidas o posterior antes de habilitar concurrencia WAL. `foreign_keys=ON` y `busy_timeout` se prueban junto al adaptador real; M0 no simula persistencia para dar por cumplida esa fase.
