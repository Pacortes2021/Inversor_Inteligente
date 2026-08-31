/* Glosario interactivo: clic en cualquier indicador → explicación simple.
   Para que cualquier persona pueda leer la app sin saber finanzas. */

const GLOSSARY = {
  mcap: { t: "Capitalización de mercado", d: "Cuánto vale toda la empresa en bolsa: precio de la acción × número de acciones. Es el 'precio de etiqueta' de comprar la compañía completa.", e: "Si una acción vale $50 y hay 1.000 M de acciones, la empresa 'cuesta' $50.000 M." },
  pe: { t: "PER / PE (precio ÷ utilidad)", d: "Cuántos años de utilidad actual estás pagando por la acción. PE 20 = pagas 20 años de ganancias. Más bajo suele ser más barato, pero compáralo siempre contra la propia historia de la empresa y su crecimiento.", e: "Acción a $100 con utilidad de $5 por acción → PE 20. Si su mediana histórica es 15, hoy está más cara que de costumbre." },
  pefwd: { t: "PE forward (a futuro)", d: "Igual que el PE, pero usando la utilidad que los analistas esperan para el próximo año en vez de la pasada. Si es mucho menor que el PE actual, el mercado espera que las ganancias crezcan.", e: "PE 30 y PE forward 15 → se espera que la utilidad casi se duplique." },
  peg: { t: "PEG (PE ÷ crecimiento)", d: "Ajusta el PE por el crecimiento esperado. Bajo 1 se considera atractivo: pagas poco por cada punto de crecimiento.", e: "PE 20 con crecimiento esperado de 20% anual → PEG 1.0." },
  ps: { t: "P/Ventas (precio ÷ ventas)", d: "Cuántas veces las ventas anuales estás pagando. Útil cuando la utilidad es volátil o negativa. Ojo: ventas no son ganancias — sirve más comparado contra su propia historia.", e: "Empresa que vale $10.000 M y vende $2.000 M al año → P/Ventas 5x." },
  pb: { t: "P/Libro (precio ÷ patrimonio contable)", d: "Compara el precio con el valor contable de la empresa (activos menos deudas). Bajo 1 significa pagar menos que su valor en libros — el terreno clásico de Graham. En empresas de marcas o software es menos informativo.", e: "P/Libro 0.8 → pagas $0.80 por cada $1 de patrimonio contable." },
  evebitda: { t: "EV/EBITDA", d: "Compara el valor total de la empresa (incluyendo su deuda) con su ganancia operativa antes de depreciación. Parecido al PE pero más justo para comparar empresas con distinta deuda.", e: "EV/EBITDA 8-12 es típico; bajo 8 suele considerarse barato para un negocio estable." },
  evrev: { t: "EV/Ventas", d: "Valor total de la empresa (con deuda incluida) dividido por sus ventas anuales. Variante del P/Ventas que no se deja engañar por la caja o deuda.", e: "" },
  grossm: { t: "Margen bruto", d: "De cada $100 vendidos, cuánto queda después del costo directo de producir. Margen bruto alto y estable (≥40%) sugiere poder de marca o ventaja competitiva: puede cobrar caro sin perder clientes.", e: "Coca-Cola vende a $100 lo que le cuesta $40 producir → margen bruto 60%." },
  opm: { t: "Margen operativo", d: "De cada $100 vendidos, cuánto queda tras pagar producción, sueldos, marketing y administración — la rentabilidad del negocio en sí, antes de impuestos e intereses.", e: "" },
  netm: { t: "Margen neto", d: "De cada $100 vendidos, cuánto llega finalmente al bolsillo del accionista después de TODO (costos, intereses, impuestos). Sobre 10% de forma consistente es señal de buen negocio.", e: "Vende $100.000 M y gana $20.000 M → margen neto 20%." },
  roe: { t: "ROE (retorno sobre patrimonio)", d: "Cuánta utilidad genera la empresa por cada $100 que los accionistas tienen invertidos. Buffett busca ≥15% sostenido: es la 'nota' de calidad del negocio. Ojo: mucha deuda puede inflarlo artificialmente.", e: "Patrimonio de $1.000 M y utilidad de $200 M → ROE 20%." },
  roa: { t: "ROA (retorno sobre activos)", d: "Cuánta utilidad genera por cada $100 de activos totales (fábricas, inventario, caja…). Como el ROE, pero sin el efecto de la deuda.", e: "" },
  roic: { t: "ROIC (retorno sobre capital invertido)", d: "La métrica de calidad favorita de los value investors modernos: cuánto gana la empresa sobre TODO el capital que usa (patrimonio + deuda − caja). Sobre 15% sostenido indica un negocio excelente.", e: "Si ROIC 25% > costo del capital 10%, cada peso reinvertido crea valor." },
  de: { t: "Deuda/Patrimonio", d: "Cuánta deuda tiene por cada peso de patrimonio propio. Bajo 1 es conservador — a Buffett le gustan las empresas que no dependen del banco para funcionar.", e: "Deuda $500 M y patrimonio $1.000 M → D/P 0.5, cómodo." },
  currentratio: { t: "Razón corriente", d: "Activos de corto plazo ÷ deudas de corto plazo. Sobre 1.2 indica que puede pagar sus cuentas del año sin apuros.", e: "" },
  beta: { t: "Beta", d: "Cuánto se mueve la acción cuando el mercado se mueve. Beta 1 = igual que el mercado; 2 = el doble de brusca; 0.5 = la mitad. Para un value investor la volatilidad no es riesgo — el riesgo es pagar de más.", e: "" },
  eps: { t: "EPS / UPA (utilidad por acción)", d: "La ganancia del año dividida entre todas las acciones. Es el 'sueldo' que genera cada acción tuya. Que crezca años tras año es de las mejores señales que existen.", e: "Utilidad $10.000 M ÷ 2.000 M acciones → EPS $5." },
  bvps: { t: "Valor libro por acción", d: "El patrimonio contable dividido por acción: lo que 'quedaría' por acción si se liquidara todo a valor contable.", e: "" },
  revgrowth: { t: "Crecimiento de ingresos (yoy)", d: "Cuánto crecieron las ventas versus el mismo período del año anterior.", e: "" },
  fcf: { t: "FCF (flujo de caja libre)", d: "La plata REAL que genera el negocio después de pagar todas sus inversiones. La utilidad contable puede maquillarse; la caja no. Es la base del DCF y la métrica favorita de Buffett ('owner earnings').", e: "Genera $30.000 M operando y gasta $10.000 M en inversiones → FCF $20.000 M." },
  fcfyield: { t: "FCF yield (rendimiento de caja)", d: "El FCF anual como porcentaje del precio total de la empresa. Es como el 'interés' que te paga el negocio en caja real. Sobre 4-5% empieza a ser interesante; sobre 8% es raro y valioso.", e: "FCF de $8.000 M sobre capitalización de $100.000 M → 8% de yield." },
  divyield: { t: "Rendimiento del dividendo", d: "Cuánto te paga en dividendos al año como % del precio de hoy. Un yield muy alto puede ser trampa: revisa que el payout sea sostenible.", e: "Acción a $100 que paga $3 al año → yield 3%." },
  payout: { t: "Payout (% de utilidad repartida)", d: "Qué parte de la ganancia se reparte como dividendo. Bajo 60% deja espacio para crecer y aguantar años malos; sobre 80-90% el dividendo puede peligrar. Mejor aún medirlo sobre FCF.", e: "" },
  mos: { t: "Margen de seguridad", d: "El concepto central de Graham y Buffett: la distancia entre lo que VALE la empresa (valor intrínseco estimado) y lo que CUESTA hoy. Comprar con ≥25% de descuento te protege de errores de cálculo y mala suerte.", e: "Valor estimado $130, precio $100 → margen de seguridad +30%: hay colchón." },
  consenso: { t: "Valor intrínseco (consenso ponderado)", d: "La estimación canónica de la plataforma: promedia ponderadamente los modelos de valoración activos (DCF, PE mediano, Graham, etc.) para obtener una cifra sólida del valor real de la acción.", e: "Si el consenso da $150 y la acción cotiza a $120, hay un margen de seguridad del +25%." },
  buyprice: { t: "Precio de compra aceptable (MoS 25%)", d: "El precio al que un inversor conservador estilo Warren Buffett buscaría comprar. Aplica un margen de seguridad estricto del 25% sobre el valor intrínseco de consenso (Consenso ÷ 1.25) para protegerse contra imprevistos.", e: "Si el valor justo es $100, el precio de compra aceptable es $80." },
  dcf: { t: "DCF (flujo de caja descontado)", d: "Proyecta la capacidad real de generar efectivo libre (FCF) a 10 años y los trae a valor presente con el costo de capital (WACC). Es el modelo más directo para medir la generación de caja futura.", e: "" },
  reversedcf: { t: "Reverse DCF (DCF inverso)", d: "En vez de adivinar el crecimiento para obtener un valor, pregunta: ¿qué crecimiento necesita la empresa para justificar su precio ACTUAL? Si la respuesta es irrealista, está cara — sin discutir supuestos.", e: "Si el precio exige 25% anual por 10 años y la empresa crece al 8%, el mercado está soñando." },
  graham: { t: "Número de Graham / Graham Revisado", d: "Fórmula clásica de Benjamin Graham (maestro de Buffett). La versión revisada usa utilidades y tasas de bonos ($V = EPS \times (8.5 + 2g) \times \frac{4.4}{Y}$). El Número estricto usa activos en libros $\sqrt{22.5 \times EPS \times BVPS}$.", e: "El Número estricto da muy bajo en empresas modernas de marcas o software con pocos activos contables." },
  reversion: { t: "Reversión al PE mediano", d: "Estima el precio si la acción volviera a cotizar a su múltiplo P/E mediano histórico de los últimos 15 años (EPS actual × P/E Mediano). Capado a 30x máximo.", e: "Si históricamente cotizó a 20x y hoy está a 15x, proyecta la vuelta a 20x." },
  peg: { t: "Valor Justo Peter Lynch (PEG 1.0)", d: "Formulado por Peter Lynch para empresas en crecimiento ($V = EPS \times (G + Dividend Yield)$). Diseñado para empresas 'growth' (15%+). En empresas defensivas de bajo crecimiento resulta ultra-conservador.", e: "" },
  epv: { t: "EPV Greenwald (cero crecimiento)", d: "¿Cuánto vale la empresa si NUNCA más crece? Capitaliza su ganancia operativa normalizada a perpetuidad. Es el ancla más conservadora: si el precio está bajo el EPV, el crecimiento te lo regalan.", e: "Si EPV = $80 y el precio es $60, pagas menos que un negocio congelado." },
  ey: { t: "Earnings yield (rendimiento de utilidades)", d: "El PE al revés: utilidad anual como % del precio (PE 20 → 5%). Permite comparar la acción contra un bono: si rinde menos que el bono del Tesoro, estás pagando por crecimiento futuro.", e: "" },
  cagr: { t: "CAGR (crecimiento anual compuesto)", d: "El ritmo de crecimiento 'parejo' equivalente entre dos años, como si cada año creciera lo mismo. Es la forma correcta de comparar crecimiento entre períodos y empresas.", e: "De $100 a $200 en 5 años → CAGR 14.9% anual (no 20%)." },
  sma: { t: "SMA (media móvil simple)", d: "El precio promedio de los últimos N días. La SMA 200 marca la tendencia de largo plazo: precio sobre ella = tendencia alcista. Para un value investor es contexto, no señal de compra.", e: "" },
  drawdown: { t: "vs máximo 52 semanas", d: "Cuánto ha caído la acción desde su punto más alto del último año. Las grandes oportunidades de Buffett aparecen cuando empresas excelentes caen 30-50% por pánico pasajero.", e: "" },
  alpha: { t: "Alfa (vs S&P 500)", d: "Tu retorno menos el del índice en el mismo período. Alfa positivo = le ganas al mercado. Si es negativo de forma persistente, un ETF indexado te haría más rico con menos esfuerzo — el propio Buffett lo recomienda.", e: "Tu acción +15%, el S&P +10% → alfa +5%." },
  score: { t: "Puntaje de valor (0-100)", d: "Nota compuesta del screener rápido: valoración (45%), calidad del negocio (30%), salud financiera (15%) y castigo en precio (10%). Sobre 65 = candidata interesante para investigar — no es recomendación de compra.", e: "" },
  banda: { t: "Mediana y rango p25-p75", d: "La línea dorada es la mediana histórica (la mitad del tiempo cotizó más caro, la mitad más barato). La banda gris cubre el 50% central del tiempo. Precio bajo la banda = territorio históricamente barato.", e: "" },
  ttm: { t: "TTM (últimos 12 meses)", d: "'Trailing Twelve Months': el dato acumulado de los últimos 4 trimestres, más actual que el último año fiscal cerrado.", e: "" },
  streak: { t: "Racha de dividendos", d: "Años consecutivos pagando (o subiendo) el dividendo sin fallar. 25+ años subiéndolo = 'aristócrata del dividendo'. Una racha larga es promesa implícita de la gerencia.", e: "" },
  payoutfcf: { t: "Payout sobre FCF", d: "El dividendo total pagado como % del flujo de caja libre — más honesto que medirlo sobre utilidad contable. Bajo 60%: sólido. Sobre 80%: el dividendo depende de que nada salga mal.", e: "" },
  moat: { t: "Moat (foso competitivo)", d: "La ventaja que impide que la competencia erosione las ganancias: marca, costos bajos, efecto de red, costos de cambio, patentes o escala. Para Buffett es EL factor: un castillo vale lo que su foso.", e: "" },
};

/* ------------------------------------------------------------- popover */
export function termify(label, key) {
  return GLOSSARY[key] ? `<span class="term" data-term="${key}">${label} <span class="term-icon">ⓘ</span></span>` : label;
}

function getPop() {
  let pop = document.getElementById("glossary-pop");
  if (!pop && document.body) {
    pop = document.createElement("div");
    pop.id = "glossary-pop";
    pop.className = "glossary-pop hidden";
    document.body.appendChild(pop);
  }
  return pop;
}

function show(el, key) {
  const g = GLOSSARY[key];
  if (!g) return;
  const pop = getPop();
  if (!pop) return;
  pop.innerHTML = `<h4>${g.t}</h4><p>${g.d}</p>` +
    (g.e ? `<p class="gp-example">Ej: ${g.e}</p>` : "") +
    `<span class="gp-close">✕</span>`;
  pop.classList.remove("hidden");
  const r = el.getBoundingClientRect();
  const pw = 340;
  let left = Math.min(r.left, window.innerWidth - pw - 16);
  let top = r.bottom + 8;
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = top + "px";
  requestAnimationFrame(() => {
    const ph = pop.offsetHeight;
    if (top + ph > window.innerHeight - 10 && r.top - ph - 8 > 0) {
      pop.style.top = (r.top - ph - 8) + "px";
    }
  });
}

document.addEventListener("click", e => {
  const t = e.target.closest("[data-term]");
  const pop = document.getElementById("glossary-pop");
  if (t) {
    e.stopPropagation();
    show(t, t.dataset.term);
  } else if (pop && !e.target.closest("#glossary-pop")) {
    pop.classList.add("hidden");
  }
  if (pop && e.target.classList && e.target.classList.contains("gp-close")) {
    pop.classList.add("hidden");
  }
}, true);

document.addEventListener("keydown", e => {
  const pop = document.getElementById("glossary-pop");
  if (e.key === "Escape" && pop) pop.classList.add("hidden");
});

window.addEventListener("scroll", () => {
  const pop = document.getElementById("glossary-pop");
  if (pop) pop.classList.add("hidden");
}, { passive: true });
