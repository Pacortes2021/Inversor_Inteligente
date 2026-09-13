# Migración, hitos y validación

Este es un plan de construcción posterior. La entrega de diseño no cambia el servidor ni migra datos personales. Cada hito produce una versión comprobable; completar archivos o conservar resultados erróneos de v1 no constituye aceptación.

## Preparación y aislamiento

Base funcional auditada: commit `5d36ea301b0abee5e58d2aa750bb7d6e996d5ee3`, rama `codex/data-confiable`. El checkout principal tiene cambios locales ajenos al plan. Sol debe inspeccionar el estado, conservarlos y comenzar un worktree de implementación desde esa base, incorporando este paquete documental. Rama propuesta `codex/rework-core`; si ya existe, inspeccionarla antes de reutilizarla. No usar reset, clean ni sustituir el checkout principal.

La aplicación legada conserva su servidor, puerto y directorio de datos. V2 usa otro puerto libre y un `INVERSOR_DATA_DIR` exclusivo. La ruta de interfaz nueva será `/v2/` durante la transición y su API `/api/v2/`. En desarrollo Vite puede tener su propio puerto y proxy; en distribución FastAPI sirve los archivos compilados. No hacer que dos procesos escriban el mismo portafolio.

Primero inventariar datos personales: archivos backend, notas, watchlist, operaciones, escenarios y alertas en almacenamiento del navegador. Registrar ubicación, tamaño, versión y hash; no copiar credenciales ni datos personales al repositorio. El respaldo incluye un manifest y una prueba de restauración en un directorio temporal.

## Hitos y puertas de aceptación

| Hito | Resultado | Dependencias | Condición para pasar |
|---|---|---|---|
| M0 · Referencia y contratos | Entorno reproducible, catálogo de casos, contratos tipados y decisiones cerradas | Ninguna | Reproducir fallos prioritarios, revisar fórmulas/contratos, separar pruebas de caracterización de pruebas de aceptación |
| M1 · Núcleo de datos | Identidad, crudos, hechos, selección, snapshots y trabajos persistentes | M0 | Replay sin red, datos faltantes distintos de cero, importación idempotente, recuperación tras interrupción |
| M2 · EE.UU. | SEC y precios/acciones corporativas secundarios explícitos | M1 | Dos emisores conciliados con documentos, caída de proveedor conserva último dato válido y su antigüedad |
| M3 · Chile y monedas | Piloto CMF o importación oficial verificable; BCCh y monedas nativas | M1; M2 como referencia | COPEC y otras dos muestras documentadas, escala/período verificados, banco separado; sin API corporativa supuesta |
| M4 · Motores centrales | Normalización, calidad, FCFF/reverse, escenarios, retornos y MoS | M2, M3 | Oráculos financieros, sensibilidad y bloqueos; cada resultado reproducible desde snapshot y revisiones |
| M5 · Expediente utilizable | Interfaz del proceso completo, evidencia, evaluación y revisión de tesis | M4 | MSFT y COPEC desde datos hasta decisión; misma revisión en todos los resultados y exportación |
| M6 · Sectores | Contratos y motores banco, REIT, ciclo medio y holding, en ese orden | M4; M5 para presentación | Ejemplo independiente por método, fuentes/inputs completos o bloqueo explícito; plantilla sectorial revisada antes de score |
| M7 · Comparación y cartera | Ranking, VT/VOO, ledger, seguimiento y respaldo integral | M5; M6 para incluir esos sectores | Filtros de elegibilidad, retornos/FX correctos, datos personales restaurables, alertas idempotentes |
| M8 · Sustitución gradual | Importación final, redirecciones, distribución y retirada del código duplicado | M7 | Pruebas críticas de extremo a extremo, reconciliación de datos personales, reversión ensayada |

M0–M5 producen el primer producto útil. M6 se incorpora método por método: un banco puede tener expediente y datos antes de tener valoración. No esperar al último modelo para usar las mejoras ya aceptadas. Una función incompleta se mantiene visible con motivo y próximos datos necesarios; no recibe un resultado industrial por defecto.

La revisión de Astra por hito comprueba contratos, fórmula, evidencias y resultados; puede devolver tareas correctivas a Sol. Es una revisión técnica, no una nueva solicitud de permiso al usuario para cada cambio. Sol no salta a otra fase para esconder fallos de la anterior. Una decisión nueva de costo, publicación o alcance se consulta sólo si realmente aparece.

## Matriz mínima de pruebas

| ID | Caso de entrada | Resultado exigido |
|---|---|---|
| A01 | Deuda ausente; caja conocida | Deuda y métricas dependientes pendientes; ningún premio por «sin deuda» |
| A02 | Cuatro registros trimestrales con un trimestre ausente y otro duplicado | No se construye TTM; detallar hueco y duplicado |
| A03 | FY=120, YTD actual=100, YTD comparable anterior=80 | TTM=140, con tres inputs y períodos compatibles |
| A04 | Importe original 1.234 expresado en miles de CLP | Canónico 1.234.000 CLP; no inferir escala a partir de magnitud |
| A05 | Precio CLP1.800, EPS USD0,10, FX900 CLP/USD, misma base accionaria | EPS comparable CLP90; PER20; conservar EPS original, tipo y fecha |
| A06 | EPS comparativo ya reexpresado de 2 tras split 2:1 | Sigue 2 en esa misma base; no se transforma nuevamente en 1 |
| A07 | Valor100, precio80, descuento requerido20% | Descuento20%, upside25%, entrada80 en API, interfaz, screener y exportación |
| A08 | FCFF externo fijo; reverse intenta variar crecimiento que no usa el modelo | `unidentifiable`; no devuelve límite inferior como crecimiento implícito |
| A09 | Cambiar driver de crecimiento de un FCFF dentro de dominio válido | Cambian flujos y valoración; reverse recupera el parámetro del precio sintético dentro de tolerancia |
| A10 | Serie anual100,100,100,−200,−300 | Conserva pérdidas; no usa sólo años positivos como «últimos tres años» |
| A11 | EPS/ventas esperados caen20%; no existe consenso | Mantiene caída en escenario propio; ninguna etiqueta de consenso inventada |
| A12 | Sólo un margen anual disponible | Nivel disponible, estabilidad pendiente; no máxima puntuación por estabilidad |
| A13 | Valoraciones100/150/200 sin probabilidades | Tres escenarios; valor ponderado pendiente hasta probabilidades válidas |
| A14 | Puntuación2/2 con98 puntos pendientes | No se convierte en100/100 ni obtiene elegibilidad de ranking |
| A15 | SEC entrega429 o Yahoo falla con copia anterior válida | Trabajo reintentable con backoff; expediente disponible y dato antiguo identificado |
| A16 | Leer evaluación guardada varias veces | No cambia snapshot, fecha económica ni valor; ningún acceso de red implícito |
| A17 | Cambiar de empresa A a B durante guardado y recibir respuesta A después | Nota A permanece en A; pantalla B y su estado de carga no son sobrescritos |
| A18 | Cambiar escenario mientras llega simulación anterior | Sólo se presenta la revisión activa; todos los resultados dependientes se actualizan juntos |
| A19 | Rendimiento USD acumulado10%, FX pasa900→990 CLP/USD | Rendimiento CLP21% para ese horizonte sin flujos intermedios |
| A20 | Importar dos veces misma compra o dividendo | Un evento económico; segunda importación identifica duplicado |
| A21 | Backup con notas, alertas, revisiones, ledger y crudos | Restauración reproduce hashes, saldos y una evaluación sin red |
| A22 | Banco sin capital regulatorio o REIT sin conciliación AFFO | Datos consultables; modelo dependiente bloqueado con requisitos concretos |
| A23 | Snapshot previo a publicación de un estado posterior | Excluye ese estado en modo histórico; captura reciente no altera fecha de disponibilidad |
| A24 | Precio de otra plaza o EPS de otra clase/ADR sin relación documentada | Bloquea comparación; no une por similitud del ticker |

Los ejemplos son sintéticos. Los casos numéricos sencillos se calculan a mano; los modelos complejos se comparan con un cálculo independiente y entradas congeladas, no con el mismo motor invocado dos veces. Además de ejemplos, comprobar invariantes: escala monetaria común no altera ratios; split coherente conserva valor económico; orden de llegada no cambia selección; replay conserva hash del resultado.

## Fixtures y evidencia

Piloto: MSFT, NFLX, FICO, NVO, JPM, VICI, COPEC.SN, CENCOSUD.SN, CHILE.SN y QUINENCO.SN. Son casos de ingeniería, no una selección de compra. Se comienza por MSFT y COPEC; el resto amplía cobertura de errores y modelos. Un símbolo de Yahoo no basta para confirmar identidad: guardar emisor, plaza, clase y relación ADR cuando corresponda.

Cada fixture real necesita URL/documento, fecha de publicación, captura, hash, moneda/unidad, período, observaciones verificadas y restricciones de distribución. Guardar localmente documentos completos cuando corresponda; el repositorio sólo incorpora muestras cuya redistribución permita la fuente y fixtures sintéticos. Los tests normales no descargan datos. Los smoke tests de proveedores se ejecutan aparte y registran fecha/resultado; un fallo de red no modifica expectativas financieras.

Separar tres clases de diferencias contra v1: **error corregido**, **dato/fuente actualizada**, **método cambiado**. Toda diferencia material tiene explicación y ejemplo. El objetivo no es paridad numérica con un defecto documentado.

## Calidad de entrega y carga

M0 fija versiones exactas de Python, librerías, Node de construcción y SQLite, junto con archivos de bloqueo y un único procedimiento local. La CI ejecuta contratos, motores, persistencia y compilación; unos pocos E2E cubren A17/A18, errores, exportación y restauración. No construir una suite extensa de tests que sólo reproduzca detalles de componentes.

Objetivos iniciales de desempeño a medir en el equipo local, con 10 expedientes y 10 años de hechos: lectura de expediente almacenado p95≤1s, navegación con datos locales≤2s, API de encolado≤500ms. Son criterios de aceptación internos medidos sobre varias ejecuciones con condiciones registradas, no garantías sobre proveedores. Una actualización remota presenta progreso por recurso inmediatamente y no bloquea navegación o guardado de notas.

No emitir aviso de éxito si el frontend no compiló, los contratos divergieron o una sección falló silenciosamente. Revisar teclado, foco, contraste y ancho móvil; cada cifra crítica abre su evidencia en un máximo de dos interacciones.

## Migración de datos personales y reversión

1. Inventariar y exportar backend y almacenamiento del navegador del origen realmente utilizado. Cambiar de `file://` a localhost puede crear otro almacén: no asumir que las notas están en el origen abierto más reciente.
2. Previsualizar importación: cantidades, monedas, duplicados, campos sin correspondencia y errores. No aplicar datos ambiguos sin resolución visible.
3. Ensayar sobre copia en un directorio separado. Comparar notas completas, operaciones, cantidades por instrumento, caja por moneda, escenarios y alertas. No importar una valoración v1 como una evaluación v2 verificada: conservarla como referencia con versión de origen.
4. Antes del corte final, crear un nuevo respaldo consistente y detener escrituras en el legado. Importar cambios posteriores al ensayo una sola vez con manifest/idempotencia.
5. Elegir v2 como aplicación principal cuando pase la reconciliación. Las rutas antiguas redirigen a identidad resuelta; las desconocidas muestran búsqueda, no otra empresa aproximada.
6. Si es necesario volver, detener v2 y restaurar la copia legada previa en su directorio original. Conservar íntegra la DB v2 y exportar las operaciones/notas nuevas para conciliación; la reversión nunca implica borrar actividad posterior. No prometer una migración inversa automática hacia un esquema que no representa revisiones nuevas.

La retirada de archivos antiguos sólo ocurre después de comprobar que no hay consumidores activos y que las alternativas pasan aceptación. El historial Git y el respaldo permanecen disponibles; no mantener dos motores de valoración activos indefinidamente.
