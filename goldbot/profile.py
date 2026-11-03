"""Erzeugt ein komplettes, Fiverr-taugliches Profil-Paket zum Einfügen.

Fiverr-Grenzen (Stand 2026, bitte bei Änderungen anpassen):
  - Einzeiler / Berufsbezeichnung: kurz, ca. 60 Zeichen
  - "Über mich": 150–600 Zeichen
  - Gig-Titel: max. 80 Zeichen, beginnt mit "I will" (EN) bzw. "Ich werde" (DE)
  - Gig-Tags: max. 5, je max. 20 Zeichen
  - Gig-Beschreibung: max. 1200 Zeichen
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import llm

LIMITS = {
    "one_liner": 60,
    "about_min": 150,
    "about_max": 600,
    "gig_title": 80,
    "tag_count": 5,
    "tag_len": 20,
    "gig_description": 1200,
}

_PACKAGE = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "price_usd": {"type": "integer"},
        "delivery_days": {"type": "integer"},
        "revisions": {"type": "integer"},
        "includes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "price_usd", "delivery_days", "revisions", "includes"],
    "additionalProperties": False,
}

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "one_liner": {"type": "string"},
        "about": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "gigs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "packages": {"type": "array", "items": _PACKAGE},
                    "faq": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "q": {"type": "string"},
                                "a": {"type": "string"},
                            },
                            "required": ["q", "a"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "category", "tags", "description", "packages", "faq"],
                "additionalProperties": False,
            },
        },
        "profile_photo_tips": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["one_liner", "about", "skills", "gigs", "profile_photo_tips"],
    "additionalProperties": False,
}

SYSTEM = (
    "Du bist ein erfahrener Fiverr-Profil-Coach. Du schreibst verkaufsstarke, "
    "ehrliche Profiltexte auf Englisch (Fiverr-Hauptmarkt), die exakt die "
    "Plattform-Grenzen einhalten. Erfinde keine Referenzen, Kunden, Zahlen oder "
    "Auszeichnungen – nutze nur die Angaben des Nutzers. Keine Kontaktdaten, "
    "keine externen Links (verstößt gegen Fiverr-Regeln)."
)


def _prompt(profile: dict[str, Any], trend_hints: list[str]) -> str:
    lines = [
        "Erstelle ein komplettes Fiverr-Verkäuferprofil mit 3 Gigs.",
        f"Grenzen: one_liner <= {LIMITS['one_liner']} Zeichen; about "
        f"{LIMITS['about_min']}-{LIMITS['about_max']} Zeichen; Gig-Titel <= "
        f"{LIMITS['gig_title']} Zeichen und beginnt mit 'I will'; genau "
        f"{LIMITS['tag_count']} Tags je Gig, je <= {LIMITS['tag_len']} Zeichen, "
        f"nur Buchstaben/Zahlen/Leerzeichen; Gig-Beschreibung <= "
        f"{LIMITS['gig_description']} Zeichen; je Gig 3 Pakete (Basic, Standard, "
        "Premium) und 3 FAQ-Einträge.",
        "",
        f"Benutzername: {profile.get('username')}",
        f"Land: {profile.get('country')}",
        f"Sprachen: {', '.join(profile.get('languages', []))}",
        f"Leistungen: {'; '.join(profile.get('services', []))}",
        f"Fähigkeiten: {', '.join(profile.get('skills', []))}",
        f"Erfahrung: {profile.get('experience', '')}",
        f"Zielkunden: {', '.join(profile.get('target_customers', []))}",
        f"Tonalität: {profile.get('tone', 'professionell')}",
        f"Preisrahmen USD (Basic/Standard/Premium): {profile.get('price_range')}",
    ]
    if trend_hints:
        lines += ["", "Aktuelle Trends, die du in Gigs/Tags aufgreifen darfst:"]
        lines += [f"- {hint}" for hint in trend_hints[:15]]
    return "\n".join(lines)


_DANGLING = {"for", "and", "with", "of", "to", "in", "on", "the", "a", "an", "or", "&", "+",
             "für", "und", "mit", "von", "zu", "im", "in", "der", "die", "das", "oder"}


def _cut(text: str, limit: int, multiline: bool = False) -> str:
    """Kürzt auf `limit` Zeichen an einer Wortgrenze.

    multiline=True behält Zeilenumbrüche (Gig-Beschreibungen mit Aufzählungen),
    sonst wird alles zu einer Zeile zusammengezogen.
    """
    if multiline:
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.replace("\r\n", "\n").split("\n")]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    head = text[: limit + 1]
    cut_at = max(head.rfind(" "), head.rfind("\n"))
    head = head[:cut_at] if cut_at > 0 else head[:limit]
    words = head.rstrip().split(" ")
    # Kein hängendes "for", "and", "&" … am Ende stehen lassen
    while len(words) > 1 and words[-1].lower().strip(",;:-–") in _DANGLING:
        words.pop()
    return " ".join(words).rstrip(",;:-–& \n")[:limit]


def _clean_tag(tag: str) -> str:
    tag = re.sub(r"[^0-9A-Za-zÄÖÜäöüß ]+", " ", tag)
    return _cut(tag.lower(), LIMITS["tag_len"])


def enforce_limits(pack: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Kürzt Felder auf Fiverr-Grenzen und liefert Hinweise zurück."""
    notes: list[str] = []
    if len(pack["one_liner"]) > LIMITS["one_liner"]:
        notes.append("Einzeiler wurde gekürzt.")
    pack["one_liner"] = _cut(pack["one_liner"], LIMITS["one_liner"])

    if len(pack["about"]) > LIMITS["about_max"]:
        notes.append("'Über mich' wurde auf 600 Zeichen gekürzt.")
    pack["about"] = _cut(pack["about"], LIMITS["about_max"])
    if len(pack["about"]) < LIMITS["about_min"]:
        notes.append("'Über mich' ist kürzer als 150 Zeichen – bitte ergänzen.")

    for gig in pack["gigs"]:
        if len(gig["title"]) > LIMITS["gig_title"]:
            notes.append(f"Gig-Titel gekürzt: {gig['title'][:40]}…")
        gig["title"] = _cut(gig["title"], LIMITS["gig_title"])
        tags = []
        for tag in gig["tags"]:
            clean = _clean_tag(tag)
            if clean and clean not in tags:
                tags.append(clean)
        gig["tags"] = tags[: LIMITS["tag_count"]]
        gig["description"] = _cut(gig["description"], LIMITS["gig_description"], multiline=True)
    return pack, notes


_COUNTRY_EN = {"Österreich": "Austria", "Deutschland": "Germany", "Schweiz": "Switzerland"}


def template_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Vorlage ohne KI – solide Grundlage, die du verfeinern kannst.

    Fiverr-Texte sind Englisch; deutsche Konfig-Werte werden daher nicht
    1:1 übernommen (das macht erst die KI-Variante sauber).
    """
    skills = profile.get("skills") or []
    customers = ["creators", "coaches", "finance and gold channels", "small online shops"]
    country = profile.get("country", "Europe")
    low, mid, high = (profile.get("price_range") or [15, 45, 120])[:3]

    about = (
        "Hi, I'm {user} from {country}. I help {customers} grow with scroll-stopping "
        "short videos and smart automation. I handle editing, captions, hooks and "
        "a clean posting workflow so you can focus on your business. Fast replies, "
        "clear communication and revisions until you're happy. Send me a message "
        "with your idea and I'll suggest the best package for your goals."
    ).format(
        user=profile.get("username", "there"),
        country=_COUNTRY_EN.get(country, country),
        customers=", ".join(customers[:3]),
    )

    def packages(factor: float, tiers: list[tuple[int, int, list[str]]]) -> list[dict[str, Any]]:
        """Pakete je Gig; `factor` skaliert den Preisrahmen nach Aufwand."""
        out = []
        for name, base, (days, revisions, includes) in zip(
            ("Basic", "Standard", "Premium"), (low, mid, high), tiers
        ):
            price = int(round(base * factor / 5.0) * 5) or 5
            out.append({"name": name, "price_usd": price, "delivery_days": days,
                        "revisions": revisions, "includes": includes})
        return out

    reels_packages = packages(1.0, [
        (2, 1, ["1 video up to 30s", "animated captions", "music + sound effects"]),
        (3, 2, ["3 videos up to 60s", "animated captions", "hook rewrite", "subtitles EN or DE"]),
        (5, 3, ["8 videos up to 60s", "animated captions", "hooks + scripts", "subtitles EN + DE", "cover images"]),
    ])
    faceless_packages = packages(2.0, [
        (3, 1, ["1 video up to 60s", "script", "AI voiceover", "stock footage + captions"]),
        (4, 2, ["1 video up to 5 min", "researched script", "AI voiceover", "charts + stock footage", "thumbnail"]),
        (7, 3, ["4 shorts + 1 video up to 8 min", "researched scripts", "AI voiceover", "charts + stock footage", "thumbnails"]),
    ])
    automation_packages = packages(2.5, [
        (2, 1, ["workflow review", "list of AI tools for your content", "written recommendations"]),
        (4, 2, ["setup of 1 AI workflow (ideas, scripts, captions)", "prompt templates", "short video guide"]),
        (7, 3, ["full content pipeline: long video to shorts", "prompt + caption templates", "documentation", "30 min handover call on Fiverr"]),
    ])

    reels_faq = [
        {"q": "What do you need from me?",
         "a": "Your raw clips, logo/brand colors if you have them, and 1-2 example videos you like."},
        {"q": "Can you post for me?",
         "a": "I deliver ready-to-post 9:16 files plus caption text and hashtags; you keep full control of your accounts."},
        {"q": "Do you offer monthly packages?",
         "a": "Yes, message me for a recurring package with a lower price per video."},
    ]
    faceless_faq = [
        {"q": "Do I need to record anything?",
         "a": "No. Send me the topic or a few keywords; I write the script and add an AI voiceover."},
        {"q": "Is the content financial advice?",
         "a": "No. Videos are educational and contain no investment recommendations."},
        {"q": "Can you match my channel style?",
         "a": "Yes, send me your channel link or example videos and I follow your format and fonts."},
    ]
    automation_faq = [
        {"q": "Which tools do you use?",
         "a": "I pick tools that fit your budget; you keep your own accounts and logins at all times."},
        {"q": "Do I need technical skills?",
         "a": "No. You get step-by-step documentation and templates you can use right away."},
        {"q": "Can you also edit the videos?",
         "a": "Yes, check my short-form editing gig or message me for a combined offer."},
    ]

    gigs = [
        {
            "title": "I will edit viral reels, tiktoks and youtube shorts with captions",
            "category": "Video & Animation > Video Editing",
            "tags": ["reels editing", "tiktok video", "youtube shorts", "captions", "short form video"],
            "description": (
                "Turn your raw clips into engaging short videos that keep viewers watching. "
                "Included: strong hook in the first seconds, dynamic captions, zooms and cuts, "
                "music and sound effects, export in 9:16 for TikTok, Reels and Shorts. "
                "Perfect for " + ", ".join(customers[:-1]) + " and " + customers[-1] + "."
            ),
            "packages": reels_packages,
            "faq": reels_faq,
        },
        {
            "title": "I will create faceless finance and gold videos for your channel",
            "category": "Video & Animation > Video Editing",
            "tags": ["faceless video", "finance video", "gold", "youtube automation", "voiceover"],
            "description": (
                "Grow a finance, gold or crypto channel without showing your face. I research "
                "the topic, write the script, add AI voiceover, stock footage, charts and captions. "
                "You get a ready-to-upload video. No financial advice is given in the content."
            ),
            "packages": faceless_packages,
            "faq": faceless_faq,
        },
        {
            "title": "I will automate your short video workflow with ai tools",
            "category": "Programming & Tech > AI Services",
            "tags": ["ai automation", "content workflow", "video automation", "ai tools", "chatgpt"],
            "description": (
                "Save hours every week: I set up an AI-assisted workflow for ideas, scripts, "
                "captions and repurposing long videos into shorts. You get a documented process "
                "and templates you can reuse."
            ),
            "packages": automation_packages,
            "faq": automation_faq,
        },
    ]

    return {
        "one_liner": "Short-Form Video Editor & AI Automation",
        "about": about,
        "skills": skills[:10],
        "gigs": gigs,
        "profile_photo_tips": [
            "Echtes, freundliches Foto mit Gesicht, gut ausgeleuchtet, neutraler Hintergrund.",
            "Kein Logo und kein KI-Avatar – Fiverr bevorzugt echte Personen.",
            "Quadratisch, mindestens 400×400 px.",
        ],
    }


def _load_pack(path: str | None) -> dict[str, Any] | None:
    """Lädt ein vorbereitetes Profil-Paket (z. B. aus der Web-Recherche)."""
    if not path:
        return None
    file = Path(path)
    if not file.is_absolute():
        file = Path(__file__).resolve().parent.parent / file
    try:
        pack = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    required = ("one_liner", "about", "skills", "gigs")
    if not all(k in pack for k in required):
        return None
    pack.setdefault("profile_photo_tips", template_profile({})["profile_photo_tips"])
    return pack


def build_profile(cfg: dict[str, Any], trend_hints: list[str] | None = None) -> tuple[dict[str, Any], str, list[str]]:
    """Gibt (Profil-Paket, Quelle, Hinweise) zurück.

    Reihenfolge: Claude > geprüftes Recherche-Paket > lokale KI > Vorlage.
    Ein lokales Modell schreibt schwächere, teils erfundene Profiltexte –
    deshalb hat das Recherche-Paket Vorrang (abschaltbar mit
    profile.prefer_pack: false).
    """
    profile = cfg.get("profile", {})
    llm_cfg = cfg.get("llm", {})
    which = llm.provider(llm_cfg)
    pack = None
    if which == "ollama" and profile.get("prefer_pack", True) and _load_pack(profile.get("pack_file")):
        which = None  # Recherche-Paket nehmen
    if which:
        pack = llm.ask_json(SYSTEM, _prompt(profile, trend_hints or []), PROFILE_SCHEMA, llm_cfg)
    source = llm.describe(llm_cfg)
    if not pack:
        pack, source = _load_pack(profile.get("pack_file")), "recherche"
    if not pack:
        pack, source = template_profile(profile), "vorlage"
    pack, notes = enforce_limits(pack)
    return pack, source, notes
