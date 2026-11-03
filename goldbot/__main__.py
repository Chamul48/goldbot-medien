"""Kommandozeile:  python -m goldbot <befehl>

Befehle:
  profil   Profiltexte + Gigs erzeugen
  trends   Trends und Auftrags-Chancen scannen
  ideen    Trends scannen und Vertriebsideen erzeugen
  auftraege  Nur neue passende Aufträge suchen (mit Antwort-Entwurf + Hinweis)
  alles    Alles zusammen (Standard)
  dauer    Dauerbetrieb: Aufträge jede Stunde (--auftraege-alle),
           alles andere alle 24 Stunden (--alle)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from . import ideas as ideas_mod
from . import leads as leads_mod
from . import llm, profile as profile_mod, report, trends as trends_mod
from .config import load_config

log = logging.getLogger("goldbot")


def run(cfg: dict, command: str) -> None:
    out_dir = cfg.get("output_dir", "reports")
    kwargs: dict = {}

    log.info("KI: %s", llm.describe(cfg.get("llm", {})))

    scanned = None
    if command in ("trends", "ideen", "alles"):
        log.info("Scanne Trend-Quellen …")
        scanned = trends_mod.scan(cfg)
        items, errors = scanned
        log.info("%d Einträge gesammelt, %d Quellen nicht erreichbar.", len(items), len(errors))
        kwargs["trends"] = scanned

    if command in ("ideen", "alles"):
        log.info("Erzeuge Vertriebsideen …")
        kwargs["ideas"] = ideas_mod.build_ideas(cfg, scanned[0] if scanned else [])

    if command in ("profil", "alles"):
        log.info("Erzeuge Profiltexte …")
        hints = [t.title for t in (scanned[0] if scanned else []) if t.matched][:15]
        kwargs["profile"] = profile_mod.build_profile(cfg, hints)

    if scanned:
        leads_mod.check(cfg, scanned[0])

    folder = report.write(out_dir, **kwargs)
    print(f"Fertig. Bericht: {folder / 'bericht.md'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="goldbot", description="Profil-, Trend- und Vertriebsassistent")
    parser.add_argument("befehl", nargs="?", default="alles",
                        choices=["profil", "trends", "ideen", "auftraege", "alles", "dauer"])
    parser.add_argument("-c", "--config", help="Pfad zur config.yaml")
    parser.add_argument("--alle", type=float, default=24.0,
                        help="Stunden zwischen zwei Komplett-Läufen im Modus 'dauer' (Standard 24)")
    parser.add_argument("--auftraege-alle", type=float, default=None,
                        help="Stunden zwischen zwei Auftrags-Checks im Modus 'dauer' (Standard aus config, sonst 1)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)

    if args.befehl == "auftraege":
        leads_mod.check(cfg)
        return 0
    if args.befehl != "dauer":
        run(cfg, args.befehl)
        return 0

    full = max(args.alle, 1.0) * 3600
    lead_hours = args.auftraege_alle or float((cfg.get("leads") or {}).get("check_every_hours", 1))
    lead = min(max(lead_hours, 0.25), args.alle) * 3600  # nicht öfter als alle 15 min (Reddit)
    log.info("Dauerbetrieb: Aufträge alle %.2g h, Komplett-Lauf alle %.3g h. Beenden mit Strg+C.",
             lead / 3600, full / 3600)
    next_full = next_lead = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            try:
                if now >= next_full:
                    run(cfg, "alles")  # enthält auch den Auftrags-Check
                    next_full, next_lead = now + full, now + lead
                elif now >= next_lead:
                    leads_mod.check(cfg)
                    next_lead = now + lead
            except Exception:  # ein Fehler darf den Dauerbetrieb nicht beenden
                log.exception("Lauf fehlgeschlagen – nächster Versuch beim nächsten Intervall.")
                next_lead = max(next_lead, now + lead)
                next_full = max(next_full, now + lead)
            time.sleep(max(30.0, min(next_full, next_lead) - time.monotonic()))
    except KeyboardInterrupt:
        log.info("Beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
