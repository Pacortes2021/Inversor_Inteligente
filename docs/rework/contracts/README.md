# Contratos iniciales y ejemplos

Los esquemas curados describen la frontera documental original y los modelos de `backend/v2/domain/` ejecutan las reglas cruzadas. JSON Schema Draft 2020-12 valida estructura; los validadores del dominio comprueban períodos, referencias, linaje, escalas y estados. M0 no activa por ello ningún motor financiero.

| Archivo | Uso |
|---|---|
| `fact.schema.json` | Magnitud canónica y procedencia por observación |
| `fact.example.json` | Ingresos ficticios: 1.000 miles de USD ⇒ 1.000.000 USD |
| `fcff-request.schema.json` | Solicitud de simulación por drivers, fechas, revisiones y evidencias |
| `fcff-request.example.json` | Empresa sintética, sin vínculo con cotizaciones reales |
| `fcff-expected.example.json` | Cálculo independiente para comprobar el futuro motor |
| `invalid-cases.json` | Parches sobre los ejemplos y capa que debe rechazarlos |
| `generated/*.schema.json` | Esquemas regenerables de Fact, identidad, Snapshot, Assessment, Scenario, ProviderResult, captura SEC, ShareBasis y errores |
| `openapi.json` | OpenAPI 3.1 del esqueleto, con todos los contratos canónicos en componentes |

Regeneración: `uv run python scripts/export_v2_schemas.py`. La CI exige que el resultado no cambie y ejecuta validación Draft 2020-12 con comprobación de formatos.

Los identificadores `synthetic-*`, documentos de ejemplo y hashes artificiales no verifican ninguna empresa real. Una validación estructural no convierte un ejemplo en dato financiero confiable.

## Fact: validación semántica requerida

- `value` es string decimal canónico; cero es válido. Un faltante/bloqueado tiene valor null y motivo. Un valor monetario disponible exige moneda conocida; un faltante puede conservar moneda null si se desconoce, sin asignarla por país.
- En una conversión sólo de escala, `value = originalValue × originalScale`. Otros cambios de unidad/FX/base requieren transformación y linaje propios; no forzar esta igualdad después de una conversión compuesta.
- Período instantáneo: start null y label instant. Duración: start/end presentes y start≤end, etiqueta compatible. El calendario fiscal puede tener 52/53 semanas; no exigir 365 días para todo FY histórico.
- Concepto y contexto fijan unidad, consolidación, moneda y denominador. EPS, saldos, flujos y precios no comparten automáticamente período/base.
- Precios disponibles identifican instrumento y listing; la moneda/sesión corresponde a esa plaza. La lista estructural inicial cubre open/high/low/close; cualquier precio adicional se incorpora al catálogo semántico con iguales requisitos.
- `firstSeenAt≤retrievedAt`; publishedAt puede ser anterior por filing histórico verificado. Si sólo se conoce fecha, no inventar precisión horaria; conservar `timestampPrecision=date` y usar disponibilidad conservadora en histórico. Origen estimate puede tener período futuro, origen reported no puede representar como realizado un período futuro.
- Evidencia: al menos un documento/payload accesible con hash/ubicación o referencia verificable. Un objeto con todos sus campos null no prueba procedencia aunque pase una parte del esquema. URLs se tratan como datos, nunca como instrucciones o rutas arbitrarias del servidor.
- Todo input derivado existe y tiene linaje acíclico. Una transformación de escala, split, FX o normalización declara versión y parámetros; ampliar el contrato de transformación en R02 con esos parámetros tipados y referencias, sin almacenar fórmulas opacas como texto ejecutable.
- Base ajustada conserva fecha y factor objetivo, acciones previas/nuevas y evento. `shareBasis=split_adjusted` por sí solo no autoriza otro ajuste. R02 debe completar `ShareBasis` como entidad vinculada; estos enums iniciales fijan estado, no contienen todavía toda la relación.

## FCFF: dominio de la primera solicitud

`asOf` es el instante de corte de información del snapshot; `valuationDate` es la fecha desde la que se descuentan flujos. En el modo inicial la fecha UTC de asOf coincide con valuationDate y sólo se aceptan hechos elegibles en ese corte. En uso histórico se requiere publicación verificable; para uso actual se incorpora el último reporte disponible con su antigüedad, sin convertirlo en reporte del día.

`currency` es moneda del modelo; `quoteCurrency` moneda de la plaza. Si difieren, `fxFactId` debe identificar la tasa y sentido de conversión en la fecha de valoración, con política para día sin publicación. El resultado nativo del motor conserva currency y el resultado por listing identifica la transformación a quoteCurrency. Estados históricos nunca se reescriben con ese FX actual.

`inputBindings` relaciona cada importe/tasa con IDs de hechos o supuestos de revisión, mediante JSON Pointer, por ejemplo `/years/0/revenueGrowth`. Todos los campos numéricos requieren vínculo, incluidos ceros del puente. Verificar que las referencias existen, pertenecen al snapshot o revisión declarados, y que unidades/valores coinciden. Una lista general `evidenceIds` no es suficiente para atribuir cada cifra.

`shares>0`, `baseRevenue>0`; decimal finito. `sharesBasis` requiere una conciliación de capital a la fecha de valoración: acciones vigentes, relación de clase/ADR y tratamiento de reclamaciones existentes. El snapshot debe vincular esa conciliación. Prohibir que una misma RSU/opción esté incluida en shares y restada en otherClaims. Denominadores de EPS y acciones al cierre son conceptos distintos. Si el dato crítico es desconocido, la API entrega estado bloqueado; no construye una solicitud con cero.

`forecastConvention=consecutive_12_month_periods`: primer inicio al día siguiente de valuationDate; fin en el aniversario de valoración siguiente; cada inicio posterior al fin anterior, sin huecos ni solapamiento. Definir aniversario de 29 de febrero como 28 de febrero en año no bisiesto. Los períodos pueden ser móviles y no coincidir con ejercicios fiscales. `baseRevenue` representa una base anual normalizada con período/evidencia y puente al inicio: nunca el ingreso de un trimestre tomado como año. Proyecciones móviles se llaman escenarios propios, no consenso FY. Un stub fiscal inicial o un período de 53 semanas proyectado necesita contrato específico antes de habilitarlo; no se comprime ni anualiza silenciosamente.

Cada `revenueGrowth` se aplica a los ingresos del período anual anterior. Los años móviles contienen sólo flujos futuros; el TTM histórico sirve de base, no se suma como flujo futuro. `cashFlowAt=forecastEnd`. Exponente de descuento `(cashFlowAt−valuationDate).days/365.25`; no usar índice de fila como tiempo.

Impuesto operativo inicial: `max(EBIT,0)×taxRate`. No crédito tributario inmediato por pérdidas ni arrastre de pérdidas incorporado por defecto. D&A no incluye SBC ni todos los ajustes del estado de caja. Crecimiento adquirido queda fuera del contrato inicial. El puente hacia el terminal requiere evidencia de transición de márgenes/reinversión; no puede ser una discontinuidad sin supuesto.

Terminal: `0≤g`, `WACC>g`, `ROIC>0`, `g/ROIC≤1`, NOPAT_terminal>0. El esquema limita algunas tasas por dominio técnico; esos límites no son una recomendación de tasa. Un input fuera del dominio requiere otra especificación o corrección, no recorte automático al máximo permitido.

No se ha definido aquí un modelo de fluctuación futura del número de acciones: las reclamaciones existentes se reconcilian a la fecha de valoración y el costo de concesiones futuras permanece como gasto SBC en EBIT. Si el escenario requiere financiación, recompra o dilución futura explícita material, ampliar el contrato con puente de capital, evitando castigar dos veces SBC; no activar esa casilla sobre este motor sin revisión.

## Oráculo numérico de FCFF

Entrada sintética: valoración31-12-2025, ingresos base1.000, crecimiento5% durante3 años, margen20%, impuesto25%, D&A30, capex50, ΔNWC10, WACC10%, g2,5%, ROIC terminal12,5%, acciones100, caja excedente50 y deuda200. Todos los otros reclamos son cero por definición del ejemplo, no por falta de información.

| Período | Ingresos | FCFF | Días desde valoración |
|---|---:|---:|---:|
| 2026 | 1.050 | 127,5 | 365 |
| 2027 | 1.102,5 | 135,375 | 730 |
| 2028 | 1.157,625 | 143,64375 | 1.096 |

Reinversión terminal20%; NOPAT terminal177,98484375; FCFF terminal142,387875; terminal al cierre2028=1.898,505. Con descuento ACT/365,25: EV≈1.762,00790916846; equity≈1.612,00790916846; valor por acción≈**16,1200790916846 USD**. Usar tolerancia absoluta1e−8 para este fixture de escala pequeña. No mostrar tantos decimales en producto.

El oráculo fue calculado separadamente con aritmética decimal a partir de las fórmulas del documento05. Todavía no demuestra que un motor de la app implemente esas fórmulas. En R20 comprobar además sensibilidad, signos, bloqueos y unidades; un único ejemplo correcto no cubre el modelo.

## Casos negativos y estado de comprobación

`invalid-cases.json` indica reemplazos por JSON Pointer sobre el ejemplo correspondiente. Casos `json_schema` deben fallar antes de dominio; casos `semantic` pueden ser estructuralmente válidos y deben fallar al resolver/validar contexto. R02 implementa los códigos definidos o documenta un cambio de contrato.

M0 ejecuta ambos niveles. Los ejemplos válidos se aceptan; cada parche negativo falla en la capa y con el código declarado. `jsonschema` usa `FormatChecker`, por lo que fechas y URLs no quedan como anotaciones sin comprobar. Los modelos generados incluyen Assessment, ProviderResult, errores, base accionaria y transformaciones tipadas. `validate_lineage` comprueba IDs desconocidos y ciclos sobre el conjunto cargado.

Los modelos de M0 fijan contratos, no pertenencia persistida: comprobar que issuer, listing, snapshot, revisión y evidencias existen en repositorios corresponde a M1. Asimismo, el request FCFF sólo comprueba que sus bindings son completos y referencian `evidenceIds`; la resolución contra hechos/supuestos reales del snapshot llega antes de activar el motor en M4.
