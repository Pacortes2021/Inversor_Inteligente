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
                   discount=0.10, terminal=0.025, years=10, fade_start=6):
    """Reverse DCF: crecimiento de FCF que el precio actual está descontando.
    Se resuelve por bisección; acotado a [-20%, +60%]."""
    if not _ok(price) or price <= 0 or not _ok(base_fcf) or base_fcf <= 0 \
            or not _ok(shares) or shares <= 0:
        return None
    lo, hi = -0.20, 0.60

    def diff(g):
        fv = dcf_fair_value(base_fcf, shares, net_cash, g, discount, terminal, years, fade_start)
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


def dividend_discount_model(info, annuals, discount=0.10):
    """Modelo de Descuento de Dividendos (Gordon Growth) para empresas financieras.
    V0 = DPS * (1 + g) / (discount - g)."""
    dps = info.get("trailingAnnualDividendRate") or info.get("dividendRate")
    if not _ok(dps) or dps <= 0:
        dps_list = [a["dividendPS"] for a in annuals if _ok(a.get("dividendPS")) and a["dividendPS"] > 0]
        dps = dps_list[-1] if dps_list else None
    if not _ok(dps) or dps <= 0:
        return None

    roe = info.get("returnOnEquity") or 0.12
    payout = info.get("payoutRatio") or 0.40
    g = max(0.01, min(0.06, roe * (1 - payout))) if (_ok(roe) and _ok(payout) and payout < 1) else 0.03

    if discount <= g:
        return None
    return dps * (1 + g) / (discount - g)


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
    los últimos 5 años). Devuelve (years, fcfs) o (None, None)."""
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
    years, fcfs = [], []
    for row in fmp_rows:
        ni = row.get("netIncomeAvg")
        if _ok(ni) and ni > 0:
            f = ni * ratio
            if f > 0:
                years.append(row.get("year"))
                fcfs.append(round(f, 2))
    if len(fcfs) < 2:
        return None, None
    return years, fcfs


def build_valuation(price, info, annuals, pe_stats, bond10y, fmp_rows=None):
    """Arma el bloque de valoración completo, con insumos para recalcular
    el DCF en el navegador (sliders)."""
    shares = info.get("sharesOutstanding")
    eps = info.get("trailingEps")
    bvps = info.get("bookValue")

    # FCF base normalizado (owner earnings): mediana entre el TTM de Yahoo,
    # el último anual y el promedio de 3 años, para suavizar cargos puntuales
    cands = []
    v = info.get("freeCashflow")
    if _ok(v) and v > 0:
        cands.append(v)
    fcfs = [a["fcf"] for a in annuals if _ok(a.get("fcf")) and a["fcf"] > 0]
    if fcfs:
        cands.append(fcfs[-1])
    if len(fcfs) >= 3:
        cands.append(sum(fcfs[-3:]) / 3)
    base_fcf = sorted(cands)[len(cands) // 2] if cands else None

    cash = info.get("totalCash") or 0
    debt = info.get("totalDebt") or 0
    net_cash = (cash - debt) if (_ok(cash) and _ok(debt)) else 0

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

    earnings_yield = (eps / price * 100) if (_ok(eps) and price) else None

    # El FCF contable de bancos y aseguradoras no refleja su economía:
    # para financieras el DCF de FCF queda excluido y se usa DDM.
    sector = (info.get("sector") or "")
    is_financial = "Financial" in sector

    epv = epv_greenwald(info, annuals, discount) if not is_financial else None
    # EPV (cero crecimiento) castiga injustamente a empresas de hypergrowth:
    # se excluye cuando el crecimiento estimado supera 15% anual.
    if growth > 0.15:
        epv = None
    ddm = dividend_discount_model(info, annuals, discount) if is_financial else None

    models = []
    if dcf and not is_financial:
        models.append({"id": "dcf", "name": "Flujo de caja descontado (DCF)", "fair": dcf, "weight": 0.35})
    if ddm and is_financial:
        models.append({"id": "ddm", "name": "Modelo Descuento Dividendos (DDM)", "fair": ddm, "weight": 0.30})
    if reversion:
        pe_target = round(min(pe_med, MAX_TARGET_PE), 1)
        label = f"Reversión al PE mediano ({pe_target}x)"
        if pe_med > MAX_TARGET_PE:
            label = f"Reversión al PE mediano (capado a {pe_target}x)"
        weight = 0.35 if is_financial else 0.20
        models.append({"id": "reversion", "name": label, "fair": reversion, "weight": weight})
    if epv:
        models.append({"id": "epv", "name": "EPV Greenwald (cero crecimiento)", "fair": epv, "weight": 0.15})
    if graham_int:
        weight = 0.20 if is_financial else 0.15
        models.append({"id": "graham_intrinsic", "name": "Valor Intrínseco de Graham (rev.)", "fair": graham_int, "weight": weight})
    if graham:
        weight = 0.15 if is_financial else 0.15
        models.append({"id": "graham", "name": "Número de Graham", "fair": graham, "weight": weight})

    consensus, mos = None, None
    if models and price:
        wsum = sum(m["weight"] for m in models)
        consensus = sum(m["fair"] * m["weight"] for m in models) / wsum
        mos = (consensus / price - 1) * 100

    # Precio de compra aceptable: el que deja un margen de seguridad de 25%
    # sobre el valor intrínseco (consenso ponderado).
    buy_price = (consensus / 1.25) if consensus else None

    for m in models:
        m["fair"] = round(m["fair"], 2)
        m["upside"] = round((m["fair"] / price - 1) * 100, 1) if price else None

    implied = None
    if not is_financial:
        implied = implied_growth(price, base_fcf, shares, net_cash, discount, terminal)

    return {
        "models": models,
        "consensus": round(consensus, 2) if consensus else None,
        "buyPrice": round(buy_price, 2) if buy_price else None,
        "marginOfSafety": round(mos, 1) if mos is not None else None,
        "verdict": verdict_from_mos(mos),
        "impliedGrowth": round(implied * 100, 1) if implied is not None else None,
        "earningsYield": round(earnings_yield, 2) if earnings_yield else None,
        "bond10y": round(bond10y, 2) if _ok(bond10y) else None,
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

def _check(cid, name, desc, value, passed, fmt="x"):
    return {"id": cid, "name": name, "desc": desc,
            "value": value, "passed": passed, "fmt": fmt}


def buffett_scorecard(info, annuals, pe_stats):
    """Criterios cuantitativos inspirados en Buffett/Munger. passed puede ser
    True, False o None (sin datos: no cuenta para el puntaje)."""
    checks = []

    def avg(key, last_n=5):
        vals = [a[key] for a in annuals[-last_n:] if _ok(a.get(key))]
        return (sum(vals) / len(vals)) if vals else None

    roe = avg("roe")
    checks.append(_check("roe", "ROE ≥ 15%", "Retorno sobre patrimonio promedio (histórico disponible)",
                         round(roe, 1) if roe is not None else None,
                         roe >= 15 if roe is not None else None, "pct"))

    gm = avg("grossMargin")
    checks.append(_check("gross", "Margen bruto ≥ 40%", "Poder de fijación de precios (proxy de ventaja competitiva)",
                         round(gm, 1) if gm is not None else None,
                         gm >= 40 if gm is not None else None, "pct"))

    nm = avg("netMargin")
    checks.append(_check("net", "Margen neto ≥ 10%", "Rentabilidad final consistente",
                         round(nm, 1) if nm is not None else None,
                         nm >= 10 if nm is not None else None, "pct"))

    de = None
    des = [a["debtToEquity"] for a in annuals if _ok(a.get("debtToEquity"))]
    if des:
        de = des[-1]
    elif _ok(info.get("debtToEquity")):
        de = info["debtToEquity"] / 100.0
    checks.append(_check("debt", "Deuda/Patrimonio < 1", "Endeudamiento conservador",
                         round(de, 2) if de is not None else None,
                         de < 1 if de is not None else None, "x"))

    ic = None
    ics = [a["interestCoverage"] for a in annuals if _ok(a.get("interestCoverage"))]
    if ics:
        ic = ics[-1]
    checks.append(_check("interest", "Cobertura de intereses > 5x", "EBIT sobre gasto en intereses",
                         round(ic, 1) if ic is not None else None,
                         ic > 5 if ic is not None else None, "x"))

    fcfs = [a["fcf"] for a in annuals if a.get("fcf") is not None]
    fcf_pos = all(f > 0 for f in fcfs) if len(fcfs) >= 3 else None
    checks.append(_check("fcf", "FCF positivo todos los años", "Genera caja real de forma consistente",
                         len(fcfs) if fcfs else None, fcf_pos, "años"))

    revs = [a["revenue"] for a in annuals if _ok(a.get("revenue")) and a["revenue"] > 0]
    rev_g = None
    if len(revs) >= 3:
        rev_g = ((revs[-1] / revs[0]) ** (1 / (len(revs) - 1)) - 1) * 100
    checks.append(_check("growth", "Crecimiento ingresos ≥ 5%", "CAGR de ventas (histórico disponible)",
                         round(rev_g, 1) if rev_g is not None else None,
                         rev_g >= 5 if rev_g is not None else None, "pct"))

    epss = [a["eps"] for a in annuals if _ok(a.get("eps"))]
    eps_up = None
    if len(epss) >= 3:
        eps_up = epss[-1] > epss[0] > 0
    checks.append(_check("eps", "EPS creciente", "Utilidad por acción mayor que al inicio del período",
                         round(epss[-1], 2) if epss else None, eps_up, "$"))

    sh = [a["sharesOut"] for a in annuals if _ok(a.get("sharesOut"))]
    buyback = None
    if len(sh) >= 3:
        buyback = sh[-1] <= sh[0] * 1.005  # tolera emisiones mínimas
    checks.append(_check("buyback", "Recompra de acciones", "Acciones en circulación no diluyen al accionista",
                         None, buyback, ""))

    cr = None
    crs = [a["currentRatio"] for a in annuals if _ok(a.get("currentRatio"))]
    if crs:
        cr = crs[-1]
    elif _ok(info.get("currentRatio")):
        cr = info["currentRatio"]
    checks.append(_check("liquidity", "Razón corriente ≥ 1.2", "Liquidez de corto plazo",
                         round(cr, 2) if cr is not None else None,
                         cr >= 1.2 if cr is not None else None, "x"))

    pe_disc = None
    if pe_stats and pe_stats.get("vsMedian") is not None:
        pe_disc = pe_stats["vsMedian"]
    checks.append(_check("pe", "PE bajo su mediana histórica", "El precio actual paga menos por cada dólar de utilidad que el promedio",
                         pe_disc, pe_disc < 0 if pe_disc is not None else None, "pct"))

    fcf_yield = None
    mc = info.get("marketCap")
    fcf_now = info.get("freeCashflow")
    if _ok(mc) and _ok(fcf_now) and mc > 0:
        fcf_yield = fcf_now / mc * 100
    checks.append(_check("fcfyield", "FCF yield ≥ 4%", "Rentabilidad de caja sobre capitalización",
                         round(fcf_yield, 2) if fcf_yield is not None else None,
                         fcf_yield >= 4 if fcf_yield is not None else None, "pct"))

    evaluated = [c for c in checks if c["passed"] is not None]
    passed = sum(1 for c in evaluated if c["passed"])
    return {"passed": passed, "evaluated": len(evaluated), "checks": checks}


def piotroski_f_score(annuals):
    """Calcula el Piotroski F-Score (0-9) basado en los dos últimos años fiscales."""
    if not annuals or len(annuals) < 2:
        return None

    # Tomar los dos últimos años disponibles
    current = annuals[-1]
    prior = annuals[-2]

    score = 0

    # Rentabilidad (Profitability)
    # 1. ROA > 0 (usamos Net Income > 0 si ROA no está explícito pero Net Income sí)
    ni_cur = current.get("netIncome")
    if _ok(ni_cur) and ni_cur > 0:
        score += 1

    # 2. Operating Cash Flow (OCF) > 0
    ocf_cur = current.get("ocf")
    if _ok(ocf_cur) and ocf_cur > 0:
        score += 1

    # 3. Change in ROA (ROA current > ROA prior)
    # Aproximado por (Net Income / Assets)
    assets_cur = current.get("assets")
    assets_prior = prior.get("assets")
    ni_prior = prior.get("netIncome")
    if _ok(ni_cur) and _ok(assets_cur) and assets_cur > 0 and _ok(ni_prior) and _ok(assets_prior) and assets_prior > 0:
        roa_cur = ni_cur / assets_cur
        roa_prior = ni_prior / assets_prior
        if roa_cur > roa_prior:
            score += 1

    # 4. Accruals (OCF > Net Income)
    if _ok(ocf_cur) and _ok(ni_cur) and ocf_cur > ni_cur:
        score += 1

    # Apalancamiento, Liquidez y Fuente de Fondos
    # 5. Change in Leverage (Long-term debt ratio current < prior)
    ltd_cur = current.get("longTermDebt") or current.get("totalDebt")
    ltd_prior = prior.get("longTermDebt") or prior.get("totalDebt")
    if _ok(ltd_cur) and _ok(assets_cur) and assets_cur > 0 and _ok(ltd_prior) and _ok(assets_prior) and assets_prior > 0:
        lev_cur = ltd_cur / assets_cur
        lev_prior = ltd_prior / assets_prior
        if lev_cur < lev_prior:
            score += 1
    elif not _ok(ltd_cur) and not _ok(ltd_prior):
        score += 1 # Sin deuda es bueno

    # 6. Change in Current Ratio (Current Ratio current > prior)
    cr_cur = current.get("currentRatio")
    cr_prior = prior.get("currentRatio")
    if _ok(cr_cur) and _ok(cr_prior) and cr_cur > cr_prior:
        score += 1

    # 7. Change in Shares (Shares current <= prior)
    sh_cur = current.get("sharesOut")
    sh_prior = prior.get("sharesOut")
    if _ok(sh_cur) and _ok(sh_prior) and sh_cur <= sh_prior * 1.01: # Tolerancia del 1%
        score += 1

    # Eficiencia Operativa
    # 8. Change in Gross Margin (Gross Margin current > prior)
    gm_cur = current.get("grossMargin")
    gm_prior = prior.get("grossMargin")
    if _ok(gm_cur) and _ok(gm_prior) and gm_cur > gm_prior:
        score += 1

    # 9. Change in Asset Turnover (Asset Turnover current > prior)
    rev_cur = current.get("revenue")
    rev_prior = prior.get("revenue")
    if _ok(rev_cur) and _ok(assets_cur) and assets_cur > 0 and _ok(rev_prior) and _ok(assets_prior) and assets_prior > 0:
        at_cur = rev_cur / assets_cur
        at_prior = rev_prior / assets_prior
        if at_cur > at_prior:
            score += 1

    return score


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
