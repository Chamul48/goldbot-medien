"""Schreibt Ergebnisse als Markdown + JSON in den Ausgabeordner."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .trends import TrendItem


def _profile_md(pack: dict[str, Any], source: str, notes: list[str]) -> str:
    out = [f"# Fiverr-Profil – zum Einfügen\n", f"_Erstellt mit: {source}_\n"]
    if notes:
        out.append("**Hinweise:**\n" + "\n".join(f"- {n}" for n in notes) + "\n")
    out += [
        "## Einzeiler (Feld unter dem Namen – aktuell steht dort „bot“)",
        f"```\n{pack['one_liner']}\n```",
        f"## Über mich ({len(pack['about'])} Zeichen) → „Details hinzufügen“",
        f"```\n{pack['about']}\n```",
        "## Fähigkeiten und Expertise",
        "\n".join(f"- {s}" for s in pack["skills"]),
        "",
        "## Profilfoto",
        "\n".join(f"- {t}" for t in pack["profile_photo_tips"]),
        "",
    ]
    for i, gig in enumerate(pack["gigs"], 1):
        out += [
            f"## Gig {i}: {gig['title']}",
            f"- **Kategorie:** {gig['category']}",
            f"- **Tags:** {', '.join(gig['tags'])}",
            "",
            "**Beschreibung:**",
            f"```\n{gig['description']}\n```",
            "| Paket | Preis | Lieferung | Revisionen | Enthalten |",
            "|---|---|---|---|---|",
        ]
        for p in gig["packages"]:
            out.append(
                f"| {p['name']} | ${p['price_usd']} | {p['delivery_days']} Tage | "
                f"{p['revisions']} | {'; '.join(p['includes'])} |"
            )
        out += ["", "**FAQ:**"]
        out += [f"- **{f['q']}** {f['a']}" for f in gig["faq"]]
        out.append("")
    return "\n".join(out)


def _trends_md(trends: list[TrendItem], errors: list[str], top: int = 25) -> str:
    out = ["# Trends & Chancen\n"]
    leads = [t for t in trends if t.kind == "auftrag"]
    if leads:
        out.append("## Mögliche Aufträge")
        for t in leads[:10]:
            out.append(f"- **[{t.score}]** [{t.title}]({t.url}) – {t.source}")
        out.append("")
    rivals = [t for t in trends if t.kind == "konkurrenz" and t.matched]
    if rivals:
        out.append("## Konkurrenz (andere Anbieter – zum Preisvergleich)")
        for t in rivals[:10]:
            price = f" · Preis: {t.price}" if t.price else ""
            out.append(f"- [{t.title}]({t.url}){price}")
        out.append("")
    out.append("## Relevante Trends")
    for t in [t for t in trends if t.kind == "trend"][:top]:
        hits = f" · Treffer: {', '.join(t.matched)}" if t.matched else ""
        traffic = f" · Traffic: {t.traffic:,}".replace(",", ".") if t.traffic else ""
        link = f"[{t.title}]({t.url})" if t.url else t.title
        out.append(f"- **[{t.score}]** {link} – {t.source}{traffic}{hits}")
    if errors:
        out += ["", "_Nicht erreichbar: " + ", ".join(errors) + "_"]
    return "\n".join(out) + "\n"


def _ideas_md(ideas: dict[str, Any], source: str) -> str:
    out = ["# Vertriebsideen\n", f"_Erstellt mit: {source}_\n",
           f"**Wochenfokus:** {ideas.get('weekly_focus', '')}\n"]
    for i, idea in enumerate(ideas.get("ideas", []), 1):
        out += [
            f"## {i}. {idea['title']}",
            f"- **Warum jetzt:** {idea['why_now']}",
            f"- **Kanal:** {idea['channel']} · **Aufwand:** {idea['effort']} · "
            f"**Umsatzpotenzial:** {idea['revenue_potential']}",
            "- **Schritte:**",
        ]
        out += [f"  {n}. {s}" for n, s in enumerate(idea["action_steps"], 1)]
        out.append("")
    return "\n".join(out)


def write(
    output_dir: str | Path,
    *,
    profile: tuple[dict[str, Any], str, list[str]] | None = None,
    trends: tuple[list[TrendItem], list[str]] | None = None,
    ideas: tuple[dict[str, Any], str] | None = None,
    now: datetime | None = None,
) -> Path:
    """Schreibt einen Bericht nach <output_dir>/<Datum-Uhrzeit>/ und gibt den Ordner zurück."""
    now = now or datetime.now()
    folder = Path(output_dir) / now.strftime("%Y-%m-%d_%H%M")
    folder.mkdir(parents=True, exist_ok=True)

    sections: list[str] = [f"# Goldbot-Bericht {now.strftime('%d.%m.%Y %H:%M')}\n"]
    data: dict[str, Any] = {"created": now.isoformat()}

    if ideas:
        md = _ideas_md(*ideas)
        (folder / "ideen.md").write_text(md, encoding="utf-8")
        sections.append(md)
        data["ideas"] = ideas[0]
    if trends:
        md = _trends_md(*trends)
        (folder / "trends.md").write_text(md, encoding="utf-8")
        sections.append(md)
        data["trends"] = [t.as_dict() for t in trends[0]]
    if profile:
        md = _profile_md(*profile)
        (folder / "profil.md").write_text(md, encoding="utf-8")
        sections.append(md)
        data["profile"] = profile[0]

    (folder / "bericht.md").write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    (folder / "daten.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder
