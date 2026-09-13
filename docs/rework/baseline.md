# Línea base de M0

Registro: 13 de septiembre de 2026. Este archivo publica sólo metadatos de ingeniería; no contiene rutas personales, nombres de archivos privados, secretos ni contenido del portafolio.

## Referencias congeladas

| Rol | Rama / revisión | Estado observado antes de editar |
|---|---|---|
| Referencia funcional auditada | `codex/data-confiable` · `5d36ea301b0abee5e58d2aa750bb7d6e996d5ee3` | Conservada; es referencia de comportamiento, no oráculo financiero. |
| Integración del rework | `origin/codex/rework-core` · `3575d9b2e42e139367b0c810d1654ee563da008e` | Contiene la referencia auditada y el diseño versionado. |
| Implementación M0 | `codex/rework-m0`, creada desde `3575d9b2e42e139367b0c810d1654ee563da008e` | Worktree aislado y limpio antes del primer cambio. |
| Checkout principal | `main` · `ae0ec75411953ea838060d6a5b4e6adec2e14343` | Seis rutas con trabajo local previo; no se enumeran ni modifican desde M0. |

El checkout principal estaba 13 commits por delante y 63 por detrás de `origin/main`; esa divergencia no se reconcilió porque pertenece al usuario. No se ejecutaron `reset`, `clean`, cambio de rama ni escritura sobre ese checkout.

## Aplicación y aislamiento

- Aplicación legada: loopback `127.0.0.1:8756`, datos en su directorio legado dentro del checkout principal. Sus módulos de notas, watchlist, portafolio y snapshots escriben allí. M0 no cambia puerto, proceso ni datos.
- API v2 de desarrollo: loopback `127.0.0.1:8762`.
- Vite de desarrollo: loopback `127.0.0.1:5173`, con proxy exclusivo a `/api/v2`.
- Datos v2: siempre mediante `INVERSOR_DATA_DIR`, fuera del checkout de distribución. En pruebas se usa un directorio temporal. M0 no crea todavía el esquema persistente de M1.
- No hay llamadas de proveedores en la suite M0 ni datos de desarrollo compartidos con el legado.

## Runtime observado y runtime fijado

El runtime del sistema observado fue Python 3.9.6, Node 26.0.0 y el ejecutable SQLite 3.51.0. El sistema no es el entorno reproducible del proyecto. M0 fija Python 3.12.13, Node 22.23.2, npm 10.9.8 y dependencias exactas en los lockfiles. El Python bloqueado enlaza SQLite 3.50.4, que no debe confundirse con el ejecutable del sistema. Como es anterior al backport corregido 3.50.7 del defecto WAL-reset, M0 informa el límite y no activa WAL ni persistencia.

## Inventario y resguardo privado

`scripts/v2_inventory.py` permite crear, dentro de `var/private-baseline/`, un inventario y una copia privada de las categorías legadas permitidas. Esa carpeta está ignorada por Git. El manifest registra ruta relativa, tamaño y SHA-256; nunca lee `.env`, claves ni caches. El respaldo sólo copia archivos regulares de datos explícitamente seleccionados y no accede al almacenamiento del navegador.

El inventario privado se mantiene local. Git conserva la referencia de código por commit; Git no es un respaldo de datos personales. El almacenamiento de navegador deberá exportarse por cada origen durante R41/M8, porque `file://`, localhost y distintos puertos no comparten necesariamente el mismo almacén.

## Comprobaciones y límites

- La rama de integración y los documentos de diseño se comprobaron antes de editar.
- La primera ejecución de la suite legada con el Python global quedó bloqueada antes de recolectar tests: un complemento global ajeno al repositorio intentó abrir un socket local. El entorno bloqueado desactiva ese complemento y ejecuta la suite desde sus dependencias declaradas.
- La comprobación de escucha del puerto legado no produjo datos publicables concluyentes; no se inició ni detuvo el servidor del usuario. La salud del legado se evalúa mediante su suite determinista, no mediante una mutación del proceso en uso.
- El respaldo de `localStorage` no se automatiza en M0 y queda explícitamente para la previsualización de migración. No se afirma que las notas del navegador ya estén respaldadas.
