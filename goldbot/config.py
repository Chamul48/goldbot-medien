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
        # Leere Schlüssel (alle Einträge auskommentiert) behalten den Standardwert
        if value is None and key in out:
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def output_dir(cfg: dict[str, Any]) -> Path:
    """Ausgabeordner, relativ zum Projektordner (unabhängig vom aktuellen Ordner)."""
    path = Path(cfg.get("output_dir", "reports"))
    return path if path.is_absolute() else ROOT / path


def _read_user(path: Path) -> dict[str, Any]:
    """config.yaml lesen – mit verständlicher Meldung statt Python-Fehler."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")  # mit dem Windows-Editor als ANSI gespeichert
    try:
        user = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name} ist kein gültiges YAML (oft: Tabulator statt Leerzeichen): {exc}") from exc
    if user is None:
        return {}
    if not isinstance(user, dict):
        raise ValueError(f"{path.name}: oberste Ebene muss aus Schlüsseln bestehen (z. B. 'profile:').")
    return user


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Lädt die Konfiguration. Fehlende Werte kommen aus config.example.yaml."""
    example = ROOT / "config.example.yaml"
    base = yaml.safe_load(example.read_text(encoding="utf-8")) if example.exists() else {}

    candidates = [Path(path)] if path else DEFAULT_PATHS
    for candidate in candidates:
        if candidate.exists():
            if candidate.resolve() == example.resolve():
                return base
            return _merge(base, _read_user(candidate))
    if path:
        raise FileNotFoundError(f"Konfiguration nicht gefunden: {path}")
    return base
