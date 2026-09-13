# Proveedores y calidad de datos

Restricción: uso personal y presupuesto mensual inicial US$0. Documentación consultada el 12–13 de septiembre de 2026. «Documentado» no significa «probado con nuestra cartera». No se compraron planes ni se consultaron endpoints autenticados nuevos. Las tarifas son referencias consultadas, no cotizaciones garantizadas.

## Base gratuita elegida

| Capacidad | Fuente principal propuesta | Respaldo explícito | Alcance/limitación a comprobar |
|---|---|---|---|
| Identidad USA | Directorios/submissions SEC + catálogo propio | Perfil secundario con resolución manual | CIK emisor separado de instrumento/clase/ADR |
| Estados USA | SEC companyfacts/submissions y reporte original | Importación del filing; Yahoo con origen secundario | XBRL estándar no cubre por sí solo todos los segmentos o métricas propietarias |
| Identidad Chile | Registro CMF + catálogo instrumento/plaza | Resolución manual con documento | Mapear RUT, serie y ticker; no inferir ADR/local |
| Estados Chile no bancarios | Documentos XBRL/IFRS CMF y emisor | Importación manual de archivo oficial; Yahoo secundario | Primero piloto de descarga/parser; no presuponer API uniforme |
| Bancos chilenos | API/documentos CMF bancarios | Estados y memorias del banco | Confirmar credenciales, frecuencia, cuentas y series regulatorias |
| Precio USA/Chile, cierre | Yahoo existente como fuente secundaria explícita | Carga fechada verificable para la lista personal | Sin SLA ni promesa de cierre oficial; no usar como precio de ejecución |
| Dividendos/splits | Aviso del emisor/mercado y reporte | Yahoo si identifica semántica y se concilia | Fuente caída es desconocido, no cero eventos |
| FX CLP/USD histórico | BCCh BDE, dólar observado | Archivo oficial importado | Tasa de referencia; no equivale al FX ejecutado del broker |
| Tasa/riesgo | Serie oficial apropiada a moneda y fecha; parámetros propios documentados | Supuesto manual fechado | Sin tasa fija silenciosa ni Treasury USD aplicado como tasa CLP |
| Consenso | Opcional y sólo si existe dato accesible con fecha/metodología | Supuestos propios editables | La valoración no depende de consenso gratuito inexistente |
| Negocio/segmentos/riesgos | 10-K/20-F, memoria y presentaciones | Evidencia introducida por usuario | No requiere LLM pago; interpretaciones se distinguen de cifras |
| VT/VOO | Documentación oficial del fondo + serie de precio/distribuciones identificada | Escenario de retorno manual | Separar descripción, rentabilidad realizada y supuesto de retorno futuro |

La arquitectura permite proveedores adicionales, pero el MVP no construye cinco adaptadores equivalentes antes de tener una ficha confiable. SEC, CMF/importación, BCCh y Yahoo aislado son suficientes para validar la cadena inicial.

## Hechos verificados sobre acceso

SEC ofrece APIs JSON de submissions y hechos XBRL sin API key. La documentación describe unidades y diferencias entre calendarios fiscales, y no habilita CORS para consulta directa desde el navegador. Política publicada: máximo agregado de 10 solicitudes/segundo y acceso identificado. Usar backend con User-Agent propio y ritmo inicial menor, por ejemplo 2/s compartido entre trabajos. [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [acceso justo](https://www.sec.gov/about/developer-resources).

CMF publica taxonomías XBRL, incluida CL-CI 2026, y una consulta de estados IFRS. La API pública encontrada está específicamente orientada a bancos e instituciones financieras; eso no demuestra una API equivalente universal para las sociedades. La primera integración no bancaria debe probar navegación/descarga de documentos y tratamiento de taxonomías reales. [CMF XBRL](https://www.cmfchile.cl/portal/principal/623/w4-propertyvalue-48724.html), [consulta IFRS](https://www.cmfchile.cl/institucional/estadisticas/merc_valores/sa_eeff_ifrs/sa_eeff_ifrs_index.php?lang=es&rg_rf=RGEIN&vigente=1), [API CMF Bancos](https://api.cmfchile.cl/), [resultados bancarios](https://api.cmfchile.cl/documentacion/Estado-de-Resultados-de-Bancos.html).

BCCh documenta REST `GetSeries`/`SearchSeries`, autenticación y la serie de dólar observado `F073.TCO.PRE.Z.D`. Conservar códigos de observación y fechas sin rellenar fines de semana como si existieran transacciones. Validar credenciales disponibles en M3; la importación oficial mantiene el producto utilizable si falta registro. [Documentación BDE](https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/documentacion.html).

yfinance es una biblioteca independiente, sin afiliación ni garantía de Yahoo; sus advertencias de uso y el comportamiento del endpoint deben considerarse al diseñar un respaldo. No proporciona una certificación de exactitud. [Documentación del proyecto](https://ranaroussi.github.io/yfinance/).

La Bolsa de Santiago ofrece productos de datos y un informativo bursátil con información diaria y avisos. La documentación encontrada no permite prometer una API oficial completa gratis. Mantener esta alternativa como futura consulta de cobertura/precio. [Market data de Bolsa](https://servicioscms.bolsadesantiago.com/Corporativo/Documentos/Soluciones%20tecnologicas/Brochure%20nuevos%20Soluciones%20Tecnol%C3%B3gicas/market%20data%20%282%29.pdf), [informativo bursátil](https://tiendaonline.bolsadesantiago.com/VentasOnline/casilla-informativo-burs%C3%A1til-electr%C3%B3nico-ibe).

## Alternativas comerciales, fuera del MVP

| Alternativa | Referencia consultada | Qué resolvería / qué no asumir |
|---|---|---|
| FMP | Basic gratuito 250 llamadas/día; Starter US$22/mes equivalentes facturado anual, 5 años y USA; Premium US$59/mes equivalente anual; Ultimate US$149/mes equivalente anual/global | Verificar entitlement exacto por endpoint. Ni plan básico ni «global» prueban consenso y fundamentales chilenos completos. [Tarifas FMP](https://site.financialmodelingprep.com/developer/docs/pricing) |
| EODHD | EOD All World US$19,99/mes; fundamentales US$59,99/mes; conjunto US$99,99/mes, modalidad personal | Probar ticker/mercado, ajustes, delistados y derechos. Su página advierte limitaciones de precios indicativos; pagar no convierte el feed en fuente bursátil oficial. [Tarifas EODHD](https://eodhd.com/pricing), [catálogo de bolsas](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours) |
| Twelve Data | Grow US$79/mes; Pro US$229/mes; figura XSGO en catálogo | Existir en catálogo no prueba acceso en el plan ni cobertura fundamental. Revisar costo por capacidad. [Precios](https://twelvedata.com/pricing), [XSGO](https://twelvedata.com/exchanges/xsgo?group=regulatory) |
| Alpaca data | Documenta IEX y SIP; la oferta gratuita en vivo usa IEX | Opción USA si hay acceso autorizado. IEX es una plaza, no cinta consolidada; no soluciona Chile ni estados fundamentales. [FAQ oficial](https://docs.alpaca.markets/us/docs/market-data-faq) |

No recomendar adquirir ninguno hasta medir su aporte sobre la muestra. Uso personal y distribución comercial tienen condiciones distintas; registrar derechos de almacenamiento/visualización/exportación según servicio. Esta revisión es técnica/documental, no una licencia otorgada al proyecto.

## Prueba de proveedores antes de seleccionarlos

Muestra propuesta de 10 instrumentos: MSFT, NFLX, FICO, NVO (ADR), JPM, VICI, COPEC.SN, CENCOSUD.SN, CHILE.SN y QUINENCO.SN. Son casos de ingeniería representativos, no recomendaciones de inversión. Confirmar identidad y clasificación mediante documentos; no confiar en el nombre del ticker.

Para cada fuente/capacidad registrar: identidad devuelta; años/trimestres; campos solicitados y obtenidos; unidad/moneda; revisiones; publicación; histórico accionarial; latencia; fallos; diferencia frente al documento; credenciales/condiciones; evidencia de la prueba. Distinguir `documented`, `sample_verified`, `unsupported` y `unknown`.

Pasa la integración cuando los importes seleccionados del último anual y cuatro períodos intermedios de la muestra coinciden con sus documentos dentro de redondeo, y faltantes/conflictos son explicados. No exigir todos los campos a todas las empresas: validar capacidades por tipo. Una tabla con 100 columnas devueltas no es evidencia de calidad si su definición es incierta.

CMF merece un spike de 1–2 sesiones de implementación con entregable: manifest de documentos, 3 emisores y parser inicial o explicación reproducible del impedimento. Si automatizar acceso requiere acciones no disponibles, continuar con importador de archivos oficiales y registrar la cobertura que queda pendiente. Nunca esquivar controles de acceso ni prometer el mismo costo operativo que SEC.

## Políticas iniciales de actualización

| Recurso | Política propuesta | Cuándo se considera problemático |
|---|---|---|
| Cierre diario | Una actualización tras sesión y reintento posterior si no está disponible | Falta una sesión esperada; diferenciar festivo/mercado cerrado |
| Submissions/filings | Una consulta diaria de emisores seguidos y actualización bajo demanda | Nuevo filing sin procesar o fallos sucesivos |
| Estados derivados | Reprocesar sólo por documento/parser nuevo | Último reporte disponible aún no integrado |
| FX oficial diario | Tras publicación de la serie | Fecha requerida ausente; arrastre sólo con regla explícita |
| Eventos corporativos | Diario para instrumentos en cartera | Cobertura interrumpida invalida total return/alfa |
| Consenso opcional | Según capacidad, fecha e informe disponible | Descarga reciente con estimación antigua no cuenta como actualización |
| Datos cualitativos | Al guardar evidencia y al detectar reporte nuevo | La revisión debe renovarse, no borrarse automáticamente |

Se ejecutan mientras la app está abierta y se recuperan pendientes al siguiente inicio; no se promete monitoreo con el computador apagado. Son políticas del producto, no garantías de los proveedores. Worker respeta rate limits, reintentos y presupuesto; horario configurable y zona de mercado. Actualizar 300 empresas con 20 recursos cada una no forma parte del primer arranque.

## Funciones posibles con US$0

Análisis profundo de una lista pequeña, estados reportados USA, documentos Chile, escenarios propios, reverse DCF, registros de tesis y portafolio. Algunas partidas requieren incorporación manual, especialmente AFFO reconciliado, segmentos, capex de mantenimiento y capital regulatorio. El modo gratuito debe ser útil con esos límites; no depender de pruebas temporales de proveedores de pago ni de consenso inventado.
