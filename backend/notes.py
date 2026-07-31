"""Notas cualitativas por acción: tesis, riesgos y checklist de moat."""

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
    return _load().get(symbol.upper(), {"thesis": "", "risks": "", "moats": []})


def set_note(symbol: str, thesis: str = "", risks: str = "", moats=None):
    with _notes_lock:
        notes = _load()
        notes[symbol.upper()] = {
            "thesis": (thesis or "")[:2000],
            "risks": (risks or "")[:2000],
            "moats": [m for m in (moats or []) if m in MOAT_TYPES],
            "updatedAt": int(time.time() * 1000),
        }
        atomic_write_json(NOTES_FILE, notes)
        return notes[symbol.upper()]
