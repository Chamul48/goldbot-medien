"""Vertriebs- und Wachstumsideen aus Profil + aktuellen Trends."""

from __future__ import annotations

from typing import Any

from . import llm
from .trends import TrendItem

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "why_now": {"type": "string"},
                    "action_steps": {"type": "array", "items": {"type": "string"}},
                    "channel": {"type": "string"},
                    "effort": {"type": "string", "enum": ["niedrig", "mittel", "hoch"]},
                    "revenue_potential": {"type": "string", "enum": ["niedrig", "mittel", "hoch"]},
                },
                "required": ["title", "why_now", "action_steps", "channel", "effort", "revenue_potential"],
                "additionalProperties": False,
            },
        },
        "weekly_focus": {"type": "string"},
    },
    "required": ["ideas", "weekly_focus"],
    "additionalProperties": False,
}

SYSTEM = (
    "Du bist ein pragmatischer Vertriebsberater für Solo-Freelancer auf Fiverr und "
    "Social Media. Du gibst konkrete, sofort umsetzbare Ideen auf Deutsch. Nur legale, "
    "plattformkonforme Methoden: kein Spam, keine Fake-Bewertungen, keine gekauften "
    "Follower, keine Kontaktaufnahme außerhalb von Fiverr bei Fiverr-Kunden. Bei Gold-, "
    "Krypto- oder Finanzthemen keine Anlageberatung versprechen."
)


def _prompt(profile: dict[str, Any], trends: list[TrendItem]) -> str:
    lines = [
        "Erstelle 8 Vertriebsideen für die nächsten 7 Tage, sortiert nach Umsatzpotenzial.",
        f"Leistungen: {'; '.join(profile.get('services', []))}",
        f"Zielkunden: {', '.join(profile.get('target_customers', []))}",
        f"Preisrahmen USD: {profile.get('price_range')}",
        "",
        "Aktuelle Signale (Quelle | Titel | Treffer):",
    ]
    for item in trends[:30]:
        lines.append(f"- {item.source} | {item.title} | {', '.join(item.matched) or '-'}")
    return "\n".join(lines)


def template_ideas(profile: dict[str, Any], trends: list[TrendItem]) -> dict[str, Any]:
    """Regelbasierte Ideen ohne KI."""
    ideas: list[dict[str, Any]] = []
    # Nur Aufträge, die zu deinen Stichwörtern passen (kein "Grafik-Praktikum")
    leads = [t for t in trends if t.kind == "auftrag" and t.matched][:3]
    for lead in leads:
        ideas.append({
            "title": f"Auftrag prüfen: {lead.title[:80]}",
            "why_now": f"Frisch gepostete Anfrage in {lead.source}, passt zu: {', '.join(lead.matched)}.",
            "action_steps": [
                "Beitrag lesen und Regeln des Subreddits prüfen.",
                "Kurze, persönliche Antwort mit 1–2 passenden Arbeitsproben senden.",
                "Auf dein Fiverr-Gig als sichere Bezahlmöglichkeit hinweisen, falls erlaubt.",
            ],
            "channel": lead.source,
            "effort": "niedrig",
            "revenue_potential": "mittel",
        })

    # Content-Ideen nur aus echten Suchtrends (Google Trends), nicht aus Tech-News
    hot = [t for t in trends if t.kind == "trend" and t.matched and t.source.startswith("Google")][:3]
    for trend in hot:
        ideas.append({
            "title": f"Trend-Content: '{trend.title[:60]}'",
            "why_now": f"Aktuell gefragt ({trend.source}). Treffer: {', '.join(trend.matched)}.",
            "action_steps": [
                "Ein 20–30-Sekunden-Reel zum Thema als Arbeitsprobe erstellen.",
                "Als Portfolio-Video in deinem passenden Gig hochladen.",
                "Gig-Tags um 1 passenden Trendbegriff ergänzen.",
            ],
            "channel": "Fiverr-Portfolio + Instagram/TikTok",
            "effort": "mittel",
            "revenue_potential": "mittel",
        })

    ideas += [
        {
            "title": "Gig-Video und 3 Portfolio-Beispiele hinzufügen",
            "why_now": "Gigs mit Video und Beispielen konvertieren auf Fiverr deutlich besser.",
            "action_steps": [
                "30–60 s Gig-Video: wer du bist, was der Kunde bekommt, Ergebnis zeigen.",
                "3 Vorher/Nachher-Beispiele als Galerie hochladen.",
            ],
            "channel": "Fiverr",
            "effort": "mittel",
            "revenue_potential": "hoch",
        },
        {
            "title": "Einstiegsangebot für die ersten 5 Bewertungen",
            "why_now": "Neue Profile brauchen erste ehrliche Bewertungen für Sichtbarkeit.",
            "action_steps": [
                "Basic-Paket zeitlich begrenzt günstiger anbieten.",
                "Extra schnell liefern und nach Abschluss freundlich um ehrliches Feedback bitten.",
            ],
            "channel": "Fiverr",
            "effort": "niedrig",
            "revenue_potential": "mittel",
        },
        {
            "title": "Buyer Requests / Briefs täglich prüfen",
            "why_now": "Fiverr zeigt passende Kundenanfragen – schnelle Angebote gewinnen öfter.",
            "action_steps": [
                "Morgens und abends die Briefs-Seite prüfen.",
                "Angebot mit konkretem Lösungsvorschlag statt Standardtext senden.",
            ],
            "channel": "Fiverr",
            "effort": "niedrig",
            "revenue_potential": "mittel",
        },
        {
            "title": "Eigene Reels als Schaufenster",
            "why_now": "Deine eigenen Kurzvideos beweisen dein Können und bringen Anfragen.",
            "action_steps": [
                "3× pro Woche ein Reel mit Vorher/Nachher-Edit posten.",
                "Im Profil auf dein Fiverr-Profil verlinken (nicht umgekehrt).",
            ],
            "channel": "Instagram / TikTok / YouTube Shorts",
            "effort": "mittel",
            "revenue_potential": "hoch",
        },
    ]
    return {
        "ideas": ideas[:8],
        "weekly_focus": "Profil vollständig machen, Gig-Video hochladen und die ersten Bewertungen holen.",
    }


def build_ideas(cfg: dict[str, Any], trends: list[TrendItem]) -> tuple[dict[str, Any], str]:
    profile = cfg.get("profile", {})
    llm_cfg = cfg.get("llm", {})
    result = llm.ask_json(
        SYSTEM,
        _prompt(profile, trends),
        IDEAS_SCHEMA,
        llm_cfg,
    )
    if result:
        return result, llm.describe(llm_cfg)
    return template_ideas(profile, trends), "vorlage"
