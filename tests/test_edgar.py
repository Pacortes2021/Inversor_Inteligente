from backend import edgar as E


def _entry(end, val, form="10-K", fp="FY", start=None, filed="2026-01-01"):
    e = {"end": end, "val": val, "form": form, "fp": fp, "filed": filed}
    if start:
        e["start"] = start
    return e


def test_annual_points_filtra_trimestres():
    entries = [
        _entry("2025-12-31", 100, start="2025-01-01"),               # anual válido
        _entry("2025-12-31", 30, start="2025-10-01"),                # trimestre: fuera
        _entry("2025-12-31", 99, form="10-Q", start="2025-01-01"),   # 10-Q: fuera
    ]
    pts = E._annual_points(entries, instant=False)
    assert pts == {2025: ("2025-12-31", 100.0)}


def test_annual_points_gana_el_mas_reciente():
    entries = [
        _entry("2024-12-31", 100, start="2024-01-01", filed="2025-02-01"),
        _entry("2024-12-31", 105, start="2024-01-01", filed="2026-02-01"),  # reexpresado
    ]
    pts = E._annual_points(entries, instant=False)
    assert pts[2024][1] == 105.0


def test_to_annual_rows_calcula_fcf_y_roe():
    hist = {
        "revenue": {"2025": ["2025-12-31", 100.0]},
        "netIncome": {"2025": ["2025-12-31", 20.0]},
        "ocf": {"2025": ["2025-12-31", 30.0]},
        "capex": {"2025": ["2025-12-31", 10.0]},
        "equity": {"2025": ["2025-12-31", 100.0]},
    }
    rows = E.to_annual_rows(hist)
    assert len(rows) == 1
    assert rows[0]["fcf"] == 20.0          # OCF - capex
    assert rows[0]["roe"] == 20.0          # 20/100
    assert rows[0]["netMargin"] == 20.0
    assert rows[0]["source"] == "edgar"
