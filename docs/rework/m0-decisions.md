# Decisiones y límites de contrato de M0

Este registro distingue decisiones cerradas de preguntas que deben revisar Astra o hitos posteriores. Los ejemplos son sintéticos y los umbrales de scoring siguen siendo política propuesta, no evidencia predictiva.

## Decisiones cerradas en R02

1. **Decimal y faltante.** Magnitudes financieras cruzan la frontera JSON como strings decimales finitos. `available` exige valor; `missing`, `blocked`, `unsupported` y `not_applicable` exigen `null` y un motivo. No existe coerción de `null` a cero.
2. **Escala.** En una conversión sólo de escala, el canónico debe ser `originalValue × originalScale`. FX, split y normalización son transformaciones distintas con parámetros y referencias tipadas; no se aplica esa igualdad a una transformación compuesta.
3. **Tiempo.** Captura y primera observación son timestamps con zona. Publicación admite timestamp o fecha sin inventar hora y debe declarar precisión compatible. Un hecho reportado disponible no puede cerrar después de su recuperación.
4. **Período.** Instantes no tienen inicio; duraciones tienen inicio y fin ordenados. FQ exige trimestre. No se impone una duración de 365 días a FY históricos.
5. **Evidencia y linaje.** Un objeto de evidencia vacío no es evidencia. Hechos derivados requieren entradas y transformación; el validador de conjunto rechaza referencias ausentes, duplicados, autorreferencia y ciclos.
6. **Identidad.** Emisor, instrumento, listing, símbolo de proveedor y relación ADR son entidades distintas. País, plaza y moneda no se infieren entre sí. Una base accionaria suma componentes incluidos en el denominador y separa reclamaciones para impedir doble conteo.
7. **Snapshot.** Precio y FX referenciados pertenecen a los hechos seleccionados; listing, moneda, políticas, base accionaria y hash forman parte del contrato inmutable.
8. **Assessment.** La modalidad financiera y personal permanece explícita; la personal exige revisión de tesis. Cobertura conserva 100 puntos posibles, puntos pendientes y rango. Dos puntos resueltos no se normalizan a 100/100.
9. **Scenario.** Las probabilidades son opcionales. Si se entregan, deben existir para todos los escenarios y sumar exactamente uno; sin ellas el valor ponderado permanece pendiente.
10. **FCFF request.** M0 valida dominio, fechas móviles consecutivas, `WACC > g`, reinversión terminal no superior a 100%, FX explícito y binding por cada número. No calcula FCFF ni valida el oráculo numérico: esa implementación es R20/M4.
11. **ProviderResult y errores.** Éxito, parcial y fallo no comparten semántica; un fallo no puede reemplazar datos. Rate limit exige espera tipada. La API usa códigos estables, request ID y reintento explícito.

## Oráculos congelados, no implementación adelantada

`tests/v2/fixtures/manifest.json` contiene A01–A14 con entrada, salida esperada, razonamiento y hito de activación. A04 queda demostrado por el contrato de escala. A01–A03 y A05–A13 esperan motores de M3/M4; A14 espera la política de evaluación M5. Las pruebas M0 recalculan sólo identidades algebraicas independientes y verifican que los demás casos sigan rotulados como pendientes.

Las reproducciones del legado viven bajo `tests/v2/characterization/`. Que un test demuestre el reverse insensible o un TTM con hueco sólo congela el defecto observado; no lo convierte en aceptación de v2.

## Puntos para revisión de Astra

- Confirmar que la fecha de publicación como `date` más `timestampPrecision=date` es suficiente para aplicar la regla conservadora de siguiente sesión en M1, sin forzar una hora falsa.
- Confirmar el límite inicial de períodos FCFF consecutivos anclados a `valuationDate`, incluido el aniversario de 29 de febrero. Un stub fiscal sigue fuera del contrato.
- Revisar que componentes de acciones incluidos en denominador frente a reclamaciones expresan la exclusión mutua necesaria; el catálogo cerrado de tipos de opciones/RSU puede definirse con la conciliación de M1.
- Revisar la decisión de exigir que todos los bindings apunten a `evidenceIds` del request. M1 debe resolver además pertenencia a snapshot o revisión y coincidencia de unidad/valor.
- La lista de conceptos de precio estructural inicial sigue limitada a open/high/low/close. Ampliarla requiere igual identidad de listing, sesión, moneda y política de ajuste.
- Los valores de `engineVersions` y `policyVersions` son identificadores en M0. La inmutabilidad y existencia referencial dependen del almacenamiento de M1.
- El runtime Python bloqueado enlaza SQLite 3.50.4 y queda por debajo de la corrección WAL-reset de 3.53.0. No hay persistencia ni WAL activos en M0. Astra debe tratar la actualización de SQLite como puerta previa del adaptador M1, no aceptar un booleano de health como mitigación.
