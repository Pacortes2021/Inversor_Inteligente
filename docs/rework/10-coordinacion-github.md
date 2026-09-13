# Coordinación, modelos y entregas en GitHub

El usuario autorizó el 13 de septiembre de 2026 organizar el repositorio, iniciar M0 con Sol y ajustar modelo/esfuerzo según las tareas. El cambio de modelo se aplica a los encargos de implementación/revisión; no supone que un agente pueda cambiar el modelo de su propio turno ya en ejecución.

## Fuente de verdad

Los documentos de `docs/rework/` definen alcance y criterios. Las incidencias de GitHub registran trabajo y estado; las pull requests contienen código y evidencia de validación. El chat sirve para coordinar y resolver decisiones. Un acuerdo material del chat se incorpora a los documentos/incidencia antes de depender de él.

La implementación empieza con R00–R03 (M0). R04–R08 están preparados para M1; no se activan hasta aceptar M0. M2–M8 tienen hitos y backlog, y sus incidencias detalladas se crean al aproximarse a esa fase.

## Ramas y referencia

- `main`: rama publicada existente, preservada mientras se revisan cambios.
- `codex/data-confiable`: referencia funcional auditada; su PR anterior permanece independiente.
- `codex/rework-plan`: propuesta sólo de documentación sobre la rama remota main.
- `codex/rework-core`: integración del rework desde la referencia auditada y el paquete de diseño. No es una declaración de que los defectos del legado estén resueltos.
- Rama de implementación por entrega, por ejemplo `codex/rework-m0`, basada en la integración verificada. PR dirigida a `codex/rework-core`, sin arrastrar diferencias del legado hacia main.

La creación de una nueva copia de trabajo no incluye automáticamente documentos sin commit. Verificar que el paquete existe en el HEAD elegido antes de empezar. No publicar contenido de `.env`, cachés, portafolios, notas personales o respaldos. Los informes públicos usan rutas relativas e inventarios de categorías; datos sensibles permanecen en respaldo local.

No fusionar automáticamente la propuesta anterior ni el rework entero a main por completar una tarea. La revisión técnica acepta PRs pequeñas con pruebas. La sustitución de la app usada por Pablo pertenece al corte de M8 y conserva reversión.

## Selección del modelo

| Trabajo | Selección inicial | Cuándo ajustar |
|---|---|---|
| M0, contratos e implementación general | Sol, esfuerzo alto | Subir una tarea a Astra si hay ambigüedad material, diseño incompatible o fallos difíciles de localizar |
| Revisión de arquitectura, fórmulas, modelos sectoriales y migración | Astra, esfuerzo alto | Usar max si la revisión requiere razonamiento especialmente complejo; documentar la pregunta y resultado |
| Componentes y cambios acotados con contrato cerrado | Terra, esfuerzo medio o alto | Comprobar calidad de una entrega representativa antes de ampliar uso |
| Documentación o presentación repetitiva y claramente definida | Luna, esfuerzo medio | No asignar una nueva fórmula financiera sólo por parecer pocas líneas |

La coordinación puede ajustar estas elecciones sin volver a consultar cada vez al usuario. Se cambia por el trabajo necesario y evidencia de calidad; no se promete un ahorro fijo de cuota por elegir otro modelo. La revisión no consiste en aceptar el resumen del implementador: debe inspeccionar código, contratos y casos independientes.

## Estados y reglas

Una incidencia abierta tiene una sola etiqueta `status:todo`, `status:in-progress`, `status:review` o `status:blocked`. Cerrar implica aceptación demostrada; no basta que el implementador haya terminado de escribir código. Al cerrar, retirar etiquetas de trabajo activo. Un bloqueo tiene causa, acción necesaria y tareas independientes que pueden continuar.

Un PR referencia las incidencias, describe el problema y comportamiento final, y registra pruebas ejecutadas y límites. Usar `Refs #N` mientras la revisión está pendiente; no cerrar anticipadamente mediante palabras automáticas de cierre. El estado del PR no sustituye la aceptación de los criterios de cada incidencia.

El acceso actual permite incidencias, hitos y ramas; GitHub Projects requiere un scope adicional no disponible. [TABLERO.md](TABLERO.md) enlaza filtros vivos e hitos del repositorio sin ampliar permisos. No se presenta como un proyecto nativo de GitHub Projects ya creado.

## Primera entrega esperada

M0 entrega inventario no sensible, fixtures de defectos, contratos canónicos validados, entorno reproducible, CI y esqueletos compilables. No habilita un DCF nuevo ni cambia la interfaz de producción. Al terminar: PR, informe por R00–R03, pruebas, limitaciones y puntos de revisión para Astra. La coordinación revisa y pide correcciones concretas antes de abrir M1.
