# Especificación de motores financieros

Los motores son funciones deterministas sobre hechos, ajustes y supuestos tipados. No descargan datos ni leen `Ticker.info`. Cada resultado devuelve inputs, período, moneda, fórmula/versión, estado y motivos de bloqueo. Las fórmulas se revisan de forma independiente; no se trasladan intactas por haber pasado tests anteriores.

## 1. Períodos, identidad contable y acciones

- TTM de flujos: cuatro trimestres independientes consecutivos y compatibles; también FY + YTD actual − YTD comparable anterior, conservando linaje. No sumar cuatro YTD. Q4 puede derivarse como FY−9M si definiciones, moneda y revisiones coinciden.
- Saldos como caja y deuda se toman a un instante; nunca se suman como flujo TTM. Para ROIC/ROE usar capital medio coherente con la duración, no mezclar TTM con patrimonio de otro año sin identificarlo.
- CAGR usa tiempo real entre extremos y continuidad de cobertura. Si cruza valores no positivos, el CAGR no es interpretable y se muestra variación absoluta/turnaround. No saltar pérdidas para «normalizar» crecimiento.
- EPS reportado básico/diluido no se reemplaza silenciosamente por utilidad/acciones al cierre. Numerador, dilución y acciones medias deben coincidir.
- Splits: conservar original y base ya reexpresada. Aplicar una única transformación desde la base del hecho hasta la base objetivo. ADRs y clases requieren relación explícita.
- Historia de ratios identifica `asReported` frente a `latestRestated`; usar sólo datos conocidos para la fecha si se pretende evaluar decisiones históricas.

## 2. Normalización

Libro de ajustes inmutable: `adjustmentId`, concepto y hecho original, período, importe/signo, recurrente/no recurrente/incierto, tratamiento impositivo, escenario, motivo, documento/página, autor y revisión. La cifra reportada nunca se modifica.

Evaluar ganancias extraordinarias, impuestos atípicos, reestructuraciones, deterioros, capital de trabajo, adquisiciones, SBC, capex, arrendamientos y partidas de operación discontinuada. Una reestructuración repetida no se excluye automáticamente. Deterioros no monetarios tampoco prueban por sí solos que la pérdida económica sea irrelevante.

Separar capex total de mantenimiento/crecimiento sólo con evidencia o supuesto explícito. Sin esa separación, usar capex total documentado y limitar la afirmación sobre owner earnings. Para ciclo medio, ingresos, precios, márgenes y reinversión deben pertenecer al mismo escenario de ciclo.

Capital de trabajo operativo = activos operativos corrientes sin caja/inversiones − pasivos operativos corrientes sin deuda financiera; guardar lista de conceptos incluidos. `currentAssets − currentLiabilities` es liquidez general, no automáticamente inversión operativa.

SBC: elegir una política visible. En FCFF construido desde EBIT que ya incluye SBC, el gasto ya reduce NOPAT; no volver a restarlo. Si se parte de CFO con SBC añadida de vuelta, una aproximación económica puede descontarla una vez, con puente explícito. Separar dilución histórica/acciones pendientes conocidas de dilución futura modelada; no cargar simultáneamente coste económico de futuras concesiones y toda su dilución como si fueran gastos independientes sin reconciliar. El primer motor usará EBIT y SBC como gasto, con sensibilidad documentada, y no activará por defecto un segundo castigo por concesiones futuras. D&A incluye sólo depreciación/amortización: no el agregado de ajustes no monetarios de CFO que volvería a añadir SBC. Las RSU/opciones ya concedidas son reclamaciones existentes; resolver su tratamiento y base de acciones con evidencia, separado del gasto de concesiones futuras. Si faltan esos datos, indicar dilución pendiente y sensibilidad.

Los ajustes afectan efectivamente los flujos valorados. Una tabla «FCF después de SBC» desconectada del DCF no cumple la especificación.

## 3. Calidad y reinversión

| Métrica | Definición inicial | Requisitos |
|---|---|---|
| ROIC | NOPAT / capital operativo invertido medio | Componentes del capital, goodwill/leases y tax policy explícitos; denominador positivo |
| ROIC−WACC | Comparación de rentabilidad operativa y costo empresarial | Mismo perímetro y contexto; no aplicar a bancos por defecto |
| ROE | Utilidad atribuible / patrimonio medio | Patrimonio positivo y denominador compatible |
| ROIC incremental | ΔNOPAT / Δcapital invertido en ventana definida | Denominador material positivo, adquisiciones y ciclo identificados; de otro modo no interpretable |
| Conversión | CFO/utilidad y FCF reportado/utilidad, como diagnósticos distintos | Mismo período y definición; utilidad >0 para ratio convencional |
| Estabilidad | Márgenes, FCF y ventas con rango, dispersión y años disponibles | Mínimo 3 períodos; preferir 5; 1 año no prueba estabilidad |
| Deuda/FCF | Deuda neta verificable / FCF de referencia documentado | Deuda y caja conocidas; FCF positivo y explicación de normalización |
| Intereses | EBIT/intereses de gasto coherentes | No aplicable a banca como test industrial |
| Dilución | Acciones al cierre ajustadas por splits y CAGR comparable | No mezclar con medias diluidas |
| Recompras | Caja gastada, precio medio si existe, variación neta de acciones y SBC | Diferenciar devolución de capital de compensación de dilución |
| Orgánico | Crecimiento reportado menos efectos adquisiciones, FX y perímetro según conciliación del emisor | Sin desglose no inventar crecimiento orgánico |

Un alto ROIC histórico con crecimiento no demuestra automáticamente que nueva inversión gane el mismo retorno. Mostrar ROIC incremental por separado y hacer explícitos los supuestos de la inversión futura.

## 4. Modelo operativo prioritario: FCFF

Por año t:

```text
Revenue_t = Revenue_(t−1) × (1 + growth_t)
EBIT_t = Revenue_t × operatingMargin_t
NOPAT_t = EBIT_t − operatingTaxes_t
FCFF_t = NOPAT_t + D&A_t − Capex_t − ΔOperatingNWC_t
EV = Σ FCFF_t / (1 + WACC)^t + TV_N / (1 + WACC)^N
Equity = EV + excessCash + nonOperatingAssets − debt − preferred − minorities − otherClaims
ValuePerShare = Equity / sharesOnValuationBasis
```

Fecha de valoración y flujos: guardar `valuationDate`, inicio/fin de cada período y `cashFlowAt`. Convención inicial: flujos al final del período, exponente ACT/365,25 desde valuationDate; sin mid-year implícito. El primer contrato admite períodos futuros consecutivos de 12 meses desde la fecha de valoración: pueden ser años móviles, rotulados como proyección propia, sin pretender que sean FY del emisor. La base anual normalizada necesita período y puente documentados hasta el punto de partida. Un primer período fiscal parcial necesita otro contrato con proyección de la porción restante y reconciliación con lo ya reportado; queda bloqueado hasta definirlo. No volver a valorar como futuro el flujo ya realizado ni solapar TTM con un FY completo. La fórmula con t entero representa el caso de períodos anuales completos.

Impuestos de la primera versión: `operatingTaxes = max(EBIT, 0) × taxRate`; no reconocer crédito inmediato por pérdidas ni arrastres tributarios sin módulo específico. La simplificación se muestra en supuestos. El terminal positivo aplica la tasa estable. La base accionaria debe tener una conciliación de acciones ordinarias vigentes y reclamaciones existentes: si una RSU/opción entra en acciones equivalentes no vuelve a restarse como `otherClaims`; si se descuenta su valor como reclamación no vuelve a añadirse al denominador. No usar acciones diluidas medias de EPS como sustituto de esta conciliación. Una relación ADR convierte el valor por acción subyacente a la unidad negociada una sola vez.

Primera versión: crecimiento orgánico. Si se incorporan adquisiciones proyectadas, el desembolso y efecto en capital deben entrar explícitamente; no permitir crecimiento adquirido gratuito.

Payout y dividendos no se restan de FCFF. El puente EV→equity se aplica una vez. Caja operativa necesaria no se añade otra vez como excedente. Capitalización de arrendamientos, minoritarios y participadas exige tratamiento coherente entre EBIT, deuda y perímetro.

WACC se estima o se introduce manualmente con fuente/fecha: costo de patrimonio, costo de deuda, tasas de impuesto pertinentes y pesos de capital. Un dato faltante puede convertirse en supuesto del usuario registrado; no en un default observado. La relación FCFF/WACC y flujos a accionistas/costo de patrimonio sigue la distinción de [Damodaran](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm).

El primer modo proyecta drivers explícitos por año. Un modo con flujos externos es adicional y declara `cashFlowType` y años, preservando huecos. No comprime 2027 y 2029 como años 1 y 2. FCF derivado de utilidad estimada por una conversión histórica se etiqueta «proyección derivada», no «FCF de consenso».

### Terminal

Tasa y flujos comparten moneda, inflación y definición. `WACC > g`. En estado estable:

```text
ReinvestmentRate = g / ROIC_terminal
FCFF_(N+1) = NOPAT_(N+1) × (1 − ReinvestmentRate)
TV_N = FCFF_(N+1) / (WACC − g)
```

Primer modo terminal: NOPAT>0, ROIC>0, g≥0, 0≤g/ROIC≤1 y WACC>g; bloquear si el puente a ese estado es incoherente. Contracción perpetua, liquidación o reinversión superior a 100% requieren otra especificación. La transición desde el último año explícito no puede cambiar márgenes o reinversión sin hipótesis documentada. No forzar automáticamente crecimiento perpetuo excesivo ni permitir crecimiento sin reinversión. Mostrar porcentaje del valor atribuible al terminal, supuestos y sensibilidad. Si Equity≤0, comunicar que el EV modelado no cubre reclamaciones, sin ocultarlo como error genérico ni presentar cotización negativa como objetivo.

### Modelos posteriores

FCFE es otro motor: flujos después de inversión y financiación neta a `ke`; no volver a descontar deuda principal. No implementarlo como alias de `freeCashflow` del proveedor. Retenerlo fuera del primer piloto salvo que un caso de uso lo justifique y existan inputs de financiación.

## 5. Reverse DCF y escenarios

Resolver una variable identificada: crecimiento de ventas, margen terminal o ajuste a flujos externos. La respuesta explica las variables mantenidas fijas; no puede inferir tres incógnitas de un solo precio.

Algoritmo: evaluar dependencia/sensibilidad respecto del parámetro, validar intervalo, localizar cruce y resolver; conservar objetivo, valor obtenido, residual y tolerancia. Respuestas `solved`, `unidentifiable`, `out_of_bounds`, `no_solution`, `blocked`. Un extremo del intervalo no es la estimación exacta. Para flujos externos fijados, resolver un parámetro del tramo libre o un factor de ajuste explícito.

Escenarios pesimista/base/optimista: ingresos, márgenes, reinversión, dilución/capital, tasa y terminal coherentes. Probabilidades opcionales, editables y sumando 1; si no se asignan, no calcular valor ponderado. 25/50/25 sólo puede ser una plantilla rotulada como supuesto inicial. La ponderación combina escenarios del mismo método, no modelos incompatibles.

Cada escenario tiene valor presente y puede tener precio de salida futuro, que es un cálculo distinto. Registrar pérdida relativa al escenario pesimista, upside optimista y ratio de asimetría. Si downside=0, no fabricar ratio 3×: usar no acotado/no definido con explicación. Sensibilidad y reverse emplean exactamente el motor principal.

## 6. Margen de seguridad e incertidumbre

```text
discountToValue = (Value − Price) / Value
upsideToValue = (Value − Price) / Price
entryPriceForDiscount = Value × (1 − requiredDiscount)
```

Definición válida para Value>0 y Price>0. Ejemplo V=100/P=75: descuento 25%, upside 33,333%; descuento exigido 25% da precio 75.

Rangos orientativos del método de Pablo: estable 10–15%; cíclica/incierta 20–30%; turnaround/binaria 30–40%; imposible de valorar, sin conclusión. Son políticas de investigación editables con razones, no calibración estadística ni garantía de protección. Un dato crítico desconocido no se resuelve aumentando el margen. Registrar incertidumbre de negocio, modelo y datos por separado.

## 7. Métodos sectoriales

| Tipo | Motor/prueba | Requisitos específicos y bloqueo |
|---|---|---|
| Banco | DDM multietapa y resultado residual, costo de patrimonio | ROE, book equity, payout sostenible, capital regulatorio/holgura; sin defaults de ROE o solvencia |
| Aseguradora | Modelo de patrimonio/distribuciones y métricas pertinentes | No heredar sin revisión plantilla bancaria; capital/resultado asegurador y reservas |
| Gestora/procesador de pagos | Clasificación económica revisada | Sector «Financial Services» no impone DDM a toda empresa |
| REIT | AFFO reconciliado por acción y NAV | FFO reportado/definido, ajuste recurrente, capex/leasing y deuda; FCF industrial no reemplaza AFFO |
| Cíclica | EBIT/FCF de ciclo medio, activos como contraste | Unidades, precio de commodity, costo y reinversión de ciclo coherentes; pico reciente no es base permanente |
| Holding | Suma de partes | Valor y participación de cada segmento, deuda de holding, minoritarios, impuestos y costos; evitar doble conteo |

AFFO no tiene una definición estandarizada universal: comparar conciliaciones del emisor y registrar ajustes propios; esto está señalado por [Nareit](https://www.reit.com/glossary/adjusted-funds-operations-affo). Importación manual de una conciliación es un primer paso válido. El módulo no pasa por llenar un campo AFFO con una etiqueta automática.

Múltiplos PER/EV-EBIT/EV-FCF sirven como controles cuando beneficios/flujo están normalizados y el denominador es pertinente. Registrar muestra histórica/pares y régimen; no utilizar mediana histórica como destino inevitable. Graham/Lynch/EPV quedan en herramientas exploratorias sólo si su fórmula y aplicabilidad están claramente delimitadas.

### Contratos y oráculos sectoriales previos a activación

Estas fórmulas fijan la semántica mínima. R30–R34 deben transformarlas en contratos tipados y fixtures; antes de superar esa revisión el clasificador sólo determina aplicabilidad y requisitos, sin emitir valor sectorial. Los ejemplos son sintéticos y usan períodos de exactamente un año para revisión a mano; producción usa fechas de descuento explícitas.

**Banco: dividendos y resultado residual.** Inputs: patrimonio común inicial atribuible, acciones y emisiones, ROE por año, distribuciones netas, otros cambios patrimoniales, costo de patrimonio y puente de capital regulatorio. `NI_t = ROE_t × B_(t−1)` en la convención inicial sobre capital inicial; no confundirlo con ROE histórico sobre patrimonio medio. `B_t = B_(t−1) + NI_t − distributions_t + equityIssues_t + otherEquityChanges_t`. La capacidad de distribuir requiere capital regulatorio elegible y activos ponderados por riesgo después del crecimiento; patrimonio contable no sustituye CET1. Los mínimos/restricciones se obtienen para entidad y fecha, nunca de una constante universal.

DDM valora distribuciones a propietarios actuales netas de aportes atribuibles, descontadas a `ke`, con efecto de emisiones/recompras sobre su participación. Primera implementación restringida: acciones constantes, sin emisiones/recompras proyectadas; si son materiales, ampliar contrato antes de valorar. Terminal estable: `payout = 1 − g/ROE_terminal`, `Dividend_(N+1) = NI_(N+1) × payout`, `TV = Dividend_(N+1)/(ke−g)`, con `ke>g`, ROE positivo y payout entre 0 y 1. Crecimiento compatible con retención y capital. Resultado residual: `EquityValue = B_0 + PV[NI_t − ke × B_(t−1)] + PV[residual terminal]`; exige puente de clean surplus y tratamiento de OCI/otros cambios. No promediar DDM y residual: bajo iguales supuestos deben reconciliarse.

Oráculo perpetuo estable: B0=100, ROE12%, g3%, ke10%, payout75% y acciones10. NI1=12, dividendo1=9, valorDDM=9/(0,10−0,03)=128,5714286; residual=100+(12−10)/(0,10−0,03)=128,5714286; por acción12,85714286. Es un ejemplo matemático condicionado a capital suficiente, no una demostración de solvencia. Sin datos regulatorios un caso real no se aprueba por coincidir con el ejemplo.

**REIT: AFFO y NAV.** Partir de FFO atribuible a comunes según conciliación del emisor. `AFFO = FFO − capexRecurrente − leasingRecurrente − rentaNoMonetariaAñadida + otrosAjustesDocumentados`, respetando signos y partidas ya incluidas. No usar una tasa fija de conversión de FCF industrial. `EquityValue_multiple = AFFO_common × targetMultiple`; no restar deuda otra vez de ese valor de patrimonio. Ejemplo FFO120, capex20, leasing5, renta no monetaria5 ⇒ AFFO90; acciones10, AFFO/acción9; múltiplo supuesto12⇒valor108/acción.

NAV por activos: `GrossPropertyValue = Σ stabilizedNOI_i / capRate_i` para activos/perímetros comparables; incluir otros activos y descontar deuda, preferentes, minoritarios y costos corporativos capitalizados no contenidos en NOI. Tasas de capitalización son supuestos/evidencia de mercado fechados, no ke. Ejemplo NOI80, capRate8%⇒activos1000; caja20, deuda400, otras reclamaciones20⇒patrimonio600; acciones10⇒NAV60/acción. AFFO108 y NAV60 de este ejemplo no se promedian: el desacuerdo exige revisar hipótesis. Vacancia, deuda por JV y capex diferido deben estar asignados una vez.

**Ciclo medio.** Definir unidades físicas, precios, costos variables/fijos, mantenimiento y crecimiento. `Revenue = volume × normalizedPrice`; `EBIT = Revenue − cashOperatingCosts − D&A`; FCFF y puente al patrimonio reutilizan el motor central con estos drivers. La ventana debe cubrir expansión y contracción; cinco años no garantizan un ciclo completo. Ejemplo 100 unidades × precio10=1000, costo operativo de caja700 y D&A100⇒EBIT200; impuestos25%⇒NOPAT150; capex120 y ΔNWC10⇒FCFF120. Con precio pico14 y mismos otros inputs, FCFF420: escenario diferente, nunca capacidad permanente por ser el dato reciente. El múltiplo normalizado necesita justificación propia; no activar valor por activos sin capacidad real de realización.

**Suma de partes.** Cada segmento declara si entrega EV o equity, moneda, fecha, participación económica, deuda/minoritarios ya incluidos y método. Convertir primero EV de subsidiaria a equity y multiplicar por participación; sumar participaciones de equity. Después aplicar sólo caja/deuda/costos/impuestos de holding no incluidos. Ejemplo A: EV500−deuda 100=equity400, participación80%⇒320; B: equity200, participación50%⇒100; caja holding30−deuda holding50−costos/impuestos PV20⇒equity holding380; acciones10⇒38/acción. No restar otra vez100 de deuda de A. Una participación material sin valoración produce total parcial identificado y bloquea el fair value completo.

## 8. Monedas y alternativa ETF

USA se presenta en USD y Chile en CLP. Conservar estados en moneda original. Para historia nominal convertida, utilizar tasas correspondientes al período (flujos) o fecha (saldos); una vista a moneda constante es otra vista, identificada. El FX actual no reescribe silenciosamente todos los ratios históricos.

Se puede valorar una emisora chilena que reporta USD en USD con tasas consistentes y convertir el valor resultante a CLP a la fecha de valoración. Una proyección directamente en CLP exige drivers/tasas CLP. No aplicar Treasury USD a flujos nominales CLP por comodidad.

La tasa que hace coincidir un FCFF con su EV no es directamente rentabilidad del accionista. Comparar alternativas mediante flujos al inversor: precio pagado, distribuciones, acciones y valor de salida a horizonte definido. Resolver IRR con detección de ausencia/múltiples soluciones; si sólo hay precio inicial/final sin distribuciones usar CAGR. «Real» se reserva para retorno ajustado por inflación; de otro modo es nominal.

Contrato inicial de retorno por escenario: fecha de compra/valoración, precio y comisiones, fechas e importes de distribuciones por acción, fecha de salida, moneda y método de salida. Ruta inicial `exit_multiple`: EPS normalizado atribuible a comunes en la fecha de salida × PER de salida documentado; REIT puede utilizar AFFO por acción y múltiplo correspondiente una vez habilitado. EPS futuro incorpora intereses, impuestos y base accionaria compatibles; no se calcula desde el precio que se pretende justificar. Distribuciones son supuestos explícitos cuya sostenibilidad debe revisarse, no un dividendo creciendo automáticamente 5%. El valor presente DCF permanece separado como contraste. Si no hay supuestos de salida/distribuciones suficientes, mostrar retorno pendiente.

Ruta posterior `roll_forward_dcf`: valorar a fecha de salida únicamente los flujos posteriores y añadir el puente caja/deuda/reclamaciones/acciones **proyectado para esa fecha**. No usar caja actual en un EV futuro. El puente debe reconciliar flujos, financiación y distribuciones: la caja distribuida no puede seguir incluida como caja acumulada en el precio de salida. Esta ruta se habilita sólo con contrato de capital completo; no se activa como `fairValue_actual × (1+WACC)^h` por defecto.

Oráculo simple de retorno: compra 100 hoy, venta121 exactamente 2 años después, sin distribuciones ⇒ CAGR10%. Si además se distribuyen5 al final de cada año, los flujos son−100, +5, +126 y la IRR anual≈14,77755786%; verificar con fechas si se usa XIRR. No llamar a10% la rentabilidad total de ese segundo caso. Ponderar probabilidades de escenarios no transforma la IRR de flujos esperados en una rentabilidad garantizada; presentar retornos por escenario y la convención de cualquier agregado.

VT y VOO son alternativas distintas. Mostrar supuesto de retorno esperado y su fundamento separado del retorno histórico observado; el usuario puede fijar un umbral personal y prima adicional requerida. Tasa libre de riesgo + prima es una hipótesis de comparación, no pronóstico del ETF.

Comparación Chile/ETF: misma moneda mediante escenario FX explícito, o estado «No comparable aún». Para retorno acumulado sin flujos intermedios en el mismo horizonte: `(1+rUSD) × (FX_final/FX_inicial) − 1`, con FX expresado en CLP/USD. Si rUSD es anualizado a h años, convertir `(1+rUSD)^h` y anualizar después. Con dividendos/aportes, convertir cada flujo a su tasa/fecha y resolver XIRR; no multiplicar una IRR directamente por la variación FX. No ocultar decisión FX ni imponer conversión en todas las pantallas.

## 9. Puntuación y reglas de decisión

Mantener pesos 25/20/15/25/10/5. El [catálogo inicial](09-politica-de-evaluacion.md) fija puntos, umbrales e historia mínima. `financialAssessment` conserva los 100 puntos dejando pendientes los criterios personales; `personalAssessment` los completa con revisiones documentadas, sin redistribuir peso. No ordenar ambas modalidades juntas. Cada plantilla sectorial suma 100, con criterios y evidencias adecuados al negocio. Provisionalmente una métrica industrial no aplicable queda fuera del resultado y bloquea ranking comparable hasta que exista plantilla revisada.

Registrar por criterio: puntos máximos, resultado, evidencias, mínima historia requerida, umbral/versión y `applicable`. Cobertura válida cuenta criterios con datos suficientes, no sólo números no nulos. Diferenciar rango por puntos pendientes de intervalo de confianza; no dar más importancia a una empresa 2/2 que otra ampliamente estudiada.

Ranking por grupos de aplicabilidad y elegibilidad, después puntuación y cobertura; usar umbral inicial 80% de cobertura válida más inputs críticos completos, rotulado como política provisional. La interfaz no «normaliza» una muestra mínima para declararla excelente. La misma revisión cualitativa y de cartera produce los mismos puntos en cualquier vista.

Un rating manual necesita evidencia específica y justificación; guardar rating sin evidencia no cierra el pendiente. No duplicar nota Buffett como segunda recomendación. Fuentes en conflicto, precio/FX no comparable o modelo no aplicable prevalecen sobre un score alto.

## 10. Portafolio y seguimiento

Ledger de compras, ventas, aportes/retiros, comisiones, dividendos y correcciones. Acciones corporativas conservan ex-date, pay-date, factor y base. Evitar sumar dividendos a una serie que ya representa total return. Benchmarks utilizan los mismos flujos externos y fechas, con política de reinversión consistente.

Presentación de exposición y rentabilidad en dos grupos USD/CLP por defecto. Total consolidado sólo cuando existe política FX explícita y cobertura completa. TWR mide desempeño independiente de aportes; XIRR mide experiencia del inversor; no mezclarlos. Si faltan acciones corporativas/cotizaciones/FX necesarios, mostrar parcial e inhibir alfa y propuesta de posición.

Encaje no puede basarse sólo en sector/moneda: registrar pesos, exposición por emisor y solapamiento conocido de ETFs, correlación sólo con historia comparable, y límites personales. Tamaño sugerido como simulación usando presupuesto de pérdida/escenario y límites; una caída modelada no representa pérdida máxima garantizada. Sin evidencia suficiente, no recomendar peso automáticamente.
