# Instrucciones para comenzar la implementación

Copiar el siguiente encargo en una tarea de implementación. No significa que esa tarea ya se haya creado ni que el rework esté construido. El primer encargo es M0; después se avanza por las puertas de aceptación de06 y los IDs de07.

---

Trabaja en el rework de Inversor Inteligente para uso personal, con US$0 mensuales de datos inicialmente. El objetivo es una herramienta de investigación fundamental: entender negocio y calidad, verificar datos, normalizar, valorar por escenarios y reverse DCF, contrastar con VT/VOO y documentar decisiones y seguimiento. Las acciones de EE.UU. se muestran en USD y las chilenas en CLP. No añadas una conversión global implícita.

La referencia auditada es el commit `5d36ea301b0abee5e58d2aa750bb7d6e996d5ee3` de `codex/data-confiable`. El paquete versionado de diseño está en `docs/rework/`. La coordinación prepara `codex/rework-core` con esa base y este diseño; confirma su HEAD y usa una rama de implementación propia en un worktree aislado. No sobrescribas la rama de integración. Si la tarea se abre inicialmente desde otra referencia, cambia de rama dentro de su worktree antes de editar y verifica que los archivos del diseño están presentes. Conserva los cambios previos del checkout principal y el servidor que usa Pablo. No hagas reset/clean. Si la referencia ha avanzado, registra la diferencia antes de elegir base; no ignores trabajo nuevo.

Lee README y los documentos01–09, con especial atención a03,05,06,07 y `contracts/README.md`. La auditoría identifica errores que no deben copiarse aunque las 84 pruebas anteriores pasen.

**Implementa M0: R00–R03 del backlog.** Entrega entorno reproducible, inventario y resguardo de referencia, fixtures de fallos prioritarios y contratos tipados validados. El frontend puede tener su estructura compilable; todavía no rediseñes todas las pantallas ni actives modelos financieros incompletos. Al terminar, prepara evidencia para revisión del hito. Los siguientes hitos se ejecutan en su orden con revisión de los contratos y las fórmulas afectadas; las correcciones de esa revisión forman parte del trabajo.

Restricciones técnicas y financieras:

- Monolito modular Python/FastAPI, SQLite local, worker administrado por la app, React/TypeScript con Vite. No servicios de nube ni infraestructura adicional obligatoria.
- `domain` y `engines` son puros. Sólo los adaptadores acceden a proveedores y almacenamiento. `AssessmentService` es la autoridad única de cálculo para ficha, screener, comparador, cartera y exportaciones.
- Hechos con identidad, período, unidad, moneda, origen, publicación, captura y evidencia. Mantén los originales y las revisiones; no sustituyas datos faltantes por cero o por proyecciones ocultas.
- SEC es fuente de reportes, no un permiso para etiquetar todo el payload como SEC. CMF bancaria no equivale a API de estados de todas las empresas chilenas. Prueba la cobertura; la importación revisada de documentos oficiales es un camino válido con presupuesto cero.
- Precios Yahoo pueden usarse con identificación y límites visibles. No contratar APIs ni exigir consenso de pago para completar una valoración propia.
- No inventes tasa, deuda, acciones, ROE, payout ni capex de mantenimiento. Un supuesto introducido expresamente tiene revisión y fundamento; nunca se presenta como dato reportado.
- Separar FCFF/WACC, flujos de accionista/ke, valor presente/precio de salida y descuento/upside. Implementa las fechas y dominios definidos en los contratos. El reverse debe resolver una variable activa, con residual y detección de indeterminación.
- El frontend captura inputs y muestra outputs. No replica DCF, retorno, score o precio objetivo en JavaScript.
- La matriz mantiene pesos 25/20/15/25/10/5 y política versionada. Faltantes, conflictos o modelo inaplicable bloquean las conclusiones dependientes aun con puntuación alta. No redistribuyas puntos personales ni normalices una cobertura mínima a 100.
- Base de datos de desarrollo separada. Notas, alertas, escenarios y operaciones deben poder respaldarse/restaurarse; no compartas escrituras con el legado.

Trabaja en cambios pequeños revisables. No delegues ediciones simultáneas sobre los mismos archivos. Ejecuta las pruebas apropiadas y registra el resultado exacto; diferencia fixture sintético, conciliación documental y prueba de proveedor en vivo. No amplíes pruebas por inercia una vez satisfechos los criterios de la tarea. No declares un hito terminado por tener archivos creados o por pasar sólo pruebas anteriores.

Si aparece una ambigüedad rutinaria, resuélvela con los contratos y documenta la decisión. Si cambia la semántica financiera, presenta fórmula, inputs y ejemplo independiente para revisión antes de activar el resultado. No uses incertidumbre de diseño como motivo para pedir permiso por cada edición autorizada. No compres servicios, despliegues la app ni conectes un broker como parte del rework. Publicar ramas, pull requests y actualizaciones de las incidencias del rework en este repositorio está autorizado; no publiques datos personales ni credenciales.

Al finalizar M0 informa: tareas completadas, ubicación del worktree, archivos/commits, pruebas y limitaciones, decisiones cerradas y evidencia para revisar. Incluye el siguiente ID habilitado. No prometas que la app ya es fiable para todas las empresas: indica el alcance efectivamente demostrado.

---

## Revisión de Astra por hito

Revisar el diff y la evidencia, no sólo el informe de Sol. Comprobar que una mejora de cobertura no ha cambiado unidad, contexto, definición o revisión; que las fórmulas no mezclan flujos/tasas; y que la misma evaluación llega intacta a todas las vistas. Para datos personales, verificar persistencia y reversión. Registrar hallazgos con prioridad, caso reproducible y criterio de corrección.

Un hito se acepta cuando no quedan defectos materiales sobre su alcance y las pruebas de06 correspondientes están demostradas. Ajustes menores de presentación pueden quedar con tarea explícita. Esta revisión no implica que deba consultarse a Pablo cada detalle técnico; se consulta sólo una decisión que requiera su preferencia o una autorización nueva.
