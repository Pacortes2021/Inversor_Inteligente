# Rework de El Inversor Inteligente

Diseño preparado el 13 de septiembre de 2026. Base auditada: `codex/data-confiable`, commit `5d36ea301b0abee5e58d2aa750bb7d6e996d5ee3`. Estado: especificación para implementación, no nueva aplicación construida. Restricciones confirmadas por Pablo: **uso personal, US$0 mensuales inicialmente, acciones de EE.UU. en USD y acciones chilenas en CLP**.

## Seguimiento de la implementación

[Tablero y tareas de GitHub](TABLERO.md) · [Coordinación y selección de modelos](10-coordinacion-github.md). El diseño permanece como referencia; los estados de implementación se consultan en las incidencias.

## Decisión principal

Construir una aplicación local de investigación fundamental con una cadena verificable desde el reporte hasta la decisión. Mantener Python/FastAPI, introducir contratos tipados y SQLite, reemplazar gradualmente la interfaz por componentes React/TypeScript y hacer que todas las pantallas consuman el mismo análisis versionado. La interfaz no calculará una segunda valoración.

La unidad central será un **expediente de inversión**: empresa e instrumento identificados, datos con período y evidencia, normalización explícita, escenarios editables, valoración apropiada, comparación con alternativas y tesis con seguimiento. La nota de 100 puntos será un resumen orientativo; nunca reemplazará los requisitos mínimos del análisis.

El objetivo inicial es profundidad sobre 10 instrumentos representativos. Ampliar después a una lista personal y luego al universo completo. Precios de cierre son suficientes para este objetivo; no se necesita infraestructura de trading en tiempo real.

## Qué cambia respecto de las conclusiones del chat

La versión actual contiene mejoras útiles, pero **84 pruebas aprobadas no prueban exactitud financiera integral**. La auditoría encontró un reverse DCF insensible al crecimiento cuando recibe flujos forward, una mezcla de flujos y tasas de descuento, proyecciones sobreescritas en JavaScript y etiquetas de fuente que exageran la verificación. Estos componentes se conservan como referencia de comportamiento, no como verdad contra la que deba coincidir el rework. Ver las reproducciones y referencias en [auditoría](01-auditoria.md).

No es suficiente sustituir Yahoo por otro proveedor. Hay que corregir identidad, períodos, moneda, ajustes accionarios, procedencia y métodos; de lo contrario, un proveedor mejor alimentará cálculos inconsistentes.

## Documentos y orden de lectura

| Documento | Entrega | Quién lo usa |
|---|---|---|
| [01 · Auditoría](01-auditoria.md) | Defectos verificables, responsabilidades y decisiones conservar/reemplazar | Astra y revisión |
| [02 · Producto y UX](02-producto-y-ux.md) | Flujo, pantallas, estados, definición de análisis completo | Diseño e implementación |
| [03 · Arquitectura y contratos](03-arquitectura-y-contratos.md) | Módulos, almacenamiento, entidades, API y reglas de estado | Sol/backend/frontend |
| [04 · Proveedores y calidad](04-proveedores-y-calidad.md) | Base gratuita, cobertura, límites, evaluación y fuentes consultadas | Integración de datos |
| [05 · Motores financieros](05-motores-financieros.md) | Fórmulas, supuestos, aplicabilidad y criterios por modelo | Implementación y validación financiera |
| [06 · Migración y validación](06-migracion-y-validacion.md) | Hitos, pruebas, comparación, reversión y aceptación | Coordinación del rework |
| [07 · Backlog ejecutable](07-backlog-sol.md) | Tareas pequeñas con dependencias, archivos y resultados verificables | Sol |
| [08 · Instrucciones para Sol](08-instrucciones-sol.md) | Prompt de inicio y protocolo de entrega/revisión por hito | Nueva tarea de implementación |
| [09 · Política de evaluación](09-politica-de-evaluacion.md) | Criterios, pesos, umbrales propuestos, cobertura y bloqueos | Revisión financiera y scoring |
| [Contratos de ejemplo](contracts/) | Esquemas JSON y ejemplos sintéticos que fijan semántica | Contratos y fixtures |
| [Comprobación de la entrega](VALIDACION.md) | Qué se verificó y qué pertenece todavía a implementación | Revisión de alcance |

## Primer resultado utilizable

Una ficha nueva para MSFT y COPEC que pueda mostrar un estado financiero verificable, explicar cualquier falta de datos y permitir una valoración reproducible donde los supuestos sí alteren los resultados. COPEC debe tener un expediente contable chileno real, no quedar vacía porque carezca de historia SEC. Si todavía falta una variable necesaria, la ficha debe permitir añadirla con evidencia y mantener bloqueado únicamente el cálculo dependiente.

## Decisiones fijadas

- Monolito modular local. Sin microservicios, Kubernetes, Redis ni servicios de nube obligatorios.
- Un usuario; acceso loopback como configuración inicial. Preservar respaldo y portabilidad.
- Datos originales inmutables; transformaciones registradas; el faltante nunca se convierte en cero.
- Un motor backend para ficha, screener, comparador y exportación.
- Fuentes gratuitas oficiales para reportes; consulta/importación de documentos como camino válido cuando no exista API utilizable.
- Los precios Yahoo pueden continuar como fuente secundaria identificada. Su fallo no debe derribar el expediente completo.
- Los 6 pesos del método se mantienen como preferencia del producto. Los umbrales concretos se versionan y se someten a revisión.
- Se mantienen USD y CLP en las fichas. Comparaciones entre monedas requieren una conversión explícita y fechada; no se suman CLP con USD.

## Decisiones condicionadas a evidencia

El acceso automatizado a los estados CMF debe probarse antes de prometer cobertura masiva. AFFO, capital regulatorio, concentración y capex de mantenimiento pueden empezar con extracción/importación revisada. Consenso de analistas no es requisito para una valoración propia. No se seleccionará ni contratará una API de pago en el alcance inicial.

React/TypeScript y SQLite son decisiones propuestas para la implementación; sus versiones exactas se fijan al crear el entorno reproducible. El catálogo de instrumentos, el período de cobertura y los parsers CMF se amplían sólo después de superar los fixtures del piloto.

## Orden de trabajo

1. Congelar y documentar la referencia; reproducir fallas y fijar contratos.
2. Construir identidad, hechos, almacenamiento y trabajos de actualización.
3. Integrar SEC, CMF y FX mediante el mismo contrato; conciliar muestras.
4. Implementar motores deterministas y escenarios, empezando por FCFF/reverse.
5. Entregar el primer flujo completo con interfaz, expediente cualitativo y revisión de tesis.
6. Incorporar modelos sectoriales, ranking, portafolio, seguimiento y migración final.

Cada hito termina con artefactos revisables y pruebas de aceptación. Astra revisa cuestiones financieras y contratos; Sol implementa tareas delimitadas. No es necesario crear una nueva tarea por cada archivo.

## Alcance de esta entrega

Se auditó código y se verificaron documentos públicos de proveedores. Se volvió a ejecutar la suite local: 84 pruebas aprobadas. Se ejecutaron reproducciones sintéticas adicionales de defectos. No se adquirieron datos ni se midió todavía cobertura real de una nueva integración CMF. Este paquete no modifica los motores ni el servidor en funcionamiento. La carpeta principal `main` tiene cambios locales previos; no se incluyen ni sobrescriben.
