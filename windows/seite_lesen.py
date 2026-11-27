"""Liest eine öffentliche Webseite und gibt die wichtigsten Angaben als JSON aus.

Aufruf:  python seite_lesen.py [-o ergebnis.json] <url> [<url> …]

Mit -o wird das Ergebnis als UTF-8-Datei geschrieben (sicher für €/Umlaute unter Windows).

Für den täglichen Preis- und Wettbewerbsvergleich (docs/taeglich-verbessern.md). Ausgabe je URL:
Titel, Beschreibung, Preise aus JSON-LD-Angeboten und €/$-Beträge mit etwas Text davor.
Keine Anmeldung, keine Klicks, höchstens ein Abruf je Domain alle 10 Sekunden.
Nur Standardbibliothek.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from urllib.parse import urlparse

AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
PAUSE_JE_DOMAIN = 10.0
MAX_BETRAEGE = 120

BETRAG_RE = re.compile(
    r"(?:€|EUR|\$|USD)\s?\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2}|\.\d{1,2})?"
    r"|\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2}|\.\d{1,2})?\s?(?:€|EUR|\$|USD)(?!\w)",
)


def _meta(seite: str, name: str) -> str | None:
    m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']*)' % re.escape(name), seite, re.I) \
        or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']%s["\']' % re.escape(name), seite, re.I)
    return html.unescape(m.group(1)).strip() if m else None


def _angebote(seite: str) -> list[dict]:
    """Preise aus <script type="application/ld+json"> (Product/Offer)."""
    out: list[dict] = []

    def lauf(x, name=None):
        if isinstance(x, list):
            for y in x:
                lauf(y, name)
        elif isinstance(x, dict):
            name = x.get("name", name)
            if "price" in x or "lowPrice" in x:
                out.append({k: x[k] for k in ("price", "lowPrice", "highPrice", "priceCurrency", "availability") if k in x}
                           | ({"name": name} if name else {}))
            for v in x.values():
                if isinstance(v, (list, dict)):
                    lauf(v, name)

    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', seite, re.S | re.I):
        try:
            lauf(json.loads(block.strip()))
        except ValueError:
            continue
    return out[:20]


def _text(seite: str) -> str:
    seite = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", seite, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", seite))).strip()


def auswerten(url: str, seite: str) -> dict:
    titel = re.search(r"<title[^>]*>(.*?)</title>", seite, re.S | re.I)
    text = _text(seite)
    betraege, gesehen = [], set()
    for m in BETRAG_RE.finditer(text):
        kontext = text[max(0, m.start() - 70):m.end()].strip()
        schluessel = text[max(0, m.start() - 15):m.end()]  # gleiche Stelle doppelt auf der Seite → einmal
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        betraege.append(kontext)
        if len(betraege) >= MAX_BETRAEGE:
            break
    return {
        "url": url,
        "titel": html.unescape(titel.group(1)).strip() if titel else None,
        "beschreibung": _meta(seite, "og:description") or _meta(seite, "description"),
        "angebote": _angebote(seite),
        "betraege": betraege,
        "captcha": bool(re.search(r"px-captcha|captcha|Press & Hold|Access denied", seite, re.I)),
        # Profilseiten (z. B. Fiverr): Bildadresse und volle Beschreibung, damit ein Abruf pro Tag reicht
        "profilbild": _json_text(seite, "profileImageUrl"),
        "beschreibung_lang": _json_text(seite, "description", mindestens=200),
    }


def _json_text(seite: str, schluessel: str, mindestens: int = 1) -> str | None:
    """Erster JSON-Textwert zu `schluessel` im Seitenquelltext, der mindestens so lang ist."""
    for roh in re.findall(r'"%s"\s*:\s*"((?:[^"\\]|\\.){0,5000})"' % re.escape(schluessel), seite):
        try:
            wert = json.loads('"' + roh + '"')
        except ValueError:
            continue
        if len(wert) >= mindestens:
            return wert
    return None


def holen(url: str, timeout: float = 25.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Language": "de-AT,de;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        roh = r.read()
        zeichensatz = r.headers.get_content_charset() or "utf-8"
    return roh.decode(zeichensatz, errors="replace")


def main(urls: list[str]) -> int:
    ziel = None
    if len(urls) >= 2 and urls[0] == "-o":
        ziel, urls = urls[1], urls[2:]
    if not urls:
        print(__doc__)
        return 2
    letzter: dict[str, float] = {}
    ergebnisse = []
    for url in urls:
        domain = urlparse(url).netloc
        warten = PAUSE_JE_DOMAIN - (time.monotonic() - letzter.get(domain, -1e9))
        if warten > 0:
            time.sleep(warten)
        letzter[domain] = time.monotonic()
        try:
            ergebnisse.append(auswerten(url, holen(url)))
        except Exception as exc:  # eine kaputte Seite darf die anderen nicht verhindern
            ergebnisse.append({"url": url, "fehler": f"{type(exc).__name__}: {exc}"[:200]})
    text = json.dumps(ergebnisse, ensure_ascii=False, indent=1)
    if ziel:
        with open(ziel, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{len(ergebnisse)} Seiten gelesen -> {ziel}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
