# Producto y experiencia de uso

## Resultado que debe entregar la app

Ayudar a determinar qué expectativas incorpora un precio, qué evidencia respalda una tesis, qué supuestos pueden fallar y si una acción merece investigarse frente a un ETF diversificado. Una acción barata por PER no recibe automáticamente una conclusión favorable.

El producto debe ser comprensible para Pablo sin conocer la arquitectura de proveedores. En la pantalla se usan nombres como «Dato reportado», «Supuesto propio», «Falta el período» o «Fuentes en conflicto». Los identificadores internos y errores HTTP pertenecen al panel de diagnóstico.

## Navegación principal propuesta

| Destino | Pregunta que responde | Contenido principal |
|---|---|---|
| Mi investigación | ¿Qué requiere atención? | Empresas seguidas, reportes nuevos, tesis pendientes de revisión, cambios materiales |
| Explorar | ¿Qué candidata merece tiempo? | Filtros, universo y fecha, cobertura, tipo de negocio, métricas comparables |
| Empresa | ¿Entiendo y puedo valorar este negocio? | Expediente con cinco pasos, fuentes y escenarios |
| Comparar | ¿Qué alternativa tiene mejor relación retorno/riesgo? | 2–4 acciones y benchmark, mismo horizonte, fecha, método y moneda comparable |
| Cartera | ¿Cómo encaja y cuánto riesgo añade? | Tenencias, pesos, costos, rentabilidad y reglas personales |
| Datos y configuración | ¿Qué está disponible y actualizado? | Fuentes activas, últimas consultas, carga de archivos, backup, configuración |

El gráfico de precio, RSI, medias móviles y distancia al máximo pasan a una sección secundaria «Mercado». No deben dominar el resumen ni otorgar puntos de inversión fundamental. Noticias y objetivos de analistas también quedan en contexto.

## Expediente de empresa

Cabecera: nombre, mercado/instrumento, moneda, precio con fecha y sesión, último período reportado, estado de datos y fecha del análisis. El nombre del proveedor no equivale a un sello de auditoría.

### 1. Negocio y calidad

Mostrar descripción factual vinculada al documento, segmentos e ingresos por segmento si existen, clientes, retención, competidores, motores y riesgos. Distinguir texto reportado de interpretación del usuario. Campos concretos para competidores, razones de permanencia del cliente y qué destruiría la ventaja; no esconderlos dentro de una única tesis genérica.

La calidad se organiza en retorno sobre capital frente a su costo, márgenes y variación, conversión de ganancias, reinversión y crecimiento orgánico. Cada gráfico permite abrir el dato, su período, su definición y su fuente. ROIC alto es evidencia económica, no prueba automática de foso.

### 2. Cifras y normalización

Tabla de reportado → ajuste → normalizado con tres estados financieros, unidad original y moneda de presentación. El usuario puede ver importes originales cuando un reporte use USD aunque la acción chilena se muestre en CLP.

Cada ajuste tiene importe, signo, período, motivo, evidencia y tratamiento impositivo. Mostrar lo que falta: por ejemplo, «No se conoce capex de mantenimiento; el escenario conserva capex total». Seleccionar un dato discrepante exige una resolución documentada; no promediar fuentes en conflicto.

### 3. Precio y expectativas

Reverse DCF central: «Manteniendo estos márgenes, reinversión y tasa, el precio exige X». El usuario elige la variable que se resuelve y ve qué supuestos permanecen fijos. No afirmar que una ecuación identifica simultáneamente crecimiento, margen y ROIC.

Tres escenarios editables con valores presentes, supuestos, probabilidad opcional y precio de salida a un horizonte explícito. No mezclar valor presente con objetivo a cinco años. Mostrar concentración del valor en el terminal y sensibilidad.

### 4. Decisión y alternativa

Resumen de calidad, valoración, incertidumbre y encaje. Presentar criterios faltantes junto a los que sí se evaluaron. Comparar retorno anualizado por escenario y umbral personal. VT/VOO deben identificarse como ETFs distintos, no como un único activo con retorno garantizado.

Registrar decisión de Pablo: investigar, esperar, descartada, incorporada o revisar. La aplicación puede advertir requisitos incompletos, pero el hecho de superar una nota no se convierte en orden de compra.

Tesis en una frase, tres motores, tres riesgos, señales para aumentar, invalidación y límite personal de posición. Cada riesgo debe poder relacionarse con una métrica o hecho observable.

### 5. Seguimiento

Línea de tiempo de reportes, cambios de supuestos y decisiones. Comparar tesis anterior con cifras nuevas. Una alerta requiere condición, dato requerido, fecha y estado de disponibilidad. Si falta el dato, su estado es «No evaluable» y no «No pasó nada».

## Estados independientes

| Dimensión | Valores visibles de ejemplo | Efecto |
|---|---|---|
| Origen | Reportado / derivado / supuesto / juicio manual | Explica qué representa la cifra |
| Disponibilidad | Disponible / faltante / no aplicable / no soportado / bloqueado | Decide qué se puede calcular |
| Frescura | Actualizado / pendiente actualización / desactualizado | No se confunde con origen o exactitud |
| Conciliación | Fuente única / contrastado / en conflicto | Expresa controles realizados |
| Análisis | Borrador / listo para revisión / revisado / requiere revisión | No equivale a atractivo financiero |

Un dato puede ser reportado, desactualizado y conflictivo a la vez. Por eso no se usa un único enum que mezcle esas dimensiones.

## Cuándo está completo un análisis

«Listo para revisión» requiere identidad resuelta; precio fechado; moneda y base de acciones coherentes; insumos críticos presentes o asumidos de manera explícita; ninguna discrepancia crítica abierta; modelo apropiado; escenarios válidos; negocio y riesgos documentados; benchmark y horizonte compatibles. «Revisado» añade revisión humana registrada de los supuestos y evidencia.

El 100% de puntos cubiertos no es una condición suficiente ni necesaria para haber revisado un modelo. Una empresa podría estar completamente documentada y seguir siendo imposible de valorar razonablemente. Las métricas no aplicables deben separarse de las faltantes.

## Componentes y reglas de interfaz

- `MetricValue`: importe + unidad + período + estado; un clic abre evidencia.
- `EvidenceDrawer`: documento/URL, ubicación, cifra original, transformación y alternativas.
- `CoverageSummary`: puntos conocidos, faltantes y no aplicables; sin barras que sugieran probabilidad de éxito.
- `NormalizationBridge`: cambios auditables, sin edición silenciosa del histórico.
- `ScenarioEditor`: supuestos agrupados por ingresos, márgenes, inversión, capital y tasa.
- `ModelAvailability`: por qué un modelo está habilitado o bloqueado y acción para resolverlo.
- `DecisionMemo`: hechos e interpretación separados, guardado por versión.
- `RefreshStatus`: última copia útil visible mientras se actualiza; reintento puntual por conjunto de datos.

El valor de una celda faltante será «Sin dato», nunca 0. El cero reportado debe poder distinguirse visualmente de un vacío. Fechas absolutas además de «hace X». Valores monetarios con USD/CLP visibles; porcentajes y puntos porcentuales no se intercambian.

## Criterios de aceptación UX

1. En una sola vista se entiende fecha del precio, último período, método principal, 3 supuestos y principal bloqueo.
2. Cualquier número decisivo llega a su evidencia en máximo dos interacciones.
3. Cambiar un supuesto modifica sólo el escenario elegido y recalcula a través de API; respuesta atrasada no sobrescribe la edición más reciente.
4. Fuente caída no oculta la tesis, cifras anteriores ni estado del trabajo.
5. Un banco no muestra casillas fallidas de ratios industriales; muestra su panel sectorial y pendientes correspondientes.
6. El mismo análisis tiene mismo `assessmentId`, nota y supuestos en ficha, tabla, comparación y exportación.
7. Navegación por teclado, foco visible, estados anunciados por lectores de pantalla y diseño probado a 390, 768 y 1440 px.
8. Una valoración distinta por cambio de supuestos se explica en la comparación de versiones.

## Funciones deliberadamente posteriores

Extracción con LLM, transcripciones pagas, tiempo real, backtesting de selección masivo, asesoramiento automático y ejecución de operaciones. El MVP no depende de una clave de LLM ni del modelo que esté usando Codex. La extracción asistida futura tendrá que proponer evidencia y someter los hechos a revisión antes de alimentar un motor.
