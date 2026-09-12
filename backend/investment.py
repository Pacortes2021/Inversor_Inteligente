"""Matriz integral de investigación de inversiones.

Convierte datos financieros y supuestos de valoración en criterios auditables.
Lo que no puede inferirse de estados financieros queda explícitamente pendiente
para evitar que ausencia de datos parezca una aprobación automática.
"""

from __future__ import annotations

import math
import statistics


def _ok(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _median(values):
    clean = [float(v) for v in values if _ok(v)]
    return statistics.median(clean) if clean else None


def _cagr(values):
    clean = [(y, float(v)) for y, v in values if _ok(y) and _ok(v)]
    if len(clean) < 3:
        return None
    # Un CAGR que atraviesa pérdidas o FCF negativo no tiene interpretación
    # económica estable. Se deja pendiente en vez de saltar los años malos.
    if any(v <= 0 for _, v in clean):
        return None
    start_y, start = clean[0]
    end_y, end = clean[-1]
    years = end_y - start_y
    if years <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def _dispersion(values):
    clean = [float(v) for v in values if _ok(v)]
    center = _median(clean)
    if len(clean) < 3 or not _ok(center) or abs(center) < 1e-9:
        return None
    return _median([abs(v - center) for v in clean]) / abs(center)


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _metric(mid, label, max_points, rating=None, value=None, detail="",
            source="Estados financieros", manual_key=None):
    pending = rating is None
    earned = None if pending else round(max_points * _clamp(rating), 2)
    if pending:
        status = "pending"
    elif rating >= 0.75:
        status = "pass"
    elif rating >= 0.40:
        status = "watch"
    else:
        status = "fail"
    return {
        "id": mid,
        "label": label,
        "maxPoints": max_points,
        "earnedPoints": earned,
        "rating": round(rating * 100, 1) if rating is not None else None,
        "status": status,
        "value": value,
        "detail": detail,
        "source": source,
        "manualKey": manual_key,
    }


def _category(cid, name, weight, metrics):
    earned = sum(m["earnedPoints"] or 0 for m in metrics)
    evaluated = sum(m["maxPoints"] for m in metrics if m["earnedPoints"] is not None)
    pending = weight - evaluated
    return {
        "id": cid,
        "name": name,
        "weight": weight,
        "earnedPoints": round(earned, 1),
        "evaluatedPoints": round(evaluated, 1),
        "pendingPoints": round(max(pending, 0), 1),
        "scorePct": round(earned / evaluated * 100, 1) if evaluated else None,
        "metrics": metrics,
    }


def _series(annuals, key, years=5, positive_only=False):
    rows = annuals[-years:]
    values = []
    for row in rows:
        value = row.get(key)
        if _ok(value) and (not positive_only or value > 0):
            values.append(value)
    return values


def _company_type(info):
    sector = str(info.get("sector") or "").lower()
    industry = str(info.get("industry") or "").lower()
    text = f"{sector} {industry}"
    if "reit" in text:
        return "reit"
    if any(x in text for x in ("bank", "insurance", "financial services",
                               "asset management", "credit services")):
        return "financial"
    if any(x in text for x in ("oil", "gas", "mining", "steel", "copper",
                               "gold", "commodity", "paper", "forest products")):
        return "cyclical"
    if any(x in text for x in ("conglomerate", "holding compan")):
        return "conglomerate"
    return "operating"


def _normalization_audit(annuals, valuation):
    recent = annuals[-5:]
    latest = recent[-1] if recent else {}
    fcfs = [r.get("fcf") for r in recent if _ok(r.get("fcf"))]
    net_income = [r.get("netIncome") for r in recent if _ok(r.get("netIncome"))]
    capex_ratios = [abs(r["capex"]) / r["revenue"] * 100 for r in recent
                    if _ok(r.get("capex")) and _ok(r.get("revenue")) and r["revenue"] > 0]
    base_fcf = (valuation.get("dcfInputs") or {}).get("baseFcf")
    latest_sbc = latest.get("stockCompensation")
    owner_after_sbc = (base_fcf - latest_sbc
                       if _ok(base_fcf) and _ok(latest_sbc) else None)
    sbc_pct_fcf = (latest_sbc / latest.get("fcf") * 100
                   if _ok(latest_sbc) and _ok(latest.get("fcf")) and latest["fcf"] > 0 else None)
    wc_delta = None
    if len(recent) >= 2 and _ok(recent[-1].get("workingCapital")) and _ok(recent[-2].get("workingCapital")):
        wc_delta = recent[-1]["workingCapital"] - recent[-2]["workingCapital"]
    wc_pct_revenue = (wc_delta / latest["revenue"] * 100
                      if _ok(wc_delta) and _ok(latest.get("revenue")) and latest["revenue"] else None)

    flags = []
    if _ok(sbc_pct_fcf) and sbc_pct_fcf > 20:
        flags.append("La compensación en acciones supera 20% del FCF reciente")
    if len(net_income) >= 3:
        med_ni = _median(net_income[:-1] or net_income)
        if _ok(med_ni) and med_ni != 0 and abs(net_income[-1] / med_ni - 1) > 0.60:
            flags.append("La utilidad reciente se desvía más de 60% de su mediana anterior")
    if len(capex_ratios) >= 3 and capex_ratios[-1] > _median(capex_ratios) * 1.5:
        flags.append("La intensidad de capex está muy por encima de su mediana reciente")
    if _ok(wc_pct_revenue) and abs(wc_pct_revenue) > 10:
        flags.append("El cambio en capital de trabajo supera 10% de las ventas")
    if not flags:
        flags.append("No se detectaron desviaciones cuantitativas grandes en los ajustes disponibles")

    return {
        "reportedFcf": latest.get("fcf"),
        "dcfBaseFcf": base_fcf,
        "medianFcf5y": _median(fcfs),
        "reportedNetIncome": latest.get("netIncome"),
        "medianNetIncome5y": _median(net_income),
        "stockCompensation": latest_sbc,
        "stockCompPctFcf": round(sbc_pct_fcf, 1) if _ok(sbc_pct_fcf) else None,
        "fcfAfterStockComp": owner_after_sbc,
        "capexPctRevenue": round(capex_ratios[-1], 1) if capex_ratios else None,
        "medianCapexPctRevenue": round(_median(capex_ratios), 1) if capex_ratios else None,
        "workingCapitalChangePctRevenue": round(wc_pct_revenue, 1) if _ok(wc_pct_revenue) else None,
        "flags": flags,
        "unavailableAdjustments": [
            "Separación entre capex de mantenimiento y crecimiento",
            "Clasificación automática de reestructuraciones y deterioros",
            "Normalización del ciclo económico por segmento",
        ],
    }


def _model_review(info, valuation):
    ctype = _company_type(info)
    mapping = {
        "operating": (["DCF", "Reverse DCF", "EV/FCF o EV/EBIT normalizado"],
                      "DCF si el FCF es positivo y razonablemente predecible"),
        "financial": (["DDM", "P/Libro y ROE normalizados"],
                      "DDM; el FCF industrial no representa bien un banco o aseguradora"),
        "reit": (["AFFO", "NAV / valor de activos"],
                 "AFFO es obligatorio antes de emitir un valor base"),
        "cyclical": (["EBIT/FCF de ciclo medio", "Valor de activos", "Reverse DCF"],
                     "Los beneficios recientes deben normalizarse a través del ciclo"),
        "conglomerate": (["Suma de partes", "DCF por segmento"],
                         "Una valoración consolidada puede ocultar negocios muy distintos"),
    }
    recommended, reason = mapping[ctype]
    primary = valuation.get("primaryModel")
    applicable = bool(primary)
    if ctype in {"reit", "conglomerate"}:
        applicable = False
    provisional = ctype == "cyclical" and primary == "dcf"
    return {
        "companyType": ctype,
        "primaryModel": primary,
        "recommendedMethods": recommended,
        "applicable": applicable,
        "provisional": provisional,
        "reason": reason,
    }


def build_investment_analysis(info, annuals, valuation, pe_stats=None, price=None):
    """Devuelve puntuación, cobertura, normalización y expectativas implícitas."""
    annuals = sorted((annuals or []), key=lambda row: row.get("year") or 0)
    recent = annuals[-5:]
    company_type = _company_type(info)
    industrial_metrics = company_type not in {"financial", "reit"}
    dcf_inputs = valuation.get("dcfInputs") or {}
    wacc_pct = dcf_inputs.get("wacc") * 100 if _ok(dcf_inputs.get("wacc")) else None

    roics = _series(annuals, "roic")
    roic_avg = sum(roics) / len(roics) if roics else None
    roic_spread = roic_avg - wacc_pct if _ok(roic_avg) and _ok(wacc_pct) else None
    roic_rating = None
    if _ok(roic_spread):
        roic_rating = _clamp((roic_spread + 3) / 11)

    op_margins = _series(annuals, "opMargin")
    margin_disp = _dispersion(op_margins)
    positive_margin_ratio = (sum(1 for v in op_margins if v > 0) / len(op_margins)
                             if op_margins else None)
    margin_rating = None
    if positive_margin_ratio is not None:
        stability = 1 - _clamp((margin_disp or 0) / 0.5)
        margin_rating = positive_margin_ratio * 0.6 + stability * 0.4

    conversions = [r["fcf"] / r["netIncome"] for r in recent
                   if _ok(r.get("fcf")) and _ok(r.get("netIncome")) and r["netIncome"] > 0]
    conversion = _median(conversions)
    conversion_rating = _clamp((conversion or 0) / 0.9) if conversion is not None else None

    quality = _category("quality", "Calidad y ventaja competitiva", 25, [
        _metric("roic_wacc", "ROIC frente al costo de capital", 10,
                roic_rating if industrial_metrics else None,
                round(roic_spread, 1) if industrial_metrics and _ok(roic_spread) else None,
                "Diferencia promedio ROIC 5A menos WACC, en puntos porcentuales" if industrial_metrics
                else "ROIC industrial no es apropiado; requiere ROE y capital regulatorio"),
        _metric("margin_quality", "Márgenes positivos y estables", 6,
                margin_rating if industrial_metrics else None,
                round(_median(op_margins), 1) if industrial_metrics and op_margins else None,
                "Combina persistencia y dispersión del margen operativo" if industrial_metrics
                else "Requiere métricas sectoriales como margen financiero o AFFO"),
        _metric("cash_conversion", "Conversión de utilidad en FCF", 5,
                conversion_rating if industrial_metrics else None,
                round(conversion * 100, 1) if industrial_metrics and conversion is not None else None,
                "Mediana FCF/utilidad de hasta 5 años" if industrial_metrics
                else "FCF industrial no representa correctamente este tipo de negocio"),
        _metric("moat_evidence", "Evidencia del foso competitivo", 4, None, None,
                "Requiere evidencia sobre marca, costos, red, switching, intangibles o escala",
                "Juicio documentado", "moatRating"),
    ])

    fcfs = _series(annuals, "fcf")
    fcf_positive = (sum(1 for value in fcfs if value > 0) / len(fcfs)) if fcfs else None
    normalized_fcf = _median([v for v in fcfs if v > 0])
    latest = recent[-1] if recent else {}
    debt = latest.get("totalDebt") if _ok(latest.get("totalDebt")) else info.get("totalDebt")
    cash = latest.get("cash") if _ok(latest.get("cash")) else info.get("totalCash")
    net_debt = ((debt or 0) - (cash or 0)) if _ok(debt) or _ok(cash) else None
    debt_years = (net_debt / normalized_fcf
                  if _ok(net_debt) and _ok(normalized_fcf) and normalized_fcf > 0 else None)
    debt_rating = (1.0 if _ok(debt_years) and debt_years <= 0 else
                   _clamp((5 - debt_years) / 5) if _ok(debt_years) else None)
    coverages = _series(annuals, "interestCoverage")
    coverage = _median(coverages)
    coverage_rating = _clamp((coverage or 0) / 8) if coverage is not None else None
    current_ratio = latest.get("currentRatio") if _ok(latest.get("currentRatio")) else info.get("currentRatio")
    liquidity_rating = _clamp((current_ratio - 0.8) / 1.2) if _ok(current_ratio) else None
    shares = [(r.get("year"), r.get("sharesOut")) for r in recent]
    shares_cagr = _cagr(shares)
    dilution_rating = _clamp((0.05 - shares_cagr) / 0.06) if shares_cagr is not None else None

    health = _category("health", "Salud financiera y flujo de caja", 20, [
        _metric("fcf_positive", "FCF positivo y persistente", 5,
                fcf_positive if industrial_metrics else None,
                round(fcf_positive * 100, 0) if industrial_metrics and fcf_positive is not None else None,
                "Porcentaje de ejercicios recientes con FCF positivo" if industrial_metrics
                else "Requiere flujo distribuible, AFFO o métricas regulatorias"),
        _metric("debt_payback", "Deuda neta pagable con FCF", 5,
                debt_rating if industrial_metrics else None,
                round(debt_years, 1) if industrial_metrics and _ok(debt_years) else None,
                "Años de FCF normalizado necesarios para pagar deuda neta" if industrial_metrics
                else "Deuda/FCF industrial no es comparable en este tipo de negocio"),
        _metric("interest_cover", "Cobertura de intereses", 4,
                coverage_rating if company_type != "financial" else None,
                round(coverage, 1) if company_type != "financial" and _ok(coverage) else None,
                "EBIT dividido por gasto financiero" if company_type != "financial"
                else "Los intereses forman parte de la operación financiera"),
        _metric("liquidity", "Liquidez de corto plazo", 2,
                liquidity_rating if industrial_metrics else None,
                round(current_ratio, 2) if industrial_metrics and _ok(current_ratio) else None,
                "Razón corriente; su relevancia depende de la industria" if industrial_metrics
                else "La razón corriente no mide adecuadamente liquidez bancaria o de un REIT"),
        _metric("dilution", "Dilución y recompras netas", 4, dilution_rating,
                round(shares_cagr * 100, 1) if shares_cagr is not None else None,
                "CAGR de acciones en circulación; negativo indica recompra neta"),
    ])

    revenue_cagr = _cagr([(r.get("year"), r.get("revenue")) for r in recent])
    eps_cagr = _cagr([(r.get("year"), r.get("eps")) for r in recent])
    fcf_cagr = _cagr([(r.get("year"), r.get("fcf")) for r in recent])
    growth_rating = lambda value, floor=-0.03, target=0.12: (_clamp((value - floor) / (target - floor))
                                                            if value is not None else None)
    roic_trend_rating = None
    if len(roics) >= 3 and _ok(wacc_pct):
        above = sum(1 for value in roics if value > wacc_pct) / len(roics)
        trend = 1 if roics[-1] >= roics[0] else 0.6
        roic_trend_rating = above * 0.7 + trend * 0.3
    growth = _category("growth", "Crecimiento y reinversión", 15, [
        _metric("revenue_growth", "Crecimiento de ventas", 4, growth_rating(revenue_cagr),
                round(revenue_cagr * 100, 1) if revenue_cagr is not None else None,
                "CAGR reportado de hasta 5 años; no equivale necesariamente a crecimiento orgánico"),
        _metric("eps_growth", "Crecimiento de EPS normalizable", 3, growth_rating(eps_cagr),
                round(eps_cagr * 100, 1) if eps_cagr is not None else None,
                "CAGR de EPS; debe contrastarse con recompras y extraordinarios"),
        _metric("fcf_growth", "Crecimiento del FCF", 3,
                growth_rating(fcf_cagr) if industrial_metrics else None,
                round(fcf_cagr * 100, 1) if industrial_metrics and fcf_cagr is not None else None,
                "CAGR de FCF de hasta 5 años" if industrial_metrics
                else "Requiere AFFO, dividendos sostenibles o crecimiento de capital regulatorio"),
        _metric("reinvestment", "Reinversión creadora de valor", 3,
                roic_trend_rating if industrial_metrics else None,
                round(roic_avg, 1) if industrial_metrics and _ok(roic_avg) else None,
                "Proxy: persistencia del ROIC sobre WACC; no reemplaza ROIC incremental" if industrial_metrics
                else "Requiere ROE incremental y métricas sectoriales"),
        _metric("organic_growth", "Crecimiento orgánico", 2, None, None,
                "Debe verificarse en reportes por adquisiciones, moneda y cambios de perímetro",
                "Reporte anual / presentación", "organicGrowthRating"),
    ])

    mos = valuation.get("marginOfSafety")
    required = valuation.get("requiredMarginPct")
    mos_rating = (_clamp((mos + 20) / (required + 20)) if _ok(mos) and _ok(required) else None)
    etf = valuation.get("etfComparison") or {}
    excess = etf.get("excessReturnPct")
    etf_rating = _clamp((excess + 3) / 8) if _ok(excess) else None
    implied_growth = valuation.get("impliedGrowth")
    base_growth = dcf_inputs.get("growth") * 100 if _ok(dcf_inputs.get("growth")) else None
    growth_gap = (base_growth - implied_growth
                  if _ok(base_growth) and _ok(implied_growth) else None)
    reverse_rating = _clamp((growth_gap + 8) / 16) if _ok(growth_gap) else None
    pe_vs_median = pe_stats.get("vsMedian") if pe_stats else None
    pe_rating = _clamp((20 - pe_vs_median) / 60) if _ok(pe_vs_median) else None
    scenarios = valuation.get("scenarios") or []
    bear = next((s for s in scenarios if s.get("key") == "bear"), None)
    bull = next((s for s in scenarios if s.get("key") == "bull"), None)
    asymmetry = None
    if (bear and bull and _ok(bear.get("value")) and _ok(bull.get("value"))
            and _ok(price) and price > 0):
        downside = max((price - bear["value"]) / price, 0)
        upside = max((bull["value"] - price) / price, 0)
        asymmetry = upside / downside if downside > 0 else (3.0 if upside > 0 else 0.0)
    asymmetry_rating = _clamp((asymmetry or 0) / 2) if asymmetry is not None else None
    model_review = _model_review(info, valuation)
    model_rating = (1.0 if model_review["applicable"] and not model_review["provisional"]
                    else 0.5 if model_review["provisional"] else 0.0)

    valuation_cat = _category("valuation", "Valoración y margen de seguridad", 25, [
        _metric("margin_safety", "Margen frente al requerido", 7, mos_rating, mos,
                f"Margen actual frente a exigencia de {required}%" if required is not None else "Sin exigencia calculable",
                source="Modelo principal y precio de mercado"),
        _metric("etf_hurdle", "Rentabilidad implícita frente a VT/VOO", 6, etf_rating, excess,
                "Prima o déficit frente al umbral diversificado",
                source="Modelo principal + bono EEUU 10A"),
        _metric("reverse_dcf", "Expectativas implícitas razonables", 5, reverse_rating,
                round(growth_gap, 1) if _ok(growth_gap) else None,
                "Crecimiento base menos crecimiento exigido por el precio",
                source="Reverse DCF"),
        _metric("historical_multiple", "Múltiplo frente a su historia", 3, pe_rating,
                round(pe_vs_median, 1) if _ok(pe_vs_median) else None,
                "Solo es una referencia; no constituye una señal de compra",
                source="SEC EDGAR + precios ajustados"),
        _metric("scenario_asymmetry", "Asimetría pesimista/optimista", 3, asymmetry_rating,
                round(asymmetry, 2) if _ok(asymmetry) else None,
                "Upside optimista dividido por pérdida del escenario pesimista",
                source="Escenarios del modelo principal"),
        _metric("model_fit", "Método apropiado para el negocio", 1, model_rating,
                valuation.get("primaryModel"), model_review["reason"],
                source="Clasificación sectorial y disponibilidad de datos"),
    ])

    fcf_disp = _dispersion(fcfs)
    ni_values = _series(annuals, "netIncome")
    ni_disp = _dispersion(ni_values)
    predict_rating = lambda value: 1 - _clamp((value or 0) / 0.6) if value is not None else None
    beta = info.get("beta")
    beta_rating = _clamp((2 - beta) / 1.5) if _ok(beta) else None
    leverage_risk_rating = debt_rating
    risk = _category("risk", "Riesgos y previsibilidad", 10, [
        _metric("fcf_predictability", "Previsibilidad del FCF", 2, predict_rating(fcf_disp),
                round(fcf_disp * 100, 1) if fcf_disp is not None else None,
                "Dispersión relativa respecto de la mediana"),
        _metric("earnings_predictability", "Previsibilidad de utilidades", 2, predict_rating(ni_disp),
                round(ni_disp * 100, 1) if ni_disp is not None else None,
                "Dispersión relativa de utilidad neta"),
        _metric("market_sensitivity", "Sensibilidad de mercado", 1, beta_rating,
                round(beta, 2) if _ok(beta) else None,
                "Beta es contexto de volatilidad, no una definición completa de riesgo"),
        _metric("leverage_risk", "Riesgo financiero", 1, leverage_risk_rating,
                round(debt_years, 1) if _ok(debt_years) else None,
                "Deuda neta sobre FCF normalizado"),
        _metric("cyclicality", "Ciclicidad del negocio", 2, None, None,
                "Requiere identificar la variable de ciclo que mueve ventas, precios y márgenes",
                "Juicio documentado", "cyclicalityRating"),
        _metric("concentration", "Concentración de clientes o productos", 2, None, None,
                "Requiere datos de segmentos, clientes y dependencia de productos",
                "10-K / memoria anual", "concentrationRating"),
    ])

    portfolio = _category("portfolio", "Encaje y diversificación del portafolio", 5, [
        _metric("portfolio_fit", "Aporte a la cartera", 5, None, None,
                "Debe considerar peso actual, sector, moneda, correlación y alternativa ETF",
                "Portafolio personal", "portfolioFitRating"),
    ])

    categories = [quality, health, growth, valuation_cat, risk, portfolio]
    earned = sum(c["earnedPoints"] for c in categories)
    evaluated = sum(c["evaluatedPoints"] for c in categories)
    pending = 100 - evaluated
    coverage = evaluated
    blockers = []
    if not model_review["applicable"]:
        blockers.append(model_review["reason"])
    elif model_review["provisional"]:
        blockers.append("DCF provisional: falta normalizar beneficios y márgenes de ciclo medio")
    if valuation.get("currencyMismatch"):
        blockers.append("Monedas financieras incompatibles sin conversión verificable")
    if coverage < 70:
        blockers.append("Cobertura insuficiente para una conclusión robusta")

    return {
        "methodVersion": "quality-value-1",
        "categories": categories,
        "score": {
            "earnedMin": round(earned, 1),
            "earnedMax": round(earned + pending, 1),
            "evaluatedPoints": round(evaluated, 1),
            "coveragePct": round(coverage, 1),
            "normalizedEvaluatedScore": round(earned / evaluated * 100, 1) if evaluated else None,
        },
        "modelReview": model_review,
        "normalizationAudit": _normalization_audit(annuals, valuation),
        "expectations": {
            "impliedGrowthPct": implied_growth,
            "baseGrowthPct": round(base_growth, 1) if _ok(base_growth) else None,
            "growthCushionPct": round(growth_gap, 1) if _ok(growth_gap) else None,
            "impliedReturnPct": valuation.get("impliedReturnPct"),
            "etfHurdlePct": etf.get("hurdlePct"),
            "excessReturnPct": excess,
            "scenarioAsymmetry": round(asymmetry, 2) if _ok(asymmetry) else None,
            "probabilityWeightedValue": valuation.get("probabilityWeightedValue"),
        },
        "blockers": blockers,
        "decisionReady": not blockers and pending == 0,
    }
