"""Einfüge-Hilfe: eine lokale Seite mit „Kopieren“-Knöpfen für jedes Fiverr-Feld.

Goldbot füllt Fiverr bewusst nicht selbst aus (Bot-Erkennung, Nutzungsbedingungen).
Mit dieser Seite geht es trotzdem schnell: Kopieren → in Fiverr klicken → Strg+V.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

FIVERR_ONBOARDING = "https://www.fiverr.com/seller_onboarding/0"


def _field(label: str, text: str, hint: str = "", limit: int | None = None) -> str:
    count = f"{len(text)}" + (f" / {limit}" if limit else "")
    return (
        '<section class="field">'
        f'<div class="head"><h3>{html.escape(label)}</h3><span class="count">{count} Zeichen</span>'
        f'<button type="button" data-copy="{html.escape(json.dumps(text), quote=True)}">Kopieren</button></div>'
        + (f'<p class="hint">{html.escape(hint)}</p>' if hint else "")
        + f"<pre>{html.escape(text)}</pre></section>"
    )


def build_page(pack: dict[str, Any], languages: list[str] | None = None) -> str:
    parts = [
        '<h2>1 · Profil</h2>',
        _field("Einzeiler", pack["one_liner"], "Feld unter deinem Namen – ersetzt „bot“ (Stift-Symbol).", 60),
        _field("Über mich", pack["about"], "Karte „Um“ → „Details hinzufügen“.", 600),
        _field("Fähigkeiten (eine pro Zeile)", "\n".join(pack.get("skills", [])),
               "„Ergänzen Sie Ihre Fähigkeiten …“ – Fiverr schlägt beim Tippen Begriffe vor; nimm die passenden."),
    ]
    if languages:
        parts.append(_field("Sprachen", "\n".join(languages), "„Sprache hinzufügen“ – nur, was du wirklich sprichst."))
    for i, gig in enumerate(pack.get("gigs", []), 1):
        parts.append(f"<h2>{i + 1} · Gig {i}</h2>")
        # Fiverr zeigt „I will“ fest vor dem Feld – nur den Rest kopieren
        title = re.sub(r"^\s*(I will|Ich werde)\s+", "", gig["title"], flags=re.I)
        parts.append(_field("Gig-Titel", title, "Ohne „I will“ – Fiverr setzt es selbst davor.", 80))
        parts.append(_field("Kategorie", gig.get("category", ""), "In Fiverr auswählen (Name kann leicht abweichen)."))
        for n, tag in enumerate(gig.get("tags", []), 1):
            parts.append(_field(f"Tag {n}", tag, "Einfügen, dann Enter." if n == 1 else "", 20))
        parts.append(_field("Beschreibung", gig["description"], "", 1200))
        rows = "".join(
            f"<tr><td>{html.escape(p['name'])}</td><td>${p['price_usd']}</td><td>{p['delivery_days']} Tage</td>"
            f"<td>{p['revisions']}</td><td>{html.escape('; '.join(p['includes']))}</td></tr>"
            for p in gig.get("packages", [])
        )
        parts.append('<section class="field"><div class="head"><h3>Pakete</h3></div>'
                     "<table><tr><th>Paket</th><th>Preis</th><th>Lieferung</th><th>Revisionen</th>"
                     f"<th>Enthalten</th></tr>{rows}</table></section>")
        for p in gig.get("packages", []):
            desc = p.get("description") or "; ".join(p["includes"])
            parts.append(_field(f"Paket {p['name']} – Beschreibung", desc, "Feld unter dem Paketnamen.", 100))
        for n, faq in enumerate(gig.get("faq", []), 1):
            parts.append(_field(f"FAQ {n} – Frage", faq["q"]))
            parts.append(_field(f"FAQ {n} – Antwort", faq["a"]))

    return """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Goldbot Einfüge-Hilfe</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--muted:#6b6a65;--line:#e2e0d8;--accent:#1dbf73}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--card:#21211e;--ink:#eceae4;--muted:#a09e97;--line:#34332f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}h1{margin:0 0 4px}h2{margin:32px 0 8px}
.lead{color:var(--muted);margin:0 0 16px}.field{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.head{display:flex;gap:10px;align-items:center}.head h3{margin:0;font-size:15px;flex:1}.count{color:var(--muted);font-size:13px}
.hint{color:var(--muted);margin:4px 0 0;font-size:13px}pre{white-space:pre-wrap;margin:8px 0 0;font:14px/1.5 system-ui,sans-serif}
button{background:var(--accent);color:#fff;border:0;border-radius:6px;padding:7px 14px;font-weight:600;cursor:pointer}
button.ok{background:#555}table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
td,th{border-top:1px solid var(--line);padding:6px;text-align:left;vertical-align:top}
a.big{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600}
</style></head><body><main>
<h1>Goldbot Einfüge-Hilfe</h1>
<p class="lead">Pro Feld: <b>Kopieren</b> → in Fiverr ins Feld klicken → <b>Strg+V</b>. Danach bei Fiverr speichern.
Vorher prüfen: Sprachen und Herkunft stimmen, Preise passen.</p>
<p><a class="big" href=\"""" + FIVERR_ONBOARDING + """\" target="_blank" rel="noopener">Fiverr-Profil öffnen</a></p>
""" + "\n".join(parts) + """
</main><script>
document.querySelectorAll("button[data-copy]").forEach(function(b){
  b.addEventListener("click",function(){
    var t=JSON.parse(b.dataset.copy);
    function done(){b.textContent="Kopiert ✓";b.classList.add("ok");setTimeout(function(){b.textContent="Kopieren";b.classList.remove("ok")},2000)}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fallback)}else{fallback()}
    function fallback(){var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove();done()}
  });
});
</script></body></html>"""


def write(path: str | Path, pack: dict[str, Any], languages: list[str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_page(pack, languages), encoding="utf-8")
    return path
