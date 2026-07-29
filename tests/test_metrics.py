import pandas as pd

from backend import metrics as M


def test_split_adjust():
    eps = pd.Series({pd.Timestamp("2020-12-31"): 4.0, pd.Timestamp("2023-12-31"): 5.0})
    splits = pd.Series({pd.Timestamp("2022-06-01"): 2.0})  # split 2:1 posterior a 2020
    adj = M.split_adjust(eps, splits, "per_share")
    assert adj[pd.Timestamp("2020-12-31")] == 2.0   # 4 / 2
    assert adj[pd.Timestamp("2023-12-31")] == 5.0   # sin splits posteriores
    sh = M.split_adjust(eps, splits, "shares")
    assert sh[pd.Timestamp("2020-12-31")] == 8.0    # 4 * 2


def test_split_factor():
    splits = pd.Series({pd.Timestamp("2021-07-01"): 4.0, pd.Timestamp("2024-06-01"): 10.0})
    assert M.split_factor(splits, "2020-01-01") == 40.0
    assert M.split_factor(splits, "2022-01-01") == 10.0
    assert M.split_factor(splits, "2025-01-01") == 1.0


def test_merge_series_gana_primaria():
    primaria = pd.Series({pd.Timestamp("2024-01-01"): 10.0})
    extra = pd.Series({pd.Timestamp("2024-01-01"): 99.0, pd.Timestamp("2020-01-01"): 5.0})
    out = M.merge_series(primaria, extra)
    assert out[pd.Timestamp("2024-01-01")] == 10.0  # Yahoo gana en duplicados
    assert out[pd.Timestamp("2020-01-01")] == 5.0   # EDGAR aporta lo antiguo
    assert list(out.index) == sorted(out.index)


def test_ttm_desde_trimestres():
    fechas = pd.date_range("2024-03-31", periods=5, freq="QE")
    inc_q = pd.DataFrame([[1.0, 1.1, 1.2, 1.3, 1.4]], index=["Diluted EPS"], columns=fechas)
    ttm = M.ttm_from_statements(None, inc_q, "Diluted EPS")
    assert len(ttm) == 2                             # dos ventanas de 4 trimestres
    assert abs(ttm.iloc[-1] - (1.1 + 1.2 + 1.3 + 1.4)) < 1e-9


def test_ratio_history_pe():
    meses = pd.date_range("2020-01-31", periods=24, freq="ME")
    precios = pd.Series(100.0, index=meses)
    eps = pd.Series({pd.Timestamp("2020-01-15"): 5.0})
    pe = M.ratio_history(precios, eps, "per_share")
    assert pe is not None and (pe == 20.0).all()


def test_series_stats_percentiles():
    pares = [[i, v] for i, v in enumerate([10, 12, 14, 16, 18, 20, 100])]
    st = M.series_stats(pares)
    assert st["median"] == 16
    assert st["p25"] < st["median"] < st["p75"] < st["max"]
    assert st["current"] == 100
