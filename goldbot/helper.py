"""Einfüge-Hilfe: eine lokale Seite mit „Kopieren“-Knöpfen für jedes Fiverr-Feld.

Goldbot füllt Fiverr bewusst nicht selbst aus (Bot-Erkennung, Nutzungsbedingungen).
Mit dieser Seite geht es trotzdem schnell: Kopieren → in Fiverr klicken → Strg+V.

Der große Knopf „Nächstes kopieren“ (oder Taste N) kopiert immer das nächste offene Feld und hakt es
ab; der Fortschritt bleibt im Browser gespeichert. Die Muster-Videos sind je Gig verlinkt.
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
        f'<section class="field" data-key="{html.escape(label, quote=True)}">'
        f'<div class="head"><h3>{html.escape(label)}</h3><span class="count">{count} Zeichen</span>'
        f'<button type="button" data-copy="{html.escape(json.dumps(text), quote=True)}">Kopieren</button></div>'
        + (f'<p class="hint">{html.escape(hint)}</p>' if hint else "")
        + f"<pre>{html.escape(text)}</pre></section>"
    )


# Welche Muster-Videos zu welchem Gig passen (Reihenfolge der Gigs im Profil-Paket)
GIG_VIDEOS = [["gold_de", "gold_en"], ["finanzen_de", "finance_en"], ["krypto_de", "crypto_en", "ozean_de", "ocean_en"]]
# Fiverr erlaubt pro Gig nur EIN Video: dieses kommt in die Galerie (Englisch – die meisten Käufer).
# Gig 3: Ozean statt Krypto, zeigt „jedes Thema automatisierbar“.
GIG_UPLOAD = ["gold_en", "finance_en", "ocean_en"]
GIG_FOLDERS = ["Gig 1 - Kurzvideos bearbeiten", "Gig 2 - Faceless Gold und Finanzen",
               "Gig 3 - KI-Video-Automatisierung"]
UPLOAD_DIR = "fiverr_hochladen"


def gallery_video(folder: Path, gig: int) -> Path | None:
    """Das eine Galerie-Video für Gig `gig` (1-basiert): Wunsch-Video, sonst erstes vorhandene (EN zuerst)."""
    names = GIG_VIDEOS[gig - 1] if 0 < gig <= len(GIG_VIDEOS) else []
    wish = [GIG_UPLOAD[gig - 1]] if 0 < gig <= len(GIG_UPLOAD) else []
    ordered = wish + sorted(names, key=lambda n: not n.endswith("_en"))
    return next((folder / f"{n}.mp4" for n in ordered if (folder / f"{n}.mp4").exists()), None)


def _link(src: Path, dst: Path) -> None:
    """Harter Link (kein zusätzlicher Speicher); geht das nicht (anderes Laufwerk), wird kopiert."""
    import os
    import shutil
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def upload_folder(folder: Path, gigs: int = 3) -> Path | None:
    """`fiverr_hochladen\Gig N …\1_Titelbild.jpg + 2_Video.mp4`, übrige Videos unter „Portfolio“.

    Wird bei jedem Lauf neu aufgebaut, damit er zu den aktuellen Videos/Titelbildern passt."""
    import shutil
    target = folder / UPLOAD_DIR
    shutil.rmtree(target, ignore_errors=True)
    used: set[Path] = set()
    made = False
    for gig in range(1, gigs + 1):
        cover, video = folder / f"gig{gig}_titelbild.jpg", gallery_video(folder, gig)
        if not cover.exists() and not video:
            continue
        name = GIG_FOLDERS[gig - 1] if gig <= len(GIG_FOLDERS) else f"Gig {gig}"
        d = target / name
        d.mkdir(parents=True, exist_ok=True)
        if cover.exists():
            _link(cover, d / "1_Titelbild.jpg")
        if video:
            _link(video, d / "2_Video.mp4")
            used.add(video)
        made = True
    rest = [v for v in sorted(folder.glob("*.mp4")) if v not in used]
    if rest:
        (target / "Portfolio (weitere Videos)").mkdir(parents=True, exist_ok=True)
        for v in rest:
            _link(v, target / "Portfolio (weitere Videos)" / v.name)
        made = True
    return target if made else None


def _videos(folder: Path | None, names: list[str]) -> str:
    if not folder:
        return ""
    found = [folder / f"{n}.mp4" for n in names if (folder / f"{n}.mp4").exists()]
    if not found:
        return ""
    gig = GIG_VIDEOS.index(names) + 1 if names in GIG_VIDEOS else 0
    cover = folder / f"gig{gig}_titelbild.jpg"
    main = gallery_video(folder, gig) or found[0]
    img = (f'<p><img src="{cover.as_uri()}" alt="Titelbild Gig {gig}" style="width:100%;border-radius:8px"></p>'
           if cover.exists() else "")
    files = ([f'Titelbild: <a href="{cover.as_uri()}">{html.escape(cover.name)}</a>'] if img else []) + \
        [f'Video: <a href="{main.as_uri()}">{html.escape(main.name)}</a>']
    others = [f for f in found if f != main]
    extra = (f'<p class="hint">Weitere Videos fürs Portfolio (nicht in die Galerie): '
             + " · ".join(f'<a href="{f.as_uri()}">{html.escape(f.name)}</a>' for f in others) + "</p>") if others else ""
    up = folder / UPLOAD_DIR
    where = up if up.exists() else folder
    return ('<section class="field info"><div class="head"><h3>Galerie: 1 Titelbild + 1 Video</h3></div>'
            + img +
            f'<p class="hint">Fiverr erlaubt pro Gig nur ein Video. Bei „Gallery“: Images = Titelbild an erster '
            f'Stelle, Video = dieses eine. Fertig sortiert in: <a href="{where.as_uri()}">{html.escape(str(where))}</a></p>'
            f'<p>{" · ".join(files)}</p>{extra}</section>')


def build_page(pack: dict[str, Any], languages: list[str] | None = None, videos: Path | None = None) -> str:
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
        parts.append(_videos(videos, GIG_VIDEOS[i - 1] if i <= len(GIG_VIDEOS) else []))

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
.field.done{opacity:.45}.field.done h3::before{content:"✓ ";color:var(--accent)}.field.next{outline:3px solid var(--accent)}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;display:flex;gap:10px;align-items:center;border-bottom:1px solid var(--line)}
.bar button.go{font-size:16px;padding:10px 18px}.bar .prog{flex:1;color:var(--muted);font-size:14px}
.bar button.reset{background:transparent;color:var(--muted);border:1px solid var(--line)}
.field.info{border-style:dashed}a{color:var(--accent)}
</style></head><body><main>
<h1>Goldbot Einfüge-Hilfe</h1>
<p class="lead">Pro Feld: <b>Kopieren</b> → in Fiverr ins Feld klicken → <b>Strg+V</b>. Danach bei Fiverr speichern.
Vorher prüfen: Sprachen und Herkunft stimmen, Preise passen.</p>
<p><a class="big" href=\"""" + FIVERR_ONBOARDING + """\" target="_blank" rel="noopener">Fiverr-Profil öffnen</a></p>
<div class="bar"><button type="button" class="go" id="next">Nächstes kopieren (N)</button>
<span class="prog" id="prog"></span><button type="button" class="reset" id="reset">Neu anfangen</button></div>
""" + "\n".join(parts) + """
</main><script>
var KEY="goldbot-einfuegen-erledigt", fields=[].slice.call(document.querySelectorAll(".field[data-key]"));
var doneSet={};try{doneSet=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(doneSet))}catch(e){}}
function refresh(){var n=0,next=null;fields.forEach(function(f){var d=!!doneSet[f.dataset.key];f.classList.toggle("done",d);
  f.classList.remove("next");if(d)n++;else if(!next)next=f});if(next)next.classList.add("next");
  document.getElementById("prog").textContent=n+" von "+fields.length+" Feldern erledigt"+(next?"":" – fertig! Jetzt bei Fiverr speichern.");
  return next}
function copy(b,cb){var t=JSON.parse(b.dataset.copy);
  function done(){b.textContent="Kopiert ✓";b.classList.add("ok");setTimeout(function(){b.textContent="Kopieren";b.classList.remove("ok")},2000);if(cb)cb()}
  function fallback(){var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();document.execCommand("copy");a.remove();done()}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fallback)}else{fallback()}}
fields.forEach(function(f,i){f.dataset.key=i+"·"+f.dataset.key});  // gleiche Namen je Gig unterscheiden
fields.forEach(function(f){var b=f.querySelector("button[data-copy]");
  b.addEventListener("click",function(){copy(b,function(){doneSet[f.dataset.key]=1;save();refresh()})});});
function goNext(){var f=refresh();if(!f)return;f.scrollIntoView({block:"center",behavior:"smooth"});f.querySelector("button[data-copy]").click()}
document.getElementById("next").addEventListener("click",goNext);
document.getElementById("reset").addEventListener("click",function(){doneSet={};save();refresh();scrollTo(0,0)});
document.addEventListener("keydown",function(e){if((e.key==="n"||e.key==="N")&&!e.ctrlKey&&!e.metaKey&&!e.altKey)goNext()});
refresh();
</script></body></html>"""


def write(path: str | Path, pack: dict[str, Any], languages: list[str] | None = None,
          videos: str | Path | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_page(pack, languages, Path(videos).resolve() if videos else None), encoding="utf-8")
    return path
