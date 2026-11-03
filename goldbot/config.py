"""Konfiguration laden (config.yaml, sonst config.example.yaml)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = [ROOT / "config.yaml", ROOT / "config.example.yaml"]


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def output_dir(cfg: dict[str, Any]) -> Path:
    """Ausgabeordner, relativ zum Projektordner (unabhängig vom aktuellen Ordner)."""
    path = Path(cfg.get("output_dir", "reports"))
    return path if path.is_absolute() else ROOT / path


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Lädt die Konfiguration. Fehlende Werte kommen aus config.example.yaml."""
    example = ROOT / "config.example.yaml"
    base = yaml.safe_load(example.read_text(encoding="utf-8")) if example.exists() else {}

    candidates = [Path(path)] if path else DEFAULT_PATHS
    for candidate in candidates:
        if candidate.exists():
            if candidate.resolve() == example.resolve():
                return base
            user = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            return _merge(base, user)
    if path:
        raise FileNotFoundError(f"Konfiguration nicht gefunden: {path}")
    return base
