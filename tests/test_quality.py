from backend import quality as Q


def _val(base_fcf):
    return {"dcfInputs": {"baseFcf": base_fcf}}


def _pares_años(n):
    ms_año = 365.25 * 24 * 3600 * 1000
    t0 = 1.6e12
    return [[t0 + i * ms_año / 12, 20.0] for i in range(int(n * 12))]


def test_fcf_deprimido():
    annuals = [{"fcf": 10e9, "netIncome": 1e9, "equity": 1e9, "year": 2023},
               {"fcf": 10e9, "netIncome": 1e9, "equity": 1e9, "year": 2024},
               {"fcf": 10e9, "netIncome": 1e9, "equity": 1e9, "year": 2025}]
    w = Q.build_warnings({}, annuals, _val(5e9), _pares_años(10), None)
    assert any("bajo su promedio" in x for x in w)
    w2 = Q.build_warnings({}, annuals, _val(10e9), _pares_años(10), None)
    assert not any("promedio" in x for x in w2)


def test_salto_utilidad():
    annuals = [{"netIncome": 1e9, "fcf": None, "equity": 1e9, "year": 2024},
               {"netIncome": 2e9, "fcf": None, "equity": 1e9, "year": 2025}]
    w = Q.build_warnings({}, annuals, _val(None), _pares_años(10), None)
    assert any("saltó" in x for x in w)


def test_patrimonio_negativo():
    annuals = [{"netIncome": 1e9, "fcf": None, "equity": -5e9, "year": 2025}]
    w = Q.build_warnings({}, annuals, _val(None), _pares_años(10), None)
    assert any("negativo" in x for x in w)


def test_pe_corto():
    w = Q.build_warnings({}, [], _val(None), _pares_años(1), None)
    assert any("historial de pe" in x.lower() for x in w)
    w_long = Q.build_warnings({}, [], _val(None), _pares_años(3), None)
    assert not any("historial de pe" in x.lower() for x in w_long)


def test_pe_is_reliable():
    assert Q.pe_is_reliable({"trailingPE": 25.0}, []) is True
    assert Q.pe_is_reliable({"trailingPE": 200.0}, []) is False
    assert Q.pe_is_reliable({"trailingPE": -5.0}, []) is False
    assert Q.pe_is_reliable({}, []) is False


def test_discrepancia_edgar():
    annuals = [{"year": 2025, "revenue": 10e9, "netIncome": None, "fcf": None, "equity": 1e9}]
    edgar = {"revenue": {"2025": ["2025-12-31", 12e9]}}
    w = Q.build_warnings({}, annuals, _val(None), _pares_años(10), edgar)
    assert any("difieren" in x for x in w)
