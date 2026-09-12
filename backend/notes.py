"""Ficha cualitativa por acción para documentar y poder invalidar una tesis."""

import json
import threading
import time
from pathlib import Path

from .data import atomic_write_json, load_json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
NOTES_FILE = DATA_DIR / "notes.json"
_notes_lock = threading.Lock()

MOAT_TYPES = ["marca", "costos", "red", "switching", "intangibles", "escala"]


def _load():
    return load_json(NOTES_FILE, {})


def get_note(symbol: str):
    return _load().get(symbol.upper(), {
        "business": "", "thesis": "", "growthDrivers": "", "risks": "",
        "buySignals": "", "invalidation": "", "maxWeightPct": None,
        "moats": [], "moatRating": "", "organicGrowthRating": "",
        "cyclicalityRating": "", "concentrationRating": "",
        "portfolioFitRating": "",
    })


def set_note(symbol: str, thesis: str = "", risks: str = "", moats=None,
             business: str = "", growth_drivers: str = "",
             buy_signals: str = "", invalidation: str = "",
             max_weight_pct=None, moat_rating="", organic_growth_rating="",
             cyclicality_rating="", concentration_rating="",
             portfolio_fit_rating=""):
    try:
        max_weight = float(max_weight_pct) if max_weight_pct not in (None, "") else None
        max_weight = min(max(max_weight, 0.0), 100.0) if max_weight is not None else None
    except (TypeError, ValueError):
        max_weight = None
    with _notes_lock:
        ratings = {
            "moatRating": moat_rating,
            "organicGrowthRating": organic_growth_rating,
            "cyclicalityRating": cyclicality_rating,
            "concentrationRating": concentration_rating,
            "portfolioFitRating": portfolio_fit_rating,
        }
        allowed = {"strong", "positive", "neutral", "weak", "negative", ""}
        notes = _load()
        notes[symbol.upper()] = {
            "business": (business or "")[:2000],
            "thesis": (thesis or "")[:2000],
            "growthDrivers": (growth_drivers or "")[:2000],
            "risks": (risks or "")[:2000],
            "buySignals": (buy_signals or "")[:2000],
            "invalidation": (invalidation or "")[:2000],
            "maxWeightPct": max_weight,
            "moats": [m for m in (moats or []) if m in MOAT_TYPES],
            **{key: value if value in allowed else "" for key, value in ratings.items()},
            "updatedAt": int(time.time() * 1000),
        }
        atomic_write_json(NOTES_FILE, notes)
        return notes[symbol.upper()]
