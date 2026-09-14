# Piloto de proveedores M2 · EE.UU.

Fecha de corte del informe: 14 de septiembre de 2026. Este documento separa acceso documentado, replay determinista, conciliación de muestra y prueba en vivo. No existe una calificación global “100% auditado”.

## Resultado

| Proveedor / capacidad | Evidencia alcanzada | Muestra | Límite vigente |
|---|---|---|---|
| SEC identidad, submissions y companyfacts | Replay determinista | fixtures sintéticos con CIK, accession, publicación, taxonomía, unidad y moneda no USD | smoke en vivo no ejecutado; exige contacto identificado |
| SEC mapeo US-GAAP | Muestra conciliada | Microsoft FY2025 y Netflix FY2025 | sólo conceptos iniciales; extensiones y dimensiones bloqueadas |
| Yahoo precios, sesión, fechas observadas y acciones | Replay determinista | cliente congelado con cierre/dividendo/split | fuente secundaria sin SLA; smoke en vivo no ejecutado |
| Snapshot USA | Replay de extremo a extremo sin red | Microsoft, 10 hechos SEC y un cierre Yahoo sintético identificado | demuestra la cadena, no constituye una captura de mercado actual |

La API `GET /api/v2/capabilities` publica estos niveles y límites. `GET /api/v2/snapshots/{id}` devuelve hechos, decisiones y hashes; cada `documentId` puede abrirse por `GET /api/v2/documents/{id}` para recuperar URL, fecha y hash exactos. Leer el snapshot no actualiza proveedores ni modifica su fecha económica.

## Conciliaciones SEC congeladas

Los importes se almacenan en unidades completas. La tabla siguiente expresa importes y acciones en millones. Capex usa desembolso positivo en el contrato canónico.

| Emisor / FY | Ingresos | EBIT operacional | Utilidad neta | CFO | Capex | Caja | Deuda corriente + no corriente | Acciones medias diluidas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Microsoft 2025, USD | 281.724 | 128.528 | 101.832 | 136.162 | 64.551 | 30.242 | 2.999 + 40.152 | 7.465 |
| Netflix 2025, USD | 45.183,036 | 13.326,603 | 10.981,201 | 10.149,273 | 688,220 | 9.033,681 | 998,865 + 13.463,971 | 4.343,863 |

Fuentes primarias: [Microsoft 10-K FY2025](https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm), [Microsoft resultados FY2025](https://www.sec.gov/Archives/edgar/data/789019/000095017025100226/msft-ex99_1.htm) y [Netflix 10-K FY2025](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/nflx-20251231.htm). Los fixtures `msft-2025-curated.json` y `nflx-2025-curated.json` son extractos seleccionados, no redistribuciones de los payloads originales.

## Semántica Yahoo comprobada sin red

Para una serie sintética con cierre 100 antes de un split 2:1, el contrato conserva `raw=100`, calcula `split_adjusted=50` y mantiene `Adj Close=48` como `total_return`; no intercambia estas bases. `NMS` queda como código devuelto por Yahoo y `XNAS` como MIC previamente resuelto. Al simular una caída posterior, el trabajo queda reintentable y la caché conserva la captura válida anterior (A15).

yfinance declara que no está afiliado ni validado por Yahoo y remite a los términos de uso de Yahoo; esta integración se mantiene como secundaria y personal. [Documentación de yfinance](https://ranaroussi.github.io/yfinance/) y [API Ticker](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.html).

## Pruebas separadas

- Suite determinista: sin red; valida contratos, replay, conciliaciones, selección, snapshot y fallos.
- `test_sec_live.py`: opt-in con `RUN_SEC_SMOKE=1` y `SEC_CONTACT_EMAIL`.
- `test_yahoo_live.py`: opt-in con `RUN_YAHOO_SMOKE=1`.

Ningún smoke fue ejecutado ni declarado exitoso en este corte. Un resultado futuro se fecha y registra aparte; nunca modifica los valores esperados de las pruebas congeladas.
