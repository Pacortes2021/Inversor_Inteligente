import math

from backend import valuation as V


def test_dcf_monotonia():
    base = dict(base_fcf=1e9, shares=1e8, net_cash=0)
    bajo = V.dcf_fair_value(**base, growth=0.05)
    alto = V.dcf_fair_value(**base, growth=0.15)
    assert alto > bajo > 0
    caro = V.dcf_fair_value(**base, growth=0.10, discount=0.12)
    barato = V.dcf_fair_value(**base, growth=0.10, discount=0.08)
    assert barato > caro


def test_dcf_invalido():
    assert V.dcf_fair_value(-1e9, 1e8) is None          # FCF negativo
    assert V.dcf_fair_value(1e9, 0) is None             # sin acciones
    assert V.dcf_fair_value(1e9, 1e8, discount=0.02, terminal=0.025) is None


def test_implied_growth_roundtrip():
    fv = V.dcf_fair_value(1e9, 1e8, 0, growth=0.08)
    g = V.implied_growth(fv, 1e9, 1e8, 0)
    assert abs(g - 0.08) < 0.002


def test_implied_growth_bordes():
    muy_barato = V.dcf_fair_value(1e9, 1e8, 0, growth=-0.20) * 0.5
    assert V.implied_growth(muy_barato, 1e9, 1e8, 0) == -0.20
    muy_caro = V.dcf_fair_value(1e9, 1e8, 0, growth=0.60) * 2
    assert V.implied_growth(muy_caro, 1e9, 1e8, 0) == 0.60


def test_graham():
    assert math.isclose(V.graham_number(4, 10), 30.0)   # sqrt(22.5*4*10)
    assert V.graham_number(-1, 10) is None
    # Con BVPS negativo pero FCF por acción positivo (ej: recompras masivas)
    assert math.isclose(V.graham_number(4, -5, fcf_per_share=10), 30.0)


def test_graham_intrinsic():
    # EPS = 2.0, Growth = 8% (0.08), Y = 4.4% (4.4)
    # V = (2.0 * (8.5 + 2 * 8) * 4.4) / 4.4 = 2.0 * 24.5 = 49.0
    val = V.graham_intrinsic_value(2.0, 0.08, 4.4)
    assert math.isclose(val, 49.0)
    assert V.graham_intrinsic_value(-2.0, 0.08) is None


def test_wacc():
    info = {"beta": 1.2, "marketCap": 1e10, "totalDebt": 2e9}
    wacc = V.estimate_wacc(info, bond10y=4.5)
    assert 0.06 <= wacc <= 0.15


def test_ddm():
    info = {"trailingAnnualDividendRate": 2.50, "returnOnEquity": 0.15, "payoutRatio": 0.40}
    ddm_val = V.dividend_discount_model(info, [], discount=0.10)
    assert ddm_val is not None
    assert ddm_val > 0


def test_pe_reversion_capado():
    assert V.pe_reversion(2, 20) == 40
    assert V.pe_reversion(2, 80) == 2 * V.MAX_TARGET_PE  # capa a 30x


def test_verdict():
    assert V.verdict_from_mos(40)["level"] == "buy"
    assert V.verdict_from_mos(10)["level"] == "hold"
    assert V.verdict_from_mos(-10)["level"] == "warn"
    assert V.verdict_from_mos(-40)["level"] == "sell"
    assert V.verdict_from_mos(None)["level"] == "na"


def _annuals(n=10, opm=25.0, rev=1e9):
    return [{"year": 2016 + i, "opMargin": opm, "revenue": rev,
             "fcf": rev * 0.2, "roe": 20.0, "dividendPS": 1.5} for i in range(n)]


def test_epv():
    info = {"totalRevenue": 1e9, "sharesOutstanding": 1e8,
            "totalCash": 1e8, "totalDebt": 0}
    fv = V.epv_greenwald(info, _annuals())
    # NOPAT = 1e9*0.25*0.79 = 197.5M → /0.10 = 1.975B + 0.1B caja = 2.075B /1e8
    assert math.isclose(fv, 20.75, rel_tol=1e-6)
    assert V.epv_greenwald(info, _annuals(2)) is None   # historia insuficiente


def test_financieras_con_ddm_sin_dcf_ni_epv():
    info = {"sector": "Financial Services", "sharesOutstanding": 1e8,
            "trailingEps": 5, "bookValue": 40, "freeCashflow": 1e9,
            "totalRevenue": 1e9, "totalCash": 0, "totalDebt": 0,
            "trailingAnnualDividendRate": 2.0}
    out = V.build_valuation(50.0, info, _annuals(), {"median": 12.0}, 4.3)
    ids = {m["id"] for m in out["models"]}
    assert "dcf" not in ids and "epv" not in ids
    assert "ddm" in ids and "reversion" in ids and "graham" in ids
    assert out["impliedGrowth"] is None


def test_scorecard_cuenta_bien():
    annuals = [{"year": 2020 + i, "roe": 20, "grossMargin": 50, "netMargin": 15,
                "debtToEquity": 0.5, "interestCoverage": 10, "fcf": 1e8,
                "revenue": 1e9 * (1.1 ** i), "eps": 1.0 * (1.1 ** i),
                "sharesOut": 1e8 - i * 1e6, "currentRatio": 2.0}
               for i in range(5)]
    info = {"marketCap": 1e10, "freeCashflow": 5e8}
    sc = V.buffett_scorecard(info, annuals, {"vsMedian": -10})
    assert sc["evaluated"] == 12
    assert sc["passed"] == 12
