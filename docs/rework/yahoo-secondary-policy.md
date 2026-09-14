# Política Yahoo secundaria · R11

Versión de parser: `yahoo-r11-v1`. Biblioteca resuelta en el lock: yfinance 1.7.0.

Yahoo Finance se rotula siempre como fuente secundaria obtenida mediante yfinance. El proyecto es de uso personal; no interpreta la licencia Apache de la biblioteca como derecho para redistribuir los datos descargados. Las capturas persistidas son normalizaciones internas identificadas, no respuestas HTTP originales ni datos oficiales de una bolsa.

## Identidad y capacidades

Cada solicitud debe traer emisor, instrumento, listing, MIC, moneda, zona horaria y rango. La moneda y zona reportadas por Yahoo deben coincidir. `exchangeName` se conserva como código de fuente separado: no reemplaza el MIC resuelto ni convierte por defecto una cotización en “equivalente Nasdaq”.

Las capacidades son independientes:

- `prices`: cierre bruto, cierre ajustado sólo por splits calculado hasta una fecha explícita y `Adj Close` de Yahoo rotulado `total_return`;
- `session`: apertura/cierre regular de la sesión actual cuando Yahoo los entrega;
- `calendar`: fechas con observaciones dentro del rango, marcadas expresamente como cobertura observada y no como calendario bursátil oficial;
- `actions`: dividendos y splits con semántica, ex-date, moneda o factor propios.

El adaptador pide `auto_adjust=False`, no activa reparaciones heurísticas y no fusiona `Adj Close` con el cierre bruto. Un split histórico se aplica al cierre anterior una sola vez; un dividendo no entra en la serie `split_adjusted`. Si Yahoo falla, el worker registra el error y programa reintento sin sustituir la última captura válida de la caché (A15).

Los tests normales usan un cliente congelado sin red. `tests/v2/smoke/test_yahoo_live.py` sólo se ejecuta al definir `RUN_YAHOO_SMOKE=1`; su resultado depende de la disponibilidad externa y nunca redefine los oráculos deterministas.
