"""Banderas de calidad de datos: la app te avisa cuándo dudar de ella."""

from datetime import datetime

from .valuation import _ok


def build_warnings(info, annuals, valuation, pe_pairs, edgar_hist):
    """Lista de avisos (strings) sobre datos que pueden distorsionar el veredicto."""
    w = []

    # 1. FCF base desviado de su promedio de 3 años (caída > 35% o salto > 150%)
    base = (valuation.get("dcfInputs") or {}).get("baseFcf")
    fcfs = [a["fcf"] for a in annuals if _ok(a.get("fcf"))][-3:]
    if _ok(base) and len(fcfs) == 3:
        avg = sum(fcfs) / 3
        if avg > 0:
            dev = (base / avg - 1) * 100
            if dev < -35:
                w.append(f"El FCF base del DCF está {abs(dev):.0f}% bajo su promedio de 3 años "
                         "— puede haber un cargo puntual y el DCF subestimaría el valor.")
            elif dev > 150:
                w.append(f"El FCF base del DCF está {dev:.0f}% sobre su promedio de 3 años "
                         "— puede ser transitorio y el DCF sobreestimaría el valor.")

    # 2. Salto/caída brusca de utilidad (> 80% de cambio interanual)
    nis = [a["netIncome"] for a in annuals if _ok(a.get("netIncome"))]
    if len(nis) >= 2 and nis[-2] > 0:
        chg = (nis[-1] / nis[-2] - 1) * 100
        if abs(chg) > 80:
            direction = "saltó" if chg > 0 else "cayó"
            w.append(f"La utilidad neta {direction} {abs(chg):.0f}% el último año — puede haber "
                     "partidas extraordinarias; interpreta el PE y el ROE con cautela.")

    # 3. Patrimonio negativo → P/Libro y ROE no interpretables
    eqs = [a["equity"] for a in annuals if a.get("equity") is not None]
    if eqs and eqs[-1] is not None and eqs[-1] < 0:
        w.append("Patrimonio contable negativo (habitual tras recompras masivas): "
                 "P/Libro, ROE y el Número de Graham no son interpretables aquí.")

    # 4. Historial de PE corto (< 2 años)
    if pe_pairs:
        years_span = (pe_pairs[-1][0] - pe_pairs[0][0]) / (365.25 * 24 * 3600 * 1000)
        if years_span < 2:
            w.append(f"El historial de PE cubre solo ~{years_span:.0f} años — la mediana "
                     "histórica y la reversión son menos confiables.")
    elif _ok(info.get("trailingPE")):
        pe = info.get("trailingPE")
        if pe > 150:
            w.append(f"PE de {pe:.0f}x probablemente no es significativo — EPS puede ser cercano a cero o haber un cargo puntual extraordinario.")
        w.append("Sin historial de PE construible (EPS histórico no disponible) — "
                 "no hay comparación contra la propia historia.")

    # 5. Discrepancia real (> 15%) entre Yahoo y SEC EDGAR
    if edgar_hist and "revenue" in edgar_hist:
        current_yr = datetime.now().year
        yahoo_rev = {a["year"]: a["revenue"] for a in annuals
                     if _ok(a.get("revenue")) and a.get("source") != "edgar" and a.get("year", 0) <= current_yr}
        for ystr, (_, val) in sorted(edgar_hist["revenue"].items(), reverse=True):
            try:
                y = int(ystr)
            except ValueError:
                continue
            if y <= current_yr and y in yahoo_rev and yahoo_rev[y] and _ok(val):
                v_edgar = val
                v_yahoo = yahoo_rev[y]
                if abs(v_edgar / (v_yahoo * 1000) - 1) < 0.15:
                    v_yahoo *= 1000
                elif abs((v_edgar * 1000) / v_yahoo - 1) < 0.15:
                    v_edgar *= 1000

                diff = abs(v_edgar / v_yahoo - 1) * 100
                if diff > 15:
                    w.append(f"Los ingresos {y} difieren {diff:.0f}% entre Yahoo y la SEC "
                             "— revisa el 10-K antes de confiar en los ratios de ese período.")
                break

    # 6. P/E saneado automáticamente por la app
    if info.get("_peSanitized"):
        raw_pe = info.get("_peRawOriginal")
        cur_pe = info.get("trailingPE")
        if raw_pe and cur_pe:
            w.append(f"El P/E trailing sin ajustar de Yahoo ({raw_pe:.1f}x) presentó una distorsión contable por cargos atípicos. "
                     f"La app lo auditó y normalizó a {cur_pe:.1f}x según la utilidad neta TTM real.")

    # 7. Valoración: margen de seguridad negativo significativo
    mos = valuation.get("marginOfSafety")
    consensus_price = valuation.get("consensus")
    if _ok(mos) and _ok(consensus_price):
        if mos < -20:
            w.append(f"El precio actual supera en {abs(mos):.0f}% el valor intrínseco consensuado "
                     f"(${consensus_price:.0f}) — la acción aparenta estar sobrevalorada según los modelos actuales.")
        elif mos > 30:
            w.append(f"El precio actual cotiza con un descuento de {mos:.0f}% sobre el valor intrínseco "
                     f"(${consensus_price:.0f}) — puede haber una oportunidad de compra.")

    # 8. PE actual en extremo superior del rango histórico
    if pe_pairs and len(pe_pairs) > 20:
        vals = [p[1] for p in pe_pairs if _ok(p[1]) and 0 < p[1] < 200]
        if vals:
            sorted_vals = sorted(vals)
            p75 = sorted_vals[int(len(sorted_vals) * 0.75)]
            p90 = sorted_vals[int(len(sorted_vals) * 0.90)]
            current_pe = vals[-1] if vals else None
            if _ok(current_pe):
                if current_pe > p90:
                    w.append(f"El P/E actual ({current_pe:.1f}x) está en el percentil 90 de su historia — "
                             "históricamente ha precedido retornos inferiores al promedio.")
                elif current_pe < sorted_vals[int(len(sorted_vals) * 0.10)]:
                    w.append(f"El P/E actual ({current_pe:.1f}x) está en el percentil 10 de su historia — "
                             "podría reflejar pesimismo excesivo del mercado.")

    return w


def pe_is_reliable(info, annuals):
    """Retorna True si el PE es significativo, False si trailingPE es None, > 150 o < 0."""
    pe = info.get("trailingPE") if isinstance(info, dict) else None
    if not _ok(pe) or pe > 150 or pe < 0:
        return False
    return True

