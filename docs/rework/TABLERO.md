# Tablero del rework

El estado vigente está en las incidencias de GitHub. Esta página reúne filtros e hitos; no es un proyecto nativo de GitHub Projects.

## Estados en vivo

| Pendiente | En curso | En revisión | Bloqueado | Terminado |
|---|---|---|---|---|
| [Ver tareas](https://github.com/Pacortes2021/Inversor_Inteligente/issues?q=is%3Aissue%20is%3Aopen%20label%3Arework%20label%3Astatus%3Atodo) | [Ver tareas](https://github.com/Pacortes2021/Inversor_Inteligente/issues?q=is%3Aissue%20is%3Aopen%20label%3Arework%20label%3Astatus%3Ain-progress) | [Ver tareas](https://github.com/Pacortes2021/Inversor_Inteligente/issues?q=is%3Aissue%20is%3Aopen%20label%3Arework%20label%3Astatus%3Areview) | [Ver tareas](https://github.com/Pacortes2021/Inversor_Inteligente/issues?q=is%3Aissue%20is%3Aopen%20label%3Arework%20label%3Astatus%3Ablocked) | [Ver tareas](https://github.com/Pacortes2021/Inversor_Inteligente/issues?q=is%3Aissue%20is%3Aclosed%20label%3Arework) |

## Hitos

| Hito | Seguimiento |
|---|---|
| M0 · Referencia y contratos | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/1) |
| M1 · Núcleo de datos | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/2) |
| M2 · Datos de EE.UU. | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/3) |
| M3 · Chile y monedas | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/4) |
| M4 · Motores financieros | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/5) |
| M5 · Expediente completo | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/6) |
| M6 · Modelos sectoriales | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/7) |
| M7 · Comparación y cartera | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/8) |
| M8 · Migración y cierre | [Abrir hito](https://github.com/Pacortes2021/Inversor_Inteligente/milestone/9) |

## Primera cola de trabajo

| Tarea | Incidencia | Dependencias |
|---|---|---|
| R00 | [Congelar referencia e inventariar el entorno sin modificar la app actual](https://github.com/Pacortes2021/Inversor_Inteligente/issues/2) | — |
| R01 | [Reproducir fallos prioritarios y definir fixtures A01–A14](https://github.com/Pacortes2021/Inversor_Inteligente/issues/3) | [R00](https://github.com/Pacortes2021/Inversor_Inteligente/issues/2) |
| R02 | [Implementar y validar los contratos canónicos iniciales](https://github.com/Pacortes2021/Inversor_Inteligente/issues/4) | [R01](https://github.com/Pacortes2021/Inversor_Inteligente/issues/3) |
| R03 | [Fijar entorno reproducible, CI y esqueletos de backend/frontend](https://github.com/Pacortes2021/Inversor_Inteligente/issues/5) | [R00](https://github.com/Pacortes2021/Inversor_Inteligente/issues/2), [R02](https://github.com/Pacortes2021/Inversor_Inteligente/issues/4) |
| R04 | [Persistir identidad de emisores, instrumentos, plazas y ADR](https://github.com/Pacortes2021/Inversor_Inteligente/issues/6) | [R02](https://github.com/Pacortes2021/Inversor_Inteligente/issues/4), [R03](https://github.com/Pacortes2021/Inversor_Inteligente/issues/5) |
| R05 | [Guardar documentos originales, observaciones y linaje](https://github.com/Pacortes2021/Inversor_Inteligente/issues/7) | [R04](https://github.com/Pacortes2021/Inversor_Inteligente/issues/6) |
| R06 | [Seleccionar y conciliar hechos por contexto y fecha disponible](https://github.com/Pacortes2021/Inversor_Inteligente/issues/8) | [R05](https://github.com/Pacortes2021/Inversor_Inteligente/issues/7) |
| R07 | [Crear snapshots inmutables y API de evidencia](https://github.com/Pacortes2021/Inversor_Inteligente/issues/9) | [R06](https://github.com/Pacortes2021/Inversor_Inteligente/issues/8) |
| R08 | [Implementar trabajos persistentes, caché y recuperación](https://github.com/Pacortes2021/Inversor_Inteligente/issues/10) | [R05](https://github.com/Pacortes2021/Inversor_Inteligente/issues/7) |

M0 comienza con R00–R03. M1 queda preparado; M2–M8 se detallan en incidencias al acercarse a esas etapas. El [backlog completo](07-backlog-sol.md) conserva las 45 tareas.

La implementación usa una rama propia y una PR hacia `codex/rework-core`. Revisar [coordinación y modelos](10-coordinacion-github.md) para estados, responsabilidades y criterios de cierre.
