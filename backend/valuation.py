"""Modelos de valoración intrínseca y scorecard estilo Buffett."""

import math


def _ok(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


# ----------------------------------------------------------------------- DCF

def dcf_fair_value(base_fcf, shares, net_cash=0.0, growth=0.08,
                   discount=0.10, terminal=0.025, years=10, fade_start=6,
                   forward_fcf=None):
    """DCF de flujo de caja libre. Si `forward_fcf` trae FCFs explícitos
    (consenso de analistas) se usan para los primeros años; después se
    continúa con el crecimiento que implican, decayendo linealmente hacia
    la tasa terminal. Sin `forward_fcf` todo crece a `growth` con el fade
    clásico desde fade_start. Devuelve valor justo por acción."""
    if not _ok(base_fcf) or base_fcf <= 0 or not _ok(shares) or shares <= 0:
        return None
    if discount <= terminal:
        return None
    fwd = [f for f in (forward_fcf or []) if _ok(f) and f > 0][:years]
    n_fwd = len(fwd)
    fcf = base_fcf
    g_after = growth
    fade_origin = max(fade_start, n_fwd + 1) if n_fwd else fade_start
    pv_sum = 0.0
    for yr in range(1, years + 1):
        if yr <= n_fwd:
            if yr > 1 and fwd[yr - 2] > 0:
                g_after = fwd[yr - 1] / fwd[yr - 2] - 1
            elif fcf > 0:
                g_after = fwd[yr - 1] / fcf - 1
            g_after = min(max(g_after, -0.25), 0.75)
            fcf = fwd[yr - 1]
        else:
            if yr >= fade_origin:
                frac = (yr - fade_origin + 1) / (years - fade_origin + 1)
                g = g_after + (terminal - g_after) * frac
            else:
                g = g_after
            fcf *= (1 + g)
        pv_sum += fcf / (1 + discount) ** yr
    tv = fcf * (1 + terminal) / (discount - terminal)
    pv_sum += tv / (1 + discount) ** years
    equity_value = pv_sum + (net_cash or 0.0)
    return equity_value / shares


def implied_growth(price, base_fcf, shares, net_cash=0.0,
                   discount=0.10, terminal=0.025, years=10, fade_start=6,
                   forward_fcf=None):
    """Reverse DCF: crecimiento de FCF que el precio actual está descontando.
    Se resuelve por bisección; acotado a [-20%, +60%]."""
    if not _ok(price) or price <= 0 or not _ok(base_fcf) or base_fcf <= 0 \
            or not _ok(shares) or shares <= 0:
        return None
    lo, hi = -0.20, 0.60

    def diff(g):
        fv = dcf_fair_value(
            base_fcf, shares, net_cash, g, discount, terminal, years,
            fade_start, forward_fcf=forward_fcf,
        )
        return None if fv is None else fv - price

    flo, fhi = diff(lo), diff(hi)
    if flo is None or fhi is None:
        return None
    if flo >= 0:
        return lo   # el precio descuenta contracción de -20% o peor
    if fhi <= 0:
        return hi   # el precio exige más de +60% anual
    for _ in range(60):
        mid = (lo + hi) / 2
        fm = diff(mid)
        if fm is None:
            return None
        if fm >= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def implied_discount_rate(price, base_fcf, shares, net_cash=0.0,
                          growth=0.08, terminal=0.025, years=10,
                          fade_start=6, forward_fcf=None):
    """Rentabilidad anual implícita en el precio para un escenario de FCF.

    Resuelve la tasa de descuento que iguala el DCF al precio observado. Es
    más útil para comparar alternativas que presentar un valor justo aislado.
    Los límites indican que el resultado queda fuera de un rango razonable,
    no que la rentabilidad esté garantizada.
    """
    if not _ok(price) or price <= 0 or not _ok(base_fcf) or base_fcf <= 0 \
            or not _ok(shares) or shares <= 0:
        return None
    lo = max(terminal + 0.0025, 0.03)
    hi = 0.40

    def diff(rate):
        value = dcf_fair_value(
            base_fcf, shares, net_cash, growth, rate, terminal, years,
            fade_start, forward_fcf=forward_fcf,
        )
        return None if value is None else value - price

    flo, fhi = diff(lo), diff(hi)
    if flo is None or fhi is None:
        return None
    if flo <= 0:
        return lo
    if fhi >= 0:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if diff(mid) >= 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _median(values):
    vals = sorted(v for v in values if _ok(v))
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def _relative_dispersion(values):
    """Desviación media absoluta relativa; robusta ante muestras pequeñas."""
    vals = [v for v in values if _ok(v)]
    center = _median(vals)
    if len(vals) < 3 or not _ok(center) or abs(center) < 1e-9:
        return None
    return _median([abs(v - center) for v in vals]) / abs(center)


def assess_uncertainty(info, annuals, model_values, fcf_source="historico"):
    """Clasifica incertidumbre observable y deriva el margen mínimo exigido.

    No intenta medir el foso competitivo. Esa parte requiere una tesis humana;
    por eso la salida siempre marca la revisión cualitativa como pendiente.
    """
    points = 0
    reasons = []
    business_text = f"{info.get('sector') or ''} {info.get('industry') or ''}".lower()
    cyclical_terms = ("oil", "gas", "mining", "steel", "copper", "gold",
                      "commodity", "paper", "forest products")
    if any(term in business_text for term in cyclical_terms):
        points += 15
        reasons.append("negocio cíclico: requiere beneficios de ciclo medio")
    years = {a.get("year") for a in annuals if a.get("year") is not None}
    if len(years) < 3:
        points += 30
        reasons.append("menos de 3 ejercicios comparables")
    elif len(years) < 5:
        points += 18
        reasons.append("historia financiera menor a 5 años")

    recent_fcfs = [a.get("fcf") for a in annuals[-5:] if _ok(a.get("fcf"))]
    positive_fcfs = sum(1 for value in recent_fcfs if value > 0)
    if len(recent_fcfs) < 3:
        points += 15
        reasons.append("cobertura limitada de flujo de caja")
    elif positive_fcfs < len(recent_fcfs):
        points += 18
        reasons.append("flujo de caja negativo en años recientes")
    fcf_dispersion = _relative_dispersion(recent_fcfs)
    if _ok(fcf_dispersion) and fcf_dispersion > 0.45:
        points += 15
        reasons.append("flujo de caja volátil")

    margins = [a.get("opMargin") for a in annuals[-5:] if _ok(a.get("opMargin"))]
    margin_dispersion = _relative_dispersion(margins)
    if _ok(margin_dispersion) and margin_dispersion > 0.25:
        points += 10
        reasons.append("márgenes poco estables")

    beta = info.get("beta")
    if not _ok(beta):
        points += 5
        reasons.append("beta no disponible")
    elif beta > 1.5:
        points += 10
        reasons.append("sensibilidad de mercado elevada")

    if fcf_source != "fmp":
        points += 7
        reasons.append("proyección basada en historia, sin consenso forward")

    spread = None
    clean_models = [v for v in model_values if _ok(v) and v > 0]
    if len(clean_models) >= 2:
        med = _median(clean_models)
        spread = (max(clean_models) - min(clean_models)) / med if med else None
        if _ok(spread) and spread > 0.75:
            points += 12
            reasons.append("gran desacuerdo entre métodos de contraste")
        elif _ok(spread) and spread > 0.40:
            points += 7
            reasons.append("desacuerdo relevante entre métodos")

    points = min(points, 100)
    if points <= 15:
        level, label, required = "low", "Baja", 15
    elif points <= 55:
        level, label, required = "medium", "Media", 25
    elif points <= 80:
        level, label, required = "high", "Alta", 35
    else:
        level, label, required = "very_high", "Muy alta", 40
    return {
        "score": points,
        "level": level,
        "label": label,
        "requiredMarginPct": required,
        "reasons": reasons[:5],
        "modelSpreadPct": round(spread * 100, 1) if _ok(spread) else None,
        "qualitativeReviewRequired": True,
    }


def graham_number(eps, bvps, fcf_per_share=None):
    """Número de Graham: sqrt(22.5 · EPS · BVPS).
    Si BVPS es negativo (recompras masivas de acciones), usa FCF/acción si está disponible."""
    if _ok(eps) and eps > 0:
        if _ok(bvps) and bvps > 0:
            return math.sqrt(22.5 * eps * bvps)
        if _ok(fcf_per_share) and fcf_per_share > 0:
            return math.sqrt(22.5 * eps * fcf_per_share)
    return None


def graham_intrinsic_value(eps, growth, bond10y=None):
    """Fórmula de Benjamin Graham revisada: (EPS * (8.5 + 2g) * 4.4) / Y."""
    if not _ok(eps) or eps <= 0 or not _ok(growth) or growth < 0:
        return None
    y = bond10y if _ok(bond10y) else 4.2
    if y <= 0:
        return None
    g = growth * 100  # pasar a porcentaje
    return (eps * (8.5 + 2 * g) * 4.4) / y


def dividend_discount_inputs(info, annuals):
    """Obtiene dividendo y crecimiento sostenible usados por el DDM."""
    dps = info.get("trailingAnnualDividendRate") or info.get("dividendRate")
    if not _ok(dps) or dps <= 0:
        dps_list = [a["dividendPS"] for a in annuals if _ok(a.get("dividendPS")) and a["dividendPS"] > 0]
        dps = dps_list[-1] if dps_list else None
    if not _ok(dps) or dps <= 0:
        return None, None

    roe = info.get("returnOnEquity") or 0.12
    if _ok(roe) and roe > 1.0:
        roe /= 100.0
    payout = info.get("payoutRatio") or 0.40
    # Yahoo's payoutRatio is already a decimal (0.40 = 40%). Cap at 1.0 for DDM
    # (payout > 1 = unsustainable dividend, clamp to 0.95 for G-Growth calc to still work)
    if _ok(payout):
        payout = min(abs(payout), 0.95)  # clamp, never divide – it's already decimal

    g = max(0.01, min(0.06, roe * (1 - payout))) if (_ok(roe) and _ok(payout) and payout < 1) else 0.03

    return dps, g


def dividend_discount_model(info, annuals, discount=0.10):
    """Modelo de Descuento de Dividendos (Gordon Growth) para financieras."""
    dps, g = dividend_discount_inputs(info, annuals)
    if not _ok(dps) or not _ok(g):
        return None

    if discount <= g:
        return None
    return dps * (1 + g) / (discount - g)


def peter_lynch_fair_value(eps, growth, div_yield=0.0):
    """Valor Justo de Peter Lynch: EPS * (G + Dividend Yield) para PEG = 1.0.
    Sólo aplica a empresas de crecimiento medio-alto. Se descarta cuando la
    tasa de crecimiento estimada < 5% anual (empresas maduras/defensivas) ya que
    el modelo PEG produce valores absurdamente bajos e inútiles."""
    if not _ok(eps) or eps <= 0 or not _ok(growth) or growth <= 0:
        return None
    # Para empresas con crecimiento < 5%, el modelo PEG no aplica:
    # Lynch lo diseñó para growth stocks, no para utilities o consumer staples maduros.
    if growth < 0.05:
        return None
    g_pct = growth * 100.0
    yield_pct = div_yield if _ok(div_yield) else 0.0
    fair_pe = min(g_pct + yield_pct, 40.0)
    return eps * fair_pe



def epv_greenwald(info, annuals, discount=0.10, tax_rate=0.21):
    """Earnings Power Value: valor asumiendo CERO crecimiento.
    EBIT normalizado (margen operativo mediano hasta 10 años) después de
    impuestos, capitalizado a perpetuidad, más caja neta."""
    margins = [a["opMargin"] for a in annuals[-10:] if _ok(a.get("opMargin"))]
    rev = info.get("totalRevenue")
    if not _ok(rev):
        revs = [a["revenue"] for a in annuals if _ok(a.get("revenue"))]
        rev = revs[-1] if revs else None
    shares = info.get("sharesOutstanding")
    if len(margins) < 3 or not _ok(rev) or not _ok(shares) or shares <= 0:
        return None
    margin = sorted(margins)[len(margins) // 2] / 100
    if margin <= 0:
        return None
    nopat = rev * margin * (1 - tax_rate)
    net_cash = (info.get("totalCash") or 0) - (info.get("totalDebt") or 0)
    fv = (nopat / discount + net_cash) / shares
    return fv if fv > 0 else None


MAX_TARGET_PE = 30.0  # disciplina: no pagar múltiplos de era de euforia


def pe_reversion(eps, pe_median):
    """Precio objetivo si el PE vuelve a su mediana histórica (capada a 30x)."""
    if not _ok(eps) or not _ok(pe_median) or eps <= 0 or pe_median <= 0:
        return None
    return eps * min(pe_median, MAX_TARGET_PE)


def estimate_wacc(info, bond10y=None, erp=0.05):
    """Estima el Costo Promedio Ponderado de Capital (WACC) con modelo CAPM.
    r_e = Rf + beta * ERP. r_d = Rf + 1.5%. Acotado a [6.0%, 15.0%]."""
    rf = (bond10y / 100.0) if _ok(bond10y) else 0.042
    beta = info.get("beta")
    if not _ok(beta) or beta <= 0:
        beta = 1.0
    r_e = rf + beta * erp

    debt = info.get("totalDebt") or 0
    mc = info.get("marketCap") or 0

    if mc <= 0 or debt <= 0:
        return min(max(r_e, 0.06), 0.15)

    v = mc + debt
    w_e = mc / v
    w_d = debt / v
    r_d = rf + 0.015
    tax = 0.21

    wacc = w_e * r_e + w_d * r_d * (1 - tax)
    return min(max(wacc, 0.06), 0.15)


def estimate_growth(annuals, info):
    """Crecimiento base para el DCF: CAGR histórico de FCF/ingresos mezclado
    con el crecimiento esperado que reporta Yahoo, acotado a [2%, 20%]."""
    candidates = []
    for key in ("fcf", "revenue"):
        vals = [a[key] for a in annuals if _ok(a.get(key)) and a[key] > 0]
        if len(vals) >= 3:
            n = len(vals) - 1
            cagr = (vals[-1] / vals[0]) ** (1 / n) - 1
            if math.isfinite(cagr):
                candidates.append(cagr)
    for key in ("earningsGrowth", "revenueGrowth"):
        v = info.get(key)
        if _ok(v) and -0.5 < v < 1.5:
            candidates.append(v)
    if not candidates:
        return 0.08
    g = sorted(candidates)[len(candidates) // 2]  # mediana
    return min(max(g, 0.02), 0.20)


def build_forward_fcf(base_fcf, annuals, fmp_rows):
    """Convierte las estimaciones de consenso de FMP (net income forward)
    en FCFs proyectados: FCF_i = NI_i × ratio FCF/NI histórico (mediana de
    los últimos 5 años). Solo usa ejercicios posteriores al último anual
    reportado (FMP mezcla histórico con forward). Devuelve (years, fcfs)."""
    if not fmp_rows:
        return None, None
    pairs = [(a["fcf"], a.get("netIncome")) for a in annuals
             if _ok(a.get("fcf")) and a["fcf"] > 0 and _ok(a.get("netIncome")) and a["netIncome"] > 0]
    if len(pairs) < 3:
        return None, None
    ratios = sorted(f / ni for f, ni in pairs[-5:])
    ratio = ratios[len(ratios) // 2]
    if not (0 < ratio < 3):
        return None, None
    hist_years = [a.get("year") for a in annuals if _ok(a.get("year"))]
    min_forward = max([int(y) for y in hist_years] or [0])
    if min_forward <= 0:
        min_forward = _now_year()  # fallback: solo ejercicios estrictamente futuros
    years, fcfs = [], []
    for row in fmp_rows:
        try:
            y = int(row.get("year"))
        except (TypeError, ValueError):
            continue
        ni = row.get("netIncomeAvg")
        if y > min_forward and _ok(ni) and ni > 0:
            f = ni * ratio
            if f > 0:
                years.append(str(y))
                fcfs.append(round(f, 2))
    if len(fcfs) < 2:
        return None, None
    return years, fcfs


def _now_year():
    import datetime
    return datetime.date.today().year


def build_valuation(price, info, annuals, pe_stats, bond10y, fmp_rows=None):
    """Arma el bloque de valoración completo, con insumos para recalcular
    el DCF en el navegador (sliders)."""
    currency_mismatch = bool(info.get("_currencyMismatch"))
    shares = info.get("sharesOutstanding") or (annuals[-1].get("sharesOut") if annuals else None)
    eps = info.get("trailingEps") or (annuals[-1].get("eps") if annuals else None)
    bvps = info.get("bookValue") or (annuals[-1].get("bvps") if annuals else (annuals[-1].get("equity") / shares if (annuals and shares and annuals[-1].get("equity")) else None))

    # FCF base normalizado (owner earnings): mediana entre el TTM de Yahoo,
    # el último anual y el promedio de 3 años, para suavizar cargos puntuales
    cands = []
    v = info.get("freeCashflow")
    annual_fcfs = [a["fcf"] for a in annuals if _ok(a.get("fcf"))]
    latest_reported_fcf = v if _ok(v) else (annual_fcfs[-1] if annual_fcfs else None)
    # Un DCF de FCF no es interpretable mientras el flujo más reciente sea no
    # positivo. No se deben saltar pérdidas recientes para rescatar años antiguos.
    if _ok(latest_reported_fcf) and latest_reported_fcf > 0:
        cands.append(latest_reported_fcf)
        if annual_fcfs and annual_fcfs[-1] > 0 and annual_fcfs[-1] != latest_reported_fcf:
            cands.append(annual_fcfs[-1])
        recent_fcfs = annual_fcfs[-3:]
        if len(recent_fcfs) == 3:
            avg_recent = sum(recent_fcfs) / 3
            if avg_recent > 0:
                cands.append(avg_recent)
    base_fcf = sorted(cands)[len(cands) // 2] if cands else None

    cash = info.get("totalCash") or (annuals[-1].get("cash") if annuals else 0) or 0
    debt = info.get("totalDebt") or (annuals[-1].get("totalDebt") if annuals else 0) or 0
    # Use (x or 0) so debt-free companies (debt=None) correctly compute net_cash = cash
    net_cash = (_ok(cash) and (cash or 0) or 0) - (_ok(debt) and (debt or 0) or 0)


    fcf_per_share = (base_fcf / shares) if (_ok(base_fcf) and _ok(shares) and shares > 0) else None

    growth = estimate_growth(annuals, info)
    wacc_est = estimate_wacc(info, bond10y)
    discount = round(wacc_est, 4)
    terminal = 0.025

    # Flujos forward: consenso de analistas (FMP) si hay clave y cobertura;
    # si no, proyección propia con el CAGR histórico (fcfSource "historico").
    fwd_years, fwd_fcfs = build_forward_fcf(base_fcf, annuals, fmp_rows)
    fcf_source = "fmp" if fwd_fcfs else "historico"

    dcf = dcf_fair_value(base_fcf, shares, net_cash, growth, discount, terminal,
                         forward_fcf=fwd_fcfs)
    graham = graham_number(eps, bvps, fcf_per_share=fcf_per_share)
    graham_int = graham_intrinsic_value(eps, growth, bond10y)
    pe_med = pe_stats["median"] if pe_stats else None
    reversion = pe_reversion(eps, pe_med)

    earnings_yield = (eps / price * 100) if (_ok(eps) and _ok(price) and price > 0) else None

    # El FCF contable de bancos y aseguradoras no refleja su economía:
    # para financieras el DCF de FCF queda excluido y se usa DDM.
    sector = (info.get("sector") or "")
    industry = (info.get("industry") or "")
    is_financial = "Financial" in sector
    is_reit = "REIT" in industry.upper()

    epv = epv_greenwald(info, annuals, discount) if not is_financial else None
    # EPV (cero crecimiento) castiga injustamente a empresas de hypergrowth:
    # se excluye cuando el crecimiento estimado supera 15% anual.
    if growth > 0.15:
        epv = None
    ddm = dividend_discount_model(info, annuals, discount) if is_financial else None
    div_yield_val = info.get("trailingAnnualDividendYield") or info.get("dividendYield")
    # Yahoo returns yield as decimal (0.033 = 3.3%). Only multiply by 100 if < 1.5
    # (threshold chosen to handle REITs/MLPs that can yield 15-30% as decimals up to 0.30)
    if _ok(div_yield_val) and 0 < div_yield_val < 1.5:
        div_yield_val *= 100.0
    lynch_fv = peter_lynch_fair_value(eps, growth, div_yield=div_yield_val)

    # Sin conversión verificable no se comparan flujos o beneficios contables
    # con un precio expresado en otra moneda. Es preferible omitir un veredicto
    # antes que mostrar una valoración numéricamente plausible pero inválida.
    if currency_mismatch:
        dcf = graham = graham_int = reversion = epv = ddm = lynch_fv = None
        earnings_yield = None


    models = []
    if dcf and not is_financial:
        models.append({"id": "dcf", "name": "Flujo de caja descontado (DCF)", "fair": dcf})
    if ddm and is_financial:
        models.append({"id": "ddm", "name": "Modelo Descuento Dividendos (DDM)", "fair": ddm})
    if reversion:
        pe_target = round(min(pe_med, MAX_TARGET_PE), 1)
        label = f"Reversión al PE mediano ({pe_target}x)"
        if pe_med > MAX_TARGET_PE:
            label = f"Reversión al PE mediano (capado a {pe_target}x)"
        models.append({"id": "reversion", "name": label, "fair": reversion})
    if lynch_fv:
        models.append({"id": "peter_lynch", "name": "Valor Justo Peter Lynch (PEG 1.0)", "fair": lynch_fv})
    if epv:
        models.append({"id": "epv", "name": "EPV Greenwald (cero crecimiento)", "fair": epv})
    if graham_int:
        models.append({"id": "graham_intrinsic", "name": "Valor Intrínseco de Graham (rev.)", "fair": graham_int})
    if graham:
        models.append({"id": "graham", "name": "Número de Graham", "fair": graham})

    # Un método apropiado dirige la decisión. Los demás sirven para contrastar
    # supuestos y detectar desacuerdos; no se promedian métodos incompatibles.
    model_ids = {m["id"] for m in models}
    applicability_warnings = []
    if is_reit:
        primary_id = None
        applicability_warnings.append(
            "REIT: falta valoración por AFFO; los modelos mostrados son solo referencias"
        )
    elif not is_financial and "dcf" in model_ids:
        primary_id = "dcf"
    elif is_financial and "ddm" in model_ids:
        primary_id = "ddm"
    elif "reversion" in model_ids:
        primary_id = "reversion"
    elif "epv" in model_ids:
        primary_id = "epv"
    else:
        primary_id = None

    uncertainty = assess_uncertainty(
        info, annuals, [m["fair"] for m in models], fcf_source=fcf_source,
    )
    for m in models:
        m["role"] = "primary" if m["id"] == primary_id else "cross_check"
        # Alias temporal para clientes antiguos: ya no representa una ponderación.
        m["weight"] = 1.0 if m["id"] == primary_id else 0.0

    primary = next((m for m in models if m["id"] == primary_id), None)
    base_value = primary["fair"] if primary else None
    mos = ((base_value / price - 1) * 100
           if _ok(base_value) and _ok(price) and price > 0 else None)
    required_mos = uncertainty["requiredMarginPct"]
    buy_price = (base_value / (1 + required_mos / 100)) if base_value else None

    # Tres escenarios coherentes dentro del modelo principal. No mezclan DCF,
    # múltiplos y fórmulas de Graham para fabricar una cifra aparentemente exacta.
    scenarios = []
    if primary_id == "dcf":
        risk_step = {"low": 0.015, "medium": 0.025, "high": 0.035,
                     "very_high": 0.045}[uncertainty["level"]]
        growth_step = {"low": 0.025, "medium": 0.04, "high": 0.06,
                       "very_high": 0.08}[uncertainty["level"]]
        scenario_inputs = [
            ("bear", "Pesimista", max(-0.10, growth - growth_step),
             min(0.25, discount + risk_step), max(0.005, terminal - 0.005), 25),
            ("base", "Base", growth, discount, terminal, 50),
            ("bull", "Optimista", min(0.30, growth + growth_step * 0.65),
             max(terminal + 0.02, discount - risk_step * 0.5),
             min(0.035, terminal + 0.005), 25),
        ]
        for key, label, sg, sd, st, probability in scenario_inputs:
            value = dcf_fair_value(
                base_fcf, shares, net_cash, sg, sd, st,
                forward_fcf=fwd_fcfs,
            )
            if _ok(value) and value > 0:
                scenarios.append({
                    "key": key, "label": label, "value": round(value, 2),
                    "probabilityPct": probability,
                    "assumptions": {
                        "growthPct": round(sg * 100, 1),
                        "discountPct": round(sd * 100, 1),
                        "terminalPct": round(st * 100, 1),
                    },
                })
    elif primary_id == "ddm":
        dps, ddm_growth = dividend_discount_inputs(info, annuals)
        if _ok(dps) and _ok(ddm_growth):
            scenario_inputs = [
                ("bear", "Pesimista", max(0.0, ddm_growth - 0.015), min(0.20, discount + 0.02), 25),
                ("base", "Base", ddm_growth, discount, 50),
                ("bull", "Optimista", min(0.06, ddm_growth + 0.01), max(ddm_growth + 0.015, discount - 0.01), 25),
            ]
            for key, label, sg, sd, probability in scenario_inputs:
                value = dps * (1 + sg) / (sd - sg) if sd > sg else None
                if _ok(value) and value > 0:
                    scenarios.append({
                        "key": key, "label": label, "value": round(value, 2),
                        "probabilityPct": probability,
                        "assumptions": {"dividendGrowthPct": round(sg * 100, 1),
                                        "requiredReturnPct": round(sd * 100, 1)},
                    })
    elif primary_id == "reversion" and _ok(eps):
        p25 = pe_stats.get("p25") if pe_stats else None
        p75 = pe_stats.get("p75") if pe_stats else None
        base_pe = min(pe_med, MAX_TARGET_PE) if _ok(pe_med) else None
        pes = [
            ("bear", "Pesimista", min(p25, MAX_TARGET_PE) if _ok(p25) else base_pe * 0.8, 25),
            ("base", "Base", base_pe, 50),
            ("bull", "Optimista", min(p75, MAX_TARGET_PE) if _ok(p75) else base_pe * 1.15, 25),
        ]
        for key, label, target_pe, probability in pes:
            if _ok(target_pe) and target_pe > 0:
                scenarios.append({
                    "key": key, "label": label, "value": round(eps * target_pe, 2),
                    "probabilityPct": probability,
                    "assumptions": {"normalizedEps": round(eps, 2),
                                    "targetPe": round(target_pe, 1)},
                })

    weighted_scenario_value = None
    if scenarios:
        probability = sum(s["probabilityPct"] for s in scenarios)
        if probability:
            weighted_scenario_value = sum(
                s["value"] * s["probabilityPct"] for s in scenarios
            ) / probability

    for m in models:
        m["fair"] = round(m["fair"], 2)
        m["upside"] = round((m["fair"] / price - 1) * 100, 1) if (_ok(price) and price > 0) else None

    implied = None
    implied_return = None
    if not is_financial:
        implied = implied_growth(
            price, base_fcf, shares, net_cash, discount, terminal,
            forward_fcf=fwd_fcfs,
        )
        if primary_id == "dcf":
            implied_return = implied_discount_rate(
                price, base_fcf, shares, net_cash, growth, terminal,
                forward_fcf=fwd_fcfs,
            )
    elif primary_id == "ddm" and _ok(price) and price > 0:
        dps, ddm_growth = dividend_discount_inputs(info, annuals)
        if _ok(dps) and _ok(ddm_growth):
            implied_return = dps * (1 + ddm_growth) / price + ddm_growth

    risk_free = bond10y / 100 if _ok(bond10y) else 0.04
    etf_hurdle = min(max(risk_free + 0.04, 0.07), 0.12)
    excess_vs_etf = ((implied_return - etf_hurdle) * 100
                     if _ok(implied_return) else None)
    verdict = verdict_from_decision(mos, required_mos, primary_id,
                                    uncertainty["level"])

    return {
        "models": models,
        # `consensus` se conserva para compatibilidad, pero ahora es el valor
        # base del modelo principal, no un promedio de métodos heterogéneos.
        "consensus": round(base_value, 2) if base_value else None,
        "baseValue": round(base_value, 2) if base_value else None,
        "primaryModel": primary_id,
        "applicabilityWarnings": applicability_warnings,
        "buyPrice": round(buy_price, 2) if buy_price else None,
        "marginOfSafety": round(mos, 1) if mos is not None else None,
        "requiredMarginPct": required_mos,
        "verdict": verdict,
        "uncertainty": uncertainty,
        "scenarios": scenarios,
        "probabilityWeightedValue": (round(weighted_scenario_value, 2)
                                     if weighted_scenario_value else None),
        "impliedGrowth": round(implied * 100, 1) if implied is not None else None,
        "impliedReturnPct": round(implied_return * 100, 1) if implied_return is not None else None,
        "etfComparison": {
            "benchmark": "VT/VOO",
            "hurdlePct": round(etf_hurdle * 100, 1),
            "method": "bono EEUU 10A + prima de renta variable de 4 pp",
            "excessReturnPct": round(excess_vs_etf, 1) if excess_vs_etf is not None else None,
            "isProxy": True,
        },
        "earningsYield": round(earnings_yield, 2) if earnings_yield else None,
        "bond10y": round(bond10y, 2) if _ok(bond10y) else None,
        "currencyMismatch": currency_mismatch,
        "dcfInputs": {
            "baseFcf": base_fcf if _ok(base_fcf) else None,
            "shares": shares if _ok(shares) else None,
            "netCash": net_cash if _ok(net_cash) else 0,
            "growth": round(growth, 4),
            "discount": discount,
            "wacc": discount,
            "terminal": terminal,
            "years": 10,
            "fadeStart": 6,
            "fcfSource": fcf_source,
            "forwardFcf": fwd_fcfs or [],
            "forwardYears": fwd_years or [],
        },
    }


def verdict_from_decision(mos, required_mos, primary_model, uncertainty_level):
    if mos is None or not primary_model:
        return {"label": "No valorable con datos actuales", "level": "na"}
    if uncertainty_level == "very_high":
        return {"label": "Incertidumbre demasiado alta", "level": "na"}
    if mos >= required_mos:
        return {"label": "Candidata para investigar", "level": "buy"}
    if mos >= 0:
        return {"label": "Bajo valor base, sin margen suficiente", "level": "hold"}
    if mos >= -20:
        return {"label": "Valoración exigente", "level": "warn"}
    return {"label": "Muy por sobre el valor base", "level": "sell"}


def verdict_from_mos(mos):
    if mos is None:
        return {"label": "Sin datos suficientes", "level": "na"}
    if mos >= 25:
        return {"label": "Potencialmente infravalorada", "level": "buy"}
    if mos >= 0:
        return {"label": "Precio razonable", "level": "hold"}
    if mos >= -20:
        return {"label": "Ligeramente sobrevalorada", "level": "warn"}
    return {"label": "Sobrevalorada", "level": "sell"}


# ----------------------------------------------------------------- scorecard

def _check(cid, name, desc, value, passed, fmt="x", history=None):
    return {"id": cid, "name": name, "desc": desc,
            "value": value, "passed": passed, "fmt": fmt,
            "history": history or []}


def buffett_scorecard(info, annuals, pe_stats, pe_pairs=None, price=None):
    """Criterios cuantitativos de élite inspirados en la filosofía de Warren Buffett
    y Charlie Munger (14 puntos de calidad económica y solidez financiera).
    Incluye series históricas completas para gráficos de tendencia (sparklines)."""
    checks = []

    def avg(key, last_n=5):
        vals = [a[key] for a in annuals[-last_n:] if _ok(a.get(key))]
        return (sum(vals) / len(vals)) if vals else None

    # 1. ROIC Promedio 5A ≥ 12% (indicio económico; no prueba por sí solo un foso)
    roics = [a["roic"] for a in annuals[-5:] if _ok(a.get("roic"))]
    roic_avg = (sum(roics) / len(roics)) if roics else None
    roic_hist = [[a["year"], round(a["roic"], 1)] for a in annuals[-10:] if _ok(a.get("roic"))]
    checks.append(_check("roic", "ROIC ≥ 12%", "Retorno sobre capital invertido sostenido",
                         round(roic_avg, 1) if roic_avg is not None else None,
                         roic_avg >= 12.0 if roic_avg is not None else None, "pct",
                         history=roic_hist))

    # 2. ROE Promedio 5A ≥ 15% (Retorno sobre patrimonio en empresas con capital positivo)
    roe = avg("roe")
    eq_latest = annuals[-1].get("equity") if annuals else None
    roe_valid = roe if (eq_latest is None or eq_latest > 0) else None
    roe_hist = [[a["year"], round(a["roe"], 1)] for a in annuals[-10:] if _ok(a.get("roe")) and (a.get("equity") is None or a["equity"] > 0)]
    checks.append(_check("roe", "ROE ≥ 15%", "Retorno sobre patrimonio promedio (capital positivo)",
                         round(roe_valid, 1) if roe_valid is not None else None,
                         roe_valid >= 15.0 if roe_valid is not None else None, "pct",
                         history=roe_hist))

    # 3. Margen Bruto ≥ 40% (Poder de fijación de precios / Pricing Power)
    gm = avg("grossMargin")
    gm_hist = [[a["year"], round(a["grossMargin"], 1)] for a in annuals[-10:] if _ok(a.get("grossMargin"))]
    checks.append(_check("gross", "Margen bruto ≥ 40%", "Poder de fijación de precios (ventaja competitiva)",
                         round(gm, 1) if gm is not None else None,
                         gm >= 40.0 if gm is not None else None, "pct",
                         history=gm_hist))

    # 4. Margen Neto ≥ 10% (Rentabilidad final consistente)
    nm = avg("netMargin")
    nm_hist = [[a["year"], round(a["netMargin"], 1)] for a in annuals[-10:] if _ok(a.get("netMargin"))]
    checks.append(_check("net", "Margen neto ≥ 10%", "Rentabilidad final consistente (promedio 5 años)",
                         round(nm, 1) if nm is not None else None,
                         nm >= 10.0 if nm is not None else None, "pct",
                         history=nm_hist))

    # 5. Endeudamiento Conservador (Deuda/Patrimonio < 1.0 ó Deuda Neta/FCF < 4 años)
    tot_debt = info.get("totalDebt") or (annuals[-1].get("totalDebt") if annuals else 0) or 0
    cash_val = info.get("totalCash") or (annuals[-1].get("cash") if annuals else 0) or 0
    net_debt = tot_debt - cash_val
    fcf_latest = annuals[-1].get("fcf") if annuals else None

    de = None
    des = [a["debtToEquity"] for a in annuals if _ok(a.get("debtToEquity"))]
    if des and eq_latest and eq_latest > 0:
        de = des[-1]
    elif _ok(info.get("debtToEquity")) and eq_latest and eq_latest > 0:
        de = info["debtToEquity"] / 100.0

    debt_pass = None
    debt_display = None
    debt_fmt = "x"

    if net_debt <= 0 or tot_debt <= 0:
        debt_pass = True
        debt_display = "Caja Neta"
        debt_fmt = "text"
    elif de is not None and de > 0:
        debt_pass = de < 1.0
        debt_display = round(de, 2)
        debt_fmt = "x"
    elif fcf_latest and fcf_latest > 0:
        years_to_pay = net_debt / fcf_latest
        debt_pass = years_to_pay <= 4.0
        debt_display = f"{round(years_to_pay, 1)}a FCF"
        debt_fmt = "text"

    debt_hist = []
    if de is not None and de > 0:
        debt_hist = [[a["year"], round(a["debtToEquity"], 2)] for a in annuals[-10:] if _ok(a.get("debtToEquity")) and a["debtToEquity"] > 0]
    else:
        debt_hist = [[a["year"], round(((a.get("totalDebt") or 0) - (a.get("cash") or 0)) / a["fcf"], 1)]
                     for a in annuals[-10:] if _ok(a.get("fcf")) and a["fcf"] > 0]

    checks.append(_check("debt", "Deuda conservadora", "Deuda/Patrimonio < 1x ó Deuda Neta/FCF < 4 años",
                         debt_display, debt_pass, debt_fmt,
                         history=debt_hist))

    # 6. Cobertura de Intereses > 5x (o Caja Neta / Cero Deuda)
    ic = None
    ics = [a["interestCoverage"] for a in annuals if _ok(a.get("interestCoverage"))]
    if ics:
        ic = ics[-1]

    int_pass = None
    int_display = None
    int_fmt = "x"
    if net_debt <= 0 or tot_debt <= 0:
        int_pass = True
        int_display = "Caja Neta"
        int_fmt = "text"
    elif ic is not None:
        int_pass = ic > 5.0
        int_display = round(ic, 1)
        int_fmt = "x"

    ic_hist = [[a["year"], round(a["interestCoverage"], 1)] for a in annuals[-10:] if _ok(a.get("interestCoverage")) and a["interestCoverage"] > 0]
    checks.append(_check("interest", "Cobertura de intereses > 5x", "EBIT sobre intereses (o Caja Neta)",
                         int_display, int_pass, int_fmt,
                         history=ic_hist))

    # 7. FCF Positivo todos los años disponibles
    fcfs = [a["fcf"] for a in annuals if a.get("fcf") is not None]
    fcf_pos = all(f > 0 for f in fcfs) if len(fcfs) >= 3 else None
    fcf_hist = [[a["year"], round(a["fcf"] / 1e6, 1)] for a in annuals[-10:] if _ok(a.get("fcf"))]
    checks.append(_check("fcf", "FCF positivo todos los años", "Genera caja real de forma consistente",
                         len(fcfs) if fcfs else None, fcf_pos, "años",
                         history=fcf_hist))

    # 8. Calidad de Ganancias (Conversión FCF / Utilidad Neta ≥ 80%)
    pairs = [(a["fcf"], a["netIncome"]) for a in annuals[-5:]
             if _ok(a.get("fcf")) and _ok(a.get("netIncome")) and a["netIncome"] > 0]
    fcf_conv = None
    if pairs:
        ratios = [f / ni * 100 for f, ni in pairs]
        fcf_conv = sum(ratios) / len(ratios)
    fcf_conv_hist = [[a["year"], round(a["fcf"] / a["netIncome"] * 100, 1)]
                     for a in annuals[-10:] if _ok(a.get("fcf")) and _ok(a.get("netIncome")) and a["netIncome"] > 0]
    checks.append(_check("fcf_conversion", "Conversión a FCF ≥ 80%", "Calidad de ganancias (FCF / Utilidad promedio 5A)",
                         round(fcf_conv, 1) if fcf_conv is not None else None,
                         fcf_conv >= 80.0 if fcf_conv is not None else None, "pct",
                         history=fcf_conv_hist))

    # 9. Crecimiento de Ingresos ≥ 5% (CAGR 5 años)
    revs5 = [a["revenue"] for a in annuals[-5:] if _ok(a.get("revenue")) and a["revenue"] > 0]
    rev_g5 = None
    if len(revs5) >= 3:
        rev_g5 = ((revs5[-1] / revs5[0]) ** (1 / (len(revs5) - 1)) - 1) * 100
    rev_hist = [[a["year"], round(a["revenue"] / 1e6, 1)] for a in annuals[-10:] if _ok(a.get("revenue"))]
    checks.append(_check("growth", "Crecimiento ingresos ≥ 5%", "CAGR de ventas últimos 5 años",
                         round(rev_g5, 1) if rev_g5 is not None else None,
                         rev_g5 >= 5.0 if rev_g5 is not None else None, "pct",
                         history=rev_hist))

    # 10. Crecimiento EPS consistente (CAGR 5A ≥ 5%)
    epss5 = [a["eps"] for a in annuals[-5:] if _ok(a.get("eps")) and a["eps"] > 0]
    eps_g5 = None
    if len(epss5) >= 3 and epss5[0] > 0:
        eps_g5 = ((epss5[-1] / epss5[0]) ** (1 / (len(epss5) - 1)) - 1) * 100
    eps_pass = (eps_g5 >= 5.0) if eps_g5 is not None else (epss5[-1] > epss5[0] if len(epss5) >= 2 else None)
    eps_hist = [[a["year"], round(a["eps"], 2)] for a in annuals[-10:] if _ok(a.get("eps"))]
    checks.append(_check("eps", "Crecimiento EPS ≥ 5%", "CAGR de beneficio por acción en 5 años",
                         round(eps_g5, 1) if eps_g5 is not None else (round(epss5[-1], 2) if epss5 else None),
                         eps_pass, "pct" if eps_g5 is not None else "$",
                         history=eps_hist))

    # 11. Recompra de Acciones / No Dilución (disciplina de capital de la directiva)
    sh = [a["sharesOut"] for a in annuals if _ok(a.get("sharesOut"))]
    buyback = None
    pct_chg = None
    if len(sh) >= 3 and sh[0] > 0:
        buyback = sh[-1] <= sh[0] * 1.005  # tolera emisiones mínimas (<0.5%)
        pct_chg = (sh[-1] / sh[0] - 1) * 100
    sh_hist = [[a["year"], round(a["sharesOut"] / 1e6, 1)] for a in annuals[-10:] if _ok(a.get("sharesOut"))]
    checks.append(_check("buyback", "Recompra de acciones", "Acciones en circulación no diluyen al accionista",
                         round(pct_chg, 1) if pct_chg is not None else None, buyback, "pct",
                         history=sh_hist))

    # 12. Razón Corriente ≥ 1.2x (Liquidez de corto plazo)
    cr = None
    crs = [a["currentRatio"] for a in annuals if _ok(a.get("currentRatio"))]
    if crs:
        cr = crs[-1]
    elif _ok(info.get("currentRatio")):
        cr = info["currentRatio"]
    cr_hist = [[a["year"], round(a["currentRatio"], 2)] for a in annuals[-10:] if _ok(a.get("currentRatio"))]
    checks.append(_check("liquidity", "Razón corriente ≥ 1.2", "Liquidez de corto plazo",
                         round(cr, 2) if cr is not None else None,
                         cr >= 1.2 if cr is not None else None, "x",
                         history=cr_hist))

    # 13. Valoración: PE bajo su Mediana Histórica 15A
    pe_disc = None
    if pe_stats and pe_stats.get("vsMedian") is not None:
        pe_disc = pe_stats["vsMedian"]
    pe_hist = [[int(pt[0]), round(pt[1], 1)] for pt in (pe_pairs[-20:] if pe_pairs else []) if _ok(pt[1]) and 0 < pt[1] < 150]
    checks.append(_check("pe", "PE bajo su mediana histórica", "El precio actual cotiza con descuento vs mediana 15A",
                         pe_disc, pe_disc < 0 if pe_disc is not None else None, "pct",
                         history=pe_hist))

    # 14. FCF Yield ≥ 4% (Rentabilidad de caja sobre precio de mercado)
    fcf_yield = None
    mc = info.get("marketCap")
    fcf_now = info.get("freeCashflow") or (annuals[-1].get("fcf") if annuals else None)
    if _ok(mc) and _ok(fcf_now) and mc > 0:
        fcf_yield = fcf_now / mc * 100
    fcf_yield_hist = []
    if price and price > 0:
        fcf_yield_hist = [[a["year"], round(a["fcf"] / (a["sharesOut"] * price) * 100, 2)]
                          for a in annuals[-10:] if _ok(a.get("fcf")) and _ok(a.get("sharesOut")) and a["sharesOut"] > 0]
    checks.append(_check("fcfyield", "FCF yield ≥ 4%", "Rentabilidad de caja sobre capitalización bursátil",
                         round(fcf_yield, 2) if fcf_yield is not None else None,
                         fcf_yield >= 4.0 if fcf_yield is not None else None, "pct",
                         history=fcf_yield_hist))

    evaluated = [c for c in checks if c["passed"] is not None]
    passed = sum(1 for c in evaluated if c["passed"])
    return {"passed": passed, "evaluated": len(evaluated), "checks": checks}


def piotroski_f_score_details(annuals):
    """F-Score con cobertura explícita para no convertir faltantes en ceros."""
    if not annuals or len(annuals) < 2:
        return {"score": None, "evaluated": 0, "total": 9}

    # Tomar los dos últimos años disponibles
    current = annuals[-1]
    prior = annuals[-2]

    results = []

    def criterion(evaluable, passed=False):
        if evaluable:
            results.append(bool(passed))

    # Rentabilidad (Profitability)
    # 1. ROA > 0 (usamos Net Income > 0 si ROA no está explícito pero Net Income sí)
    ni_cur = current.get("netIncome")
    criterion(_ok(ni_cur), _ok(ni_cur) and ni_cur > 0)

    # 2. Operating Cash Flow (OCF) > 0
    ocf_cur = current.get("ocf")
    criterion(_ok(ocf_cur), _ok(ocf_cur) and ocf_cur > 0)

    # 3. Change in ROA (ROA current > ROA prior)
    # Aproximado por (Net Income / Assets)
    assets_cur = current.get("assets")
    assets_prior = prior.get("assets")
    ni_prior = prior.get("netIncome")
    roa_evaluable = (_ok(ni_cur) and _ok(assets_cur) and assets_cur > 0
                     and _ok(ni_prior) and _ok(assets_prior) and assets_prior > 0)
    if roa_evaluable:
        roa_cur = ni_cur / assets_cur
        roa_prior = ni_prior / assets_prior
        criterion(True, roa_cur > roa_prior)

    # 4. Accruals (OCF > Net Income)
    criterion(_ok(ocf_cur) and _ok(ni_cur),
              _ok(ocf_cur) and _ok(ni_cur) and ocf_cur > ni_cur)

    # 5. Change in Leverage (Long-term debt ratio current < prior)
    def _reported_debt(row):
        for key in ("longTermDebt", "totalDebt"):
            if key in row and _ok(row.get(key)):
                return row[key]
        return None

    ltd_cur_v = _reported_debt(current)
    ltd_prior_v = _reported_debt(prior)
    debt_evaluable = False
    debt_passed = False
    if ltd_cur_v is not None and ltd_prior_v is not None and ltd_cur_v <= 0 and ltd_prior_v <= 0:
        debt_evaluable, debt_passed = True, True
    elif ltd_cur_v is not None and ltd_prior_v is not None and ltd_cur_v <= 0 < ltd_prior_v:
        debt_evaluable, debt_passed = True, True
    elif (_ok(ltd_cur_v) and _ok(ltd_prior_v) and _ok(assets_cur) and assets_cur > 0
          and _ok(assets_prior) and assets_prior > 0):
        debt_evaluable = True
        lev_cur = ltd_cur_v / assets_cur
        lev_prior = ltd_prior_v / assets_prior
        debt_passed = lev_cur < lev_prior
    criterion(debt_evaluable, debt_passed)

    # 6. Change in Current Ratio (Current Ratio current > prior)
    cr_cur = current.get("currentRatio")
    cr_prior = prior.get("currentRatio")
    criterion(_ok(cr_cur) and _ok(cr_prior),
              _ok(cr_cur) and _ok(cr_prior) and cr_cur > cr_prior)

    # 7. Change in Shares (Shares current <= prior)
    sh_cur = current.get("sharesOut")
    sh_prior = prior.get("sharesOut")
    criterion(_ok(sh_cur) and _ok(sh_prior),
              _ok(sh_cur) and _ok(sh_prior) and sh_cur <= sh_prior * 1.01)

    # Eficiencia Operativa
    # 8. Change in Gross Margin (Gross Margin current > prior)
    gm_cur = current.get("grossMargin")
    gm_prior = prior.get("grossMargin")
    criterion(_ok(gm_cur) and _ok(gm_prior),
              _ok(gm_cur) and _ok(gm_prior) and gm_cur > gm_prior)

    # 9. Change in Asset Turnover (Asset Turnover current > prior)
    rev_cur = current.get("revenue")
    rev_prior = prior.get("revenue")
    turnover_evaluable = (_ok(rev_cur) and _ok(assets_cur) and assets_cur > 0
                          and _ok(rev_prior) and _ok(assets_prior) and assets_prior > 0)
    if turnover_evaluable:
        at_cur = rev_cur / assets_cur
        at_prior = rev_prior / assets_prior
        criterion(True, at_cur > at_prior)

    return {
        "score": sum(results) if results else None,
        "evaluated": len(results),
        "total": 9,
    }


def piotroski_f_score(annuals):
    """Compatibilidad: devuelve el puntaje, omitiéndolo si no se evaluó nada."""
    return piotroski_f_score_details(annuals)["score"]


def greenblatt_roc(info, annuals):
    """Return on Capital estilo Greenblatt: EBIT / Capital Empleado.
    Usa ROIC (EBIT*(1-t)/invested) cuando está disponible; para filas EDGAR
    aproxima EBIT = ingresos * margen operativo y capital = patrimonio."""
    if not annuals:
        return None

    current = annuals[-1]
    roic = current.get("roic")
    if _ok(roic):
        return round(float(roic), 2)

    rev = current.get("revenue")
    op_margin = current.get("opMargin")
    eq = current.get("equity")
    if not _ok(rev) or not _ok(op_margin) or not _ok(eq) or eq <= 0:
        return None
    ebit = float(rev) * float(op_margin) / 100.0
    return round(ebit / float(eq) * 100, 2)
