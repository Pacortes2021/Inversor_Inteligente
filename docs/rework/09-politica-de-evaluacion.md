# Política inicial de evaluación

Identificador propuesto: `operating_company_research_v1`. Estado: política de investigación propuesta para revisión en M0 e implementación R28. **Los pesos y umbrales son heurísticos, no una predicción calibrada de rentabilidad.** No se ha demostrado que una nota alta supere a VT/VOO. La política organiza evidencia; no genera una orden de compra ni oculta los supuestos de valoración.

## Alcance y estados

Primera plantilla: operativas rentables con flujos, capital y métricas interpretables. Empresas con pérdidas, bancos, aseguradoras, REIT y holdings siguen siendo investigables, pero no reciben automáticamente esta nota. Cada plantilla sectorial requiere criterio, fórmula, evidencia mínima, pesos 100 y casos independientes antes de activarse en R34. «No aplicable» no equivale a mala empresa ni a dato faltante.

Cada criterio conserva `criterionId`, `policyVersion`, `maxPoints`, `status`, `fraction`, `earnedPoints`, `inputFactIds`, `evidenceIds`, `rationale`, `assessmentMode` y bloqueos. Estados: `evaluated`, `pending_data`, `pending_judgment`, `conflict`, `not_applicable`. Sólo `evaluated` participa como criterio resuelto. Una cifra numérica desactualizada o de contexto incompatible no cumple la evidencia mínima por existir en el payload.

Puntuar con fracción0, 0,5 o1 según tabla; redondear sólo presentación a un decimal. Valores exactos se conservan para sumas. Los intervalos se aplican en el orden indicado: primero puntuación máxima, después media y luego cero. Un requisito desconocido da pendiente, nunca cero ni puntuación máxima. Cero significa que el criterio sí pudo evaluarse y no cumple el umbral de esta política.

Mínimos comunes: series comparables y completas, calendario/moneda/base accionaria compatibles, hechos válidos sin conflicto material pendiente, definición de ratio versionada. Las tasas son fracciones internamente; «pp» significa puntos porcentuales. Para criterios de niveles y crecimiento, mostrar además los años y valores originales; una nota no sustituye la serie.

## Catálogo inicial: 100 puntos

### Calidad y ventaja competitiva · 25

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| Q1 ROIC frente a costo /10 | 3 FY consecutivos, capital medio positivo, NOPAT compatible; costo de capital documentado para cada comparación o sensibilidad explícita si se usa una tasa de referencia | Spread mediano≥5pp y todos positivos / mediano>0 / restante. Sin política de capital/goodwill no evaluar. |
| Q2 Margen operativo /6 | 5 FY comparables; media, desviación poblacional y último margen | Todos positivos, desviación≤3pp y último≥mediana−2pp / todos positivos y desviación≤6pp / restante. Cambios de perímetro materiales exigen reconstrucción o pendiente. |
| Q3 Conversión de utilidad en caja /5 | CFO y utilidad atribuible compatibles 3 FY; utilidad agregada>0 | CFO agregado/utilidad agregada≥1 y sin anomalía de capital de trabajo pendiente / ratio≥0,8 / restante. Financiación a clientes y factoring requieren interpretación antes de puntuar. |
| Q4 Ventaja competitiva /4 | Juicio personal, fuentes fechadas sobre retención/precio/costos/competidores y posible erosión | Dos mecanismos observables con evidencia y resistencia examinada / un mecanismo razonado y límites explícitos / evidencia revisada no sostiene ventaja. Texto genérico sin fuentes: pendiente. |

### Salud financiera y flujo de caja · 20

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| H1 FCF reportado /5 | CFO−capex total comparable 5 FY; mantener años negativos | Positivo5/5 / positivo3–4/5 / positivo≤2/5. No sustituir por FCF ajustado escogiendo sólo años favorables. |
| H2 Carga de deuda /5 | Deuda y caja explícitas; FCF normalizado positivo y puente aprobado | Deuda neta/FCF≤2 / ≤4 / >4. Caja neta con deuda/caja verificadas cumple; deuda desconocida queda pendiente. |
| H3 Cobertura de intereses /4 | EBIT y gasto de intereses bruto 3 FY; ratio mínimo | Mínimo≥6 / mínimo≥3 / restante. Deuda cero comprobada y gasto cero: cumplimiento documentado; gasto cero con deuda material: revisar, no infinito automático. |
| H4 Liquidez a12 meses /2 | Caja disponible y líneas comprometidas no dispuestas; vencimientos, intereses y usos obligatorios de12 meses, sin doble conteo | Fuentes comprometidas/usos≥1,5 / ≥1 / <1. No incluir una refinanciación futura supuesta como caja disponible. Usos cero comprobados se explica separadamente. |
| H5 Dilución /4 | Acciones al cierre en misma base ajustada por splits, 3 años de distancia | CAGR de acciones≤0% / ≤2% / >2%. Recompras financiadas con deuda y SBC se muestran aunque este criterio cumpla. |

### Crecimiento y reinversión · 15

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| G1 Ventas /4 | CAGR de5 años, extremos positivos, continuidad; perímetro y FX identificados | ≥6% / >0% / ≤0%. Crecimiento nominal reportado; no llamarlo orgánico. |
| G2 EPS normalizado /3 | Extremos positivos separados5 años, ajustes y base accionaria reconciliados | CAGR≥6% / >0% / ≤0%. Cruce por pérdidas no es CAGR negativo interpretable: pendiente de plantilla turnaround. |
| G3 FCF por acción /3 | Mismo horizonte5 años y base; extremos positivos, años intermedios conservados | CAGR≥6% / >0% / ≤0%. Crecer desde un año atípico requiere puente de normalización. |
| G4 Reinversión incremental /3 | ΔNOPAT/Δcapital en ventana3 años; Δcapital>0 y material (≥5% del capital inicial), adquisiciones identificadas; WACC compatible | ROIC incremental−WACC≥3pp / >0 / ≤0. Desinversión o denominador pequeño: no interpretable, no sobresaliente. |
| G5 Crecimiento orgánico /2 | Conciliación del emisor de los últimos2 FY, separando FX/adquisiciones/perímetro | Ambos positivos / uno positivo / ninguno positivo. Sin conciliación no inferirlo restando partidas arbitrarias. |

### Valoración y margen de seguridad · 25

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| V1 Margen de seguridad /7 | Valor base y precio compatibles; descuento exigido>0 elegido y justificado según incertidumbre | Descuento≥exigido / ≥mitad del exigido / restante. Value≤0: criterio incumplido y sin precio objetivo convencional; no dividir por él. |
| V2 Alternativa ETF /6 | Retorno anualizado del escenario base del inversor, benchmark esperado y prima requerida>0, mismo horizonte/moneda/flujos | Exceso≥prima requerida / exceso>0 / exceso≤0. Benchmark y prima son supuestos fechados, no rendimientos garantizados. |
| V3 Expectativas implícitas /5 | Reverse resuelto, variable/rango plausible con evidencia y sensibilidad; demás inputs fijados | Exigencia≤supuesto conservador / ≤supuesto base / >base, para variables cuyo aumento eleva el valor. En sentido contrario invertir comparador expresamente; sin monotonicidad no evaluar por esta regla. |
| V4 Múltiplo normalizado /3 | EPS o EBIT normalizado positivo; múltiplo objetivo razonado por crecimiento/riesgo/reinversión, precio y definición compatibles | Descuento frente al valor por múltiplo≥descuento exigido / descuento>0 / restante. PER histórico es contraste, no objetivo automático. |
| V5 Escenario adverso /3 | Downside del escenario conservador con hipótesis justificadas; pérdida tolerable personal configurada y positiva | Pérdida modelada≤mitad del límite / ≤límite / >límite. Si escenario adverso aún da ganancia, no llamar riesgo cero: exigir escenario de ruptura de tesis o dejar pendiente. |
| V6 Coherencia del modelo /1 | Lista explícita de aplicabilidad, flujos/tasa, terminal, fecha, acciones y puente de reclamaciones revisada | Cumple todas / no hay nivel intermedio / fallo verificado. Un fallo crítico además bloquea valoración y elegibilidad, aunque aquí sólo pese1. |

V1/V3/V4 comparten supuestos económicos y no son tres evidencias independientes. Se conservan porque responden preguntas distintas, sin promediar sus valores ni presentar la nota como diversificación estadística. V5 evalúa riesgo a partir del escenario, no una pérdida máxima garantizada. Los límites personales usados como supuestos numéricos se versionan y pueden acompañar ambas modalidades de evaluación; su ausencia deja el criterio pendiente.

### Riesgos y previsibilidad · 10

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| R1 Previsibilidad de caja /2 | Al menos3 proyecciones anuales archivadas antes del período y resultados posteriores de igual definición | Error absoluto relativo mediano≤15% / ≤30% / >30%. Denominador realizado no material/cero: métrica no interpretable. Sin archivo histórico, pendiente; no reconstruir pronósticos con información posterior. |
| R2 Previsibilidad de utilidad /2 | Mismo criterio temporal y definición para utilidad normalizada;3 observaciones | Error mediano≤15% / ≤30% / >30%. Guidance de emisor y escenario propio son series diferentes; no combinarlos. |
| R3 Resistencia a supuestos /1 | Sensibilidad documentada WACC±1pp y crecimiento explícito±2pp, dentro de dominio; definición de pérdida tolerable | Todas las combinaciones válidas quedan dentro del límite de pérdida modelada / algunas / ninguna. Si una combinación central sale del dominio, revisar el modelo, no descartarla para aprobar. |
| R4 Vencimientos/refinanciación /1 | Calendario de vencimientos3 años, caja/FCF conservador disponible después de usos y restricciones | No depende de nueva financiación no comprometida / cobertura depende de líneas ya comprometidas / déficit. No repetir deuda/FCF como único input. |
| R5 Ciclicidad y riesgos estructurales /2 | Juicio personal con ciclo, regulación, sustitución y escenario de ruptura documentados | Exposición y mitigaciones contrastadas, supervivencia razonable en escenario adverso / riesgos identificados pero mitigación parcial / amenaza estructural sin mitigación convincente. Falta de estudio: pendiente. |
| R6 Concentración /2 | Juicio personal con productos/clientes/proveedores/geografías y documento; «no divulgado» explícito | Dependencias materiales conocidas y alternativas verificadas / dependencia conocida con mitigación parcial / concentración material sin alternativa. No divulgación material impide puntuar como diversificada. |

R1/R2 probablemente estarán pendientes al inicio: es preferible mostrar cuatro puntos sin evidencia a fabricar un historial de aciertos. Se puede incorporar guidance publicado anteriormente si se conserva la fecha y la definición comparable. Su peso no se redistribuye.

### Encaje de portafolio · 5

| ID / puntos | Evidencia mínima | Fracción1 / 0,5 / 0 |
|---|---|---|
| P1 Encaje /5 | Ledger completo, exposición por emisor/moneda, solapamiento ETF conocido, límites personales y tamaño propuesto | Cumple límites y aporta función explícita diferenciada / cumple límites pero aporte de diversificación/retorno es débil / incumple límites. Sin cartera o exposición material desconocida: pendiente, no máxima puntuación. |

## Aritmética, modalidades y ranking

Para una plantilla completa aplicable: `maxPoints=100`; `resolvedPoints = suma(maxPoints de evaluated)`; `earnedPoints = suma(maxPoints × fraction)`; `pendingPoints = 100 − resolvedPoints`; `coverage = resolvedPoints/100`. Mostrar **puntos acreditados**, **cobertura** y **rango por información pendiente = [earnedPoints, earnedPoints + pendingPoints]**. Ese rango no es un intervalo de confianza ni una valoración pesimista/optimista. No mostrar `earnedPoints/resolvedPoints ×100` como nota.

Una plantilla con `not_applicable` queda incompleta hasta asignar una política sectorial aprobada; puede mostrar el detalle evaluado, pero no una nota final de 100 ni ranking comparable. No restar los criterios inaplicables y reescalar por cuenta propia.

`financialAssessment` deja Q4/R5/R6/P1 pendientes:13 puntos personales, máximo resuelto87. Mantiene100 como escala y no añade juicios de tesis sin revisión. `personalAssessment` reutiliza los mismos hechos y supuestos, incorpora la revisión cualitativa y el snapshot de cartera, y puede completar esos 13. La carga manual de un dato reportado con evidencia no lo convierte en juicio personal. No mezclar modalidades, políticas sectoriales o versiones al ordenar.

Elegibilidad inicial: cobertura≥80%, política aplicable y misma modalidad, sin conflictos materiales, precio y moneda comparables, valoración válida y requisitos críticos completos. Deben conocerse o estar explícitamente modelados con evidencia: identidad y base accionaria, período de flujos, normalización, deuda/caja/reclamaciones, moneda/tasa, terminal/reinversión, supuestos por escenario, benchmark/horizonte y riesgos materiales pendientes de resolución. Si falta alguno, no se habilita ranking conclusivo por tener80 puntos de cobertura. El financial ranking se rotula exploración cuantitativa; decidir requiere revisión del negocio y la tesis personal.

Orden: elegibles en grupo comparable, puntos acreditados descendentes, cobertura descendente y nombre como desempate estable. Los no elegibles aparecen en un grupo separado con motivo; pueden ordenarse por una métrica concreta para investigar, sin llamarse «mejores inversiones». Versiones de datos distintas se muestran con sus fechas; para comparar a un mismo corte se exige snapshot temporal compatible.

## Ejemplos obligatorios de R28

1. Sólo un criterio de2 puntos resuelto al máximo: acreditados2, cobertura2%, pendientes98, rango[2,100]. No elegible. No mostrar100/100.
2. Evaluación financiera con los 87 puntos posibles resueltos, acreditados64: cobertura87%, pendientes13, rango[64,77]. Puede estar en exploración financiera si pasa requisitos críticos; no consta aún una tesis personal completa.
3. Evaluación personal con90 puntos resueltos, acreditados72 y deuda desconocida entre pendientes: cobertura90%, rango[72,82]. **No elegible** por deuda crítica ausente. Otra empresa con90 resueltos y60 acreditados pero inputs críticos completos sí puede ser elegible; la puntuación mayor no elimina el bloqueo.
4. Banco con algunos ratios industriales no aplicables: se muestran observaciones bancarias y plantilla pendiente. No «80/80=100». Al activarse una plantilla bancaria revisada se crea otra evaluación con versión propia.

## Cambios de política

Guardar autor, fecha, motivo, umbral anterior/nuevo y casos afectados. Recalcular produce evaluaciones nuevas; decisiones históricas conservan su política original. En M0 revisar umbrales por utilidad para investigación; más adelante contrastarlos con casos fuera de muestra antes de afirmar capacidad predictiva. Los pesos no autorizan omitir el análisis narrativo ni convertir «barato» en compra automática.
