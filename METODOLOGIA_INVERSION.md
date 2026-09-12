# Metodología de inversión de la aplicación

La aplicación sirve para investigar y comparar candidatas. No debe convertir una cifra aislada en una orden de compra. Su proceso combina calidad, valoración, incertidumbre y una comparación contra la alternativa diversificada VT/VOO.

## Flujo de decisión

1. **Entender el negocio.** La ficha cualitativa documenta cómo gana dinero, la variable que mueve sus resultados, la tesis, el foso y los competidores implícitos en los riesgos.
2. **Medir calidad económica.** Se revisan ROIC, ROE, márgenes, conversión de utilidad a FCF, deuda, intereses, dilución, crecimiento y reinversión.
3. **Normalizar la capacidad de generar caja.** El DCF usa una base robusta entre FCF TTM, último anual y promedio reciente. La auditoría compara el FCF y la utilidad con sus medianas, descuenta la compensación en acciones, contrasta capex/ventas y vigila cambios anómalos de capital de trabajo. Si el flujo más reciente no es positivo, el DCF se desactiva. La separación de capex de mantenimiento, extraordinarios y ciclos por segmento queda marcada como pendiente.
4. **Elegir un modelo principal.** Una empresa operativa con FCF positivo usa DCF; una financiera con dividendos usa DDM; la reversión de múltiplos solo sirve como respaldo cuando no existe un modelo mejor. Graham, Peter Lynch y EPV son controles cruzados. No se promedian métodos incompatibles.
5. **Construir escenarios.** Pesimista, base y optimista cambian crecimiento, tasa de descuento y crecimiento terminal dentro del mismo modelo. Las probabilidades iniciales son 25%, 50% y 25%; representan supuestos, no certezas.
6. **Leer el reverse DCF.** La app muestra el crecimiento que exige el precio y la rentabilidad implícita del escenario base.
7. **Exigir margen según incertidumbre.** El margen requerido varía entre 15% y 40% según historia disponible, estabilidad de FCF y márgenes, beta, cobertura forward y desacuerdo entre métodos. El foso y los riesgos estructurales siguen requiriendo juicio humano.
8. **Comparar con VT/VOO.** El umbral usa el bono de EE.UU. a 10 años más una prima de renta variable de 4 puntos, acotado entre 7% y 12%. Es una tasa mínima de comparación, no un pronóstico del ETF.
9. **Documentar la decisión.** La ficha exige tesis, tres motores, tres riesgos, señales para aumentar, condiciones de invalidación y peso máximo. También permite calificar con evidencia el foso, crecimiento orgánico, ciclicidad, concentración y encaje de cartera.

## Puntaje para ordenar candidatas

| Área | Peso |
| --- | ---: |
| Calidad y ventaja económica observable | 25 |
| Salud financiera y flujo de caja | 20 |
| Crecimiento y reinversión | 15 |
| Valoración y margen de seguridad | 25 |
| Riesgo y previsibilidad observable | 10 |
| Encaje y diversificación de cartera | 5 |

Cada criterio muestra puntos, estado, valor, explicación y fuente. Cuando falta evidencia, la app entrega un rango mínimo-máximo y porcentaje de cobertura en vez de convertir el dato ausente en cero o en una aprobación. El screener profundo usa esta misma matriz para ordenar candidatas; la caída desde máximos aparece como contexto y no suma puntos.

## Reglas de interpretación

- **Candidata para investigar** significa que supera el filtro cuantitativo; todavía exige validar negocio, riesgos, datos y cartera.
- Un PER inferior a su historia inicia una investigación. No demuestra infravaloración.
- Una diferencia grande entre modelos es evidencia de incertidumbre, no una invitación a promediarlos.
- Un objetivo de analistas es una fuente externa y nunca reemplaza los supuestos propios.
- La precisión visual se limita a lo que permiten los datos. Un rango honesto es preferible a un valor justo exacto.

## Limitaciones que deben permanecer visibles

- Yahoo Finance y FMP son proveedores secundarios y pueden corregir o reclasificar cifras.
- Para Estados Unidos, los estados SEC/EDGAR deben usarse como contraste de fuente primaria cuando estén disponibles.
- Para Chile falta una integración primaria equivalente con CMF/Bolsa de Santiago para verificar estados, hechos esenciales y ajustes corporativos.
- REIT, conglomerados, recursos naturales y empresas en recuperación necesitan modelos específicos como AFFO, suma de partes, valor de activos o beneficios normalizados. Hasta implementarlos, la app debe evitar un veredicto fuerte cuando el DCF no represente bien la economía del negocio.
