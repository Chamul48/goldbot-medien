"""Dünne Hülle um die Claude-API.

Ist kein API-Zugang vorhanden (Paket fehlt, kein Key, Netzwerkfehler),
liefert `ask_json` None – die aufrufenden Module nutzen dann Vorlagen.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

try:  # optionales Paket
    import anthropic
except ImportError:  # pragma: no cover - abhängig von der Umgebung
    anthropic = None


def available() -> bool:
    if anthropic is None:
        return False
    if os.environ.get("GOLDBOT_OFFLINE") == "1":
        return False
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("ANTHROPIC_PROFILE")
    )


def ask_json(
    system: str,
    prompt: str,
    schema: dict[str, Any],
    *,
    model: str = "claude-opus-5-5",
    effort: str = "medium",
) -> dict[str, Any] | None:
    """Stellt eine Anfrage und gibt das JSON-Ergebnis (nach `schema`) zurück."""
    if not available():
        return None

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "effort": effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            # Bei einer Sicherheits-Ablehnung springt die API automatisch
            # auf ein passendes Ersatzmodell um.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        log.warning("Claude-API: Zugangsdaten ungültig – nutze Vorlagen.")
        return None
    except anthropic.RateLimitError:
        log.warning("Claude-API: Rate-Limit erreicht – nutze Vorlagen.")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("Claude-API-Fehler %s: %s – nutze Vorlagen.", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError:
        log.warning("Claude-API nicht erreichbar – nutze Vorlagen.")
        return None

    if response.stop_reason in ("refusal", "max_tokens"):
        log.warning("Claude-Antwort unvollständig (%s) – nutze Vorlagen.", response.stop_reason)
        return None

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("Claude-Antwort war kein gültiges JSON – nutze Vorlagen.")
        return None
