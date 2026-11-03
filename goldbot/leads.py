"""Auftrags-Wächter: meldet nur NEUE passende Aufträge – mit Antwort-Entwurf.

- merkt sich gemeldete Aufträge in einer Datei (keine Wiederholungen)
- schreibt zu jedem Auftrag einen kurzen, persönlichen Antwort-Entwurf
  (Claude oder lokale KI; ohne KI eine Vorlage). Absenden machst du selbst.
- schickt einen Windows-Hinweis (und optional Telegram)
- sammelt alles in reports/auftraege/<Datum>.md
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import llm, notify, trends as trends_mod
from .config import ROOT, output_dir
from .trends import TrendItem

log = logging.getLogger(__name__)

KEEP_DAYS = 30

# Ein Auftrag muss mindestens einen dieser Begriffe enthalten (Video-Bezug).
# Sonst würde z. B. "[Hiring] AI chatbot developer" wegen "ai" gemeldet.
DEFAULT_LEAD_TERMS = [
    "video", "editor", "editing", "edit", "reel", "reels", "shorts", "tiktok", "youtube",
    "caption", "subtitle", "untertitel", "ugc", "faceless", "schnitt", "cutter", "creator", "premiere",
    "capcut", "davinci",
]

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "replies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "reply": {"type": "string"}},
                "required": ["url", "reply"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["replies"],
    "additionalProperties": False,
}

REPLY_SYSTEM = (
    "Du schreibst kurze Antworten auf Auftrags-Posts für einen NEUEN Freelance-Video-Editor ohne "
    "Referenzen. Regeln: Englisch (außer der Post ist deutsch), höchstens 70 Wörter, freundlich, konkret "
    "auf den Post bezogen. Beschreibe, was du für DIESEN Post tun WÜRDEST ('I'd cut …', 'I can …'). "
    "VERBOTEN: Behauptungen über Erfahrung oder Spezialisierung ('I specialize', 'I have experience', "
    "'I work with', 'for various industries', 'my clients', Jahreszahlen, Ergebnisse). Setze für "
    "Arbeitsproben genau den Platzhalter [PORTFOLIO-LINK] ein. Keine E-Mail-Adressen, Telefonnummern "
    "oder Links. Ende mit einer kurzen Frage nach Umfang, Deadline oder Budget."
)

# Entwürfe mit erfundener Erfahrung werden verworfen (Vorlage statt KI-Text)
CLAIM_RE = re.compile(
    r"\b(i specialize|i specialise|specializ\w* in|i have (been|worked|experience|edited|helped)|"
    r"years? of|experienced|my clients|for various|i work with|i('ve| have) (worked|edited|created)|"
    r"proven|track record|many clients|top[- ]rated)\b|https?://|www\.|@\w+\.\w+",
    re.I,
)


# --------------------------------------------------------------------------- #
# Gedächtnis
# --------------------------------------------------------------------------- #

def state_path(cfg: dict[str, Any]) -> Path:
    raw = (cfg.get("leads") or {}).get("state_file")
    if not raw:
        return output_dir(cfg) / ".gesehen.json"
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def load_state(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path: Path, state: dict[str, str], now: datetime) -> None:
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    kept = {url: ts for url, ts in state.items() if ts >= cutoff}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(kept, indent=1, sort_keys=True), encoding="utf-8")


def _key(item: TrendItem) -> str:
    return item.url or item.title


def _video_related(item: TrendItem, terms: list[str]) -> bool:
    text = f"{item.title} {item.summary}".lower()
    return any(re.search(rf"\b{re.escape(t.lower())}" + ("" if len(t) >= 4 else r"\b"), text) for t in terms)


def find_new(items: list[TrendItem], state: dict[str, str], terms: list[str] | None = None) -> list[TrendItem]:
    """Passende Aufträge mit Video-Bezug, die noch nicht gemeldet wurden."""
    terms = terms or DEFAULT_LEAD_TERMS
    out, seen = [], set()
    for item in items:
        key = _key(item)
        if (item.kind == "auftrag" and item.matched and _video_related(item, terms)
                and key not in state and key not in seen):
            seen.add(key)
            out.append(item)
    return out


# --------------------------------------------------------------------------- #
# Antwort-Entwürfe
# --------------------------------------------------------------------------- #

def template_reply(item: TrendItem, cfg: dict[str, Any]) -> str:
    return (
        "Hi! I'm a video editor (English and German) and would be glad to help with this. "
        "Here are some samples: [PORTFOLIO-LINK]. "
        "Could you share the number of videos, the deadline and your budget? "
        "Then I'll send you a concrete offer."
    )


def draft_replies(cfg: dict[str, Any], items: list[TrendItem]) -> dict[str, str]:
    if not items:
        return {}
    drafts = {_key(i): template_reply(i, cfg) for i in items}
    if not (cfg.get("leads") or {}).get("reply_drafts", True):
        return drafts
    profile = cfg.get("profile", {})
    lines = [
        f"Über den Editor: {'; '.join(profile.get('services', []))}. Sprachen: {', '.join(profile.get('languages', []))}.",
        "Schreibe zu jedem Post eine Antwort. Gib die url unverändert zurück.",
        "",
    ]
    for item in items:
        lines += [f"url: {_key(item)}", f"Titel: {item.title}", f"Text: {item.summary[:600]}", ""]
    result = llm.ask_json(REPLY_SYSTEM, "\n".join(lines), REPLY_SCHEMA, cfg.get("llm", {}))
    for entry in (result or {}).get("replies", []):
        url, reply = entry.get("url"), (entry.get("reply") or "").strip()
        if url in drafts and 20 <= len(reply) <= 900 and "[PORTFOLIO-LINK]" in reply:
            if CLAIM_RE.search(reply):
                log.info("KI-Entwurf mit Erfahrungs-Behauptung verworfen – nutze Vorlage.")
                continue
            drafts[url] = reply
    return drafts


# --------------------------------------------------------------------------- #
# Ausgabe
# --------------------------------------------------------------------------- #

def write_leads(out_dir: str | Path, items: list[TrendItem], drafts: dict[str, str], now: datetime) -> Path:
    folder = Path(out_dir) / "auftraege"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now:%Y-%m-%d}.md"
    new_file = not path.exists()
    with path.open("a", encoding="utf-8") as fh:
        if new_file:
            fh.write(f"# Neue Aufträge vom {now:%d.%m.%Y}\n\n"
                     "_Antwort-Entwürfe prüfen, [PORTFOLIO-LINK] ersetzen und selbst absenden._\n\n")
        for item in items:
            fh.write(f"## {now:%H:%M} · {item.title}\n")
            fh.write(f"- **Link:** {item.url}\n- **Quelle:** {item.source} · **Treffer:** {', '.join(item.matched)}\n")
            if item.summary:
                fh.write(f"- **Auszug:** {item.summary[:300]}\n")
            fh.write(f"\n**Antwort-Entwurf:**\n```\n{drafts.get(_key(item), '')}\n```\n\n")
    return path


def check(
    cfg: dict[str, Any],
    items: list[TrendItem] | None = None,
    *,
    fetcher: trends_mod.Fetcher | None = None,
    now: datetime | None = None,
) -> list[TrendItem]:
    """Sucht neue Aufträge, schreibt Entwürfe, benachrichtigt. Gibt die neuen Aufträge zurück."""
    now = now or datetime.now()
    if items is None:
        items, errors = trends_mod.scan(cfg, fetcher, only=("reddit",))
        if errors:
            log.warning("Auftrags-Quellen nicht erreichbar: %s", ", ".join(errors))
    path = state_path(cfg)
    state = load_state(path)
    new = find_new(items, state, (cfg.get("leads") or {}).get("require_any"))
    if not new:
        log.info("Keine neuen passenden Aufträge.")
        return []

    log.info("%d neue passende Aufträge – schreibe Antwort-Entwürfe …", len(new))
    drafts = draft_replies(cfg, new)
    file = write_leads(output_dir(cfg), new, drafts, now)
    title = "Goldbot: 1 neuer Auftrag" if len(new) == 1 else f"Goldbot: {len(new)} neue Aufträge"
    body = new[0].title if len(new) == 1 else "; ".join(i.title[:60] for i in new[:3])
    details = "\n\n".join(f"{i.title}\n{i.url}" for i in new)
    used = notify.send(cfg, title, body, details)
    log.info("Gespeichert in %s%s", file, f" · gemeldet über {', '.join(used)}" if used else "")

    for item in new:
        state[_key(item)] = now.isoformat()
    save_state(path, state, now)
    return new
