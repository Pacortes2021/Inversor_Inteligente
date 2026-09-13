# Comprobación de esta entrega de diseño

Fecha: 13 de septiembre de 2026. Alcance: documentos de rework en el worktree `codex/data-confiable`. Esta comprobación no es la aceptación de una app nueva.

| Comprobación | Resultado |
|---|---|
| Referencia de la auditoría | `5d36ea301b0abee5e58d2aa750bb7d6e996d5ee3` |
| Suite de la aplicación de referencia durante la auditoría | 84 pruebas aprobadas; no cubren todos los defectos reproducidos |
| Hallazgos registrados | 25 con ubicación, consecuencia y destino de corrección |
| Backlog | 45 IDs únicos R00–R44, agrupados M0–M8 |
| Matriz de aceptación | 24 casos A01–A24, con resultado esperado |
| Política de evaluación | 27 criterios; máximos suman 100 y grupos 25/20/15/25/10/5 |
| Documentos JSON | 6 archivos con sintaxis válida; requeridos, propiedades superiores y patrones superiores de ejemplos comprobados |
| Enlaces locales del paquete | Sin destinos faltantes en la comprobación |
| Oráculo FCFF | Calculado por separado con Decimal y ACT/365,25; valor sintético 16,1200790916846 USD/acción |
| Oráculo de retorno | Flujos anuales −100,+5,+126 ⇒ IRR 14,77755786%, comprobada por ecuación cuadrática |
| Casos negativos de contrato | 8 casos definidos con capa y error esperado; deben automatizarse en R02 |
| Integridad del alcance | Sólo documentos añadidos en el worktree; código y cambios locales previos del checkout principal preservados |

Pendientes que pertenecen a la implementación: validación completa Draft2020-12, contratos adicionales de toda la API, pruebas contra el nuevo motor, extracción/conciliación real del piloto CMF, validación de proveedores en vivo y migración de datos personales. No se presentan como aprobados. La falta de JSON Schema en los runtimes inspeccionados no se resolvió instalando dependencias en la aplicación durante un trabajo documental.

El diseño incorpora revisión de arquitectura y finanzas sobre períodos, revisión histórica, concurrencia de SQLite, identidad de plaza, SBC, terminal, monedas y modelos sectoriales. Los umbrales del score siguen siendo una política inicial propuesta, sin validación predictiva. La implementación debe someter fórmulas y contratos a la revisión por hito descrita en06.
