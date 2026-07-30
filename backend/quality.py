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

    return w


def pe_is_reliable(info, annuals):
    """Retorna True si el PE es significativo, False si trailingPE es None, > 150 o < 0."""
    pe = info.get("trailingPE") if isinstance(info, dict) else None
    if not _ok(pe) or pe > 150 or pe < 0:
        return False
    return True

