"""KI-Anbindung: Claude-API oder lokale KI über Ollama.

`ask_json` gibt das JSON-Ergebnis (nach Schema) zurück oder None, wenn keine
KI verfügbar ist bzw. die Antwort unbrauchbar war – die aufrufenden Module
nutzen dann das Recherche-Paket oder die Vorlagen.

Konfiguration (Abschnitt `llm` in config.yaml):
  provider: auto | claude | ollama | aus
      auto = Claude, wenn ein API-Key gesetzt ist, sonst Ollama, wenn erreichbar
  model:          Claude-Modell (Standard claude-opus-5-5)
  effort:         Claude-Aufwand (low/medium/high)
  ollama_host:    Standard http://127.0.0.1:11434
  ollama_model:   z. B. qwen3:14b
  ollama_timeout: Sekunden pro Anfrage (lokale Modelle brauchen Zeit)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

try:  # optionales Paket
    import anthropic
except ImportError:  # pragma: no cover - abhängig von der Umgebung
    anthropic = None

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"


# --------------------------------------------------------------------------- #
# Verfügbarkeit
# --------------------------------------------------------------------------- #

def _offline() -> bool:
    return os.environ.get("GOLDBOT_OFFLINE") == "1"


def claude_available() -> bool:
    if anthropic is None or _offline():
        return False
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("ANTHROPIC_PROFILE")
    )


_OLLAMA_CACHE: dict[tuple[str, str], tuple[float, bool]] = {}
_OLLAMA_TTL = 60.0  # Sekunden; im Dauerbetrieb wird ein neu geladenes Modell erkannt


def ollama_available(host: str = DEFAULT_OLLAMA_HOST, model: str = DEFAULT_OLLAMA_MODEL) -> bool:
    """True, wenn der Ollama-Server läuft und das Modell installiert ist."""
    if _offline():
        return False
    key = (host, model)
    cached = _OLLAMA_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < _OLLAMA_TTL:
        return cached[1]
    result = _check_ollama(host, model)
    _OLLAMA_CACHE[key] = (time.monotonic(), result)
    return result


def _check_ollama(host: str, model: str) -> bool:
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        resp.raise_for_status()
        names = {m.get("name", "") for m in resp.json().get("models", [])}
    except (requests.RequestException, ValueError):
        return False
    wanted = {model, f"{model}:latest"} if ":" not in model else {model}
    if names & wanted:
        return True
    log.warning("Ollama läuft, aber Modell '%s' fehlt (installieren: ollama pull %s).", model, model)
    return False


def provider(cfg: dict[str, Any] | None = None) -> str | None:
    """Welche KI genutzt wird: 'claude', 'ollama' oder None."""
    cfg = cfg or {}
    choice = str(cfg.get("provider", "auto")).lower()
    if choice in ("aus", "off", "none", "false"):
        return None
    host = cfg.get("ollama_host", DEFAULT_OLLAMA_HOST)
    model = cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL)
    if choice == "claude":
        return "claude" if claude_available() else None
    if choice == "ollama":
        return "ollama" if ollama_available(host, model) else None
    if claude_available():
        return "claude"
    if ollama_available(host, model):
        return "ollama"
    return None


def available(cfg: dict[str, Any] | None = None) -> bool:
    return provider(cfg) is not None


def describe(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or {}
    which = provider(cfg)
    if which == "claude":
        return f"Claude ({cfg.get('model', 'claude-opus-5-5')})"
    if which == "ollama":
        return f"lokale KI über Ollama ({cfg.get('ollama_model', DEFAULT_OLLAMA_MODEL)})"
    return "keine KI"


# --------------------------------------------------------------------------- #
# Anfragen
# --------------------------------------------------------------------------- #

def _parse(text: str | None, label: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        log.warning("%s-Antwort war kein gültiges JSON – nutze Ersatz.", label)
        return None
    return data if isinstance(data, dict) else None


def _missing_required(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return [k for k in schema.get("required", []) if k not in data]


def _ask_claude(system: str, prompt: str, schema: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=cfg.get("model", "claude-opus-5-5"),
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "effort": cfg.get("effort", "medium"),
                "format": {"type": "json_schema", "schema": schema},
            },
            # Bei einer Sicherheits-Ablehnung springt die API automatisch
            # auf ein passendes Ersatzmodell um.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        log.warning("Claude-API: Zugangsdaten ungültig – nutze Ersatz.")
        return None
    except anthropic.RateLimitError:
        log.warning("Claude-API: Rate-Limit erreicht – nutze Ersatz.")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("Claude-API-Fehler %s: %s – nutze Ersatz.", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError:
        log.warning("Claude-API nicht erreichbar – nutze Ersatz.")
        return None

    if response.stop_reason in ("refusal", "max_tokens"):
        log.warning("Claude-Antwort unvollständig (%s) – nutze Ersatz.", response.stop_reason)
        return None
    text = next((b.text for b in response.content if b.type == "text"), None)
    return _parse(text, "Claude")


def _ask_ollama(system: str, prompt: str, schema: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    host = cfg.get("ollama_host", DEFAULT_OLLAMA_HOST).rstrip("/")
    payload = {
        "model": cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt + "\n\nAntworte ausschließlich mit JSON nach dem vorgegebenen Schema."},
        ],
        "format": schema,  # Ollama erzwingt damit JSON nach Schema
        "stream": False,
        "think": False,  # direkte Antwort, schneller bei Denk-Modellen
        "options": {"num_ctx": int(cfg.get("ollama_num_ctx", 16384)), "temperature": 0.4},
    }
    try:
        resp = requests.post(f"{host}/api/chat", json=payload, timeout=float(cfg.get("ollama_timeout", 900)))
        resp.raise_for_status()
        body = resp.json()
    except requests.Timeout:
        log.warning("Ollama hat zu lange gebraucht – nutze Ersatz.")
        return None
    except (requests.RequestException, ValueError) as exc:
        log.warning("Ollama-Fehler (%s) – nutze Ersatz.", exc.__class__.__name__)
        return None
    return _parse((body.get("message") or {}).get("content"), "Ollama")


def ask_json(
    system: str,
    prompt: str,
    schema: dict[str, Any],
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fragt die konfigurierte KI und gibt JSON nach `schema` zurück (oder None)."""
    cfg = cfg or {}
    which = provider(cfg)
    if which == "claude":
        data = _ask_claude(system, prompt, schema, cfg)
    elif which == "ollama":
        log.info("Frage lokale KI (%s) – das kann einige Minuten dauern …", cfg.get("ollama_model", DEFAULT_OLLAMA_MODEL))
        data = _ask_ollama(system, prompt, schema, cfg)
    else:
        return None
    if data is not None and (missing := _missing_required(data, schema)):
        log.warning("KI-Antwort unvollständig (fehlt: %s) – nutze Ersatz.", ", ".join(missing))
        return None
    return data
