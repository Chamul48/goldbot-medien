"""Kommandozeile:  python -m goldbot <befehl>

Befehle:
  profil   Profiltexte + Gigs erzeugen
  trends   Trends und Auftrags-Chancen scannen
  ideen    Trends scannen und Vertriebsideen erzeugen
  alles    Alles zusammen (Standard)
  dauer    "alles" in festem Abstand wiederholen (z. B. --alle 24)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from . import ideas as ideas_mod
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

    folder = report.write(out_dir, **kwargs)
    print(f"Fertig. Bericht: {folder / 'bericht.md'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="goldbot", description="Profil-, Trend- und Vertriebsassistent")
    parser.add_argument("befehl", nargs="?", default="alles",
                        choices=["profil", "trends", "ideen", "alles", "dauer"])
    parser.add_argument("-c", "--config", help="Pfad zur config.yaml")
    parser.add_argument("--alle", type=float, default=24.0,
                        help="Stunden zwischen zwei Läufen im Modus 'dauer' (Standard 24)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)

    if args.befehl != "dauer":
        run(cfg, args.befehl)
        return 0

    interval = max(args.alle, 1.0) * 3600
    log.info("Dauerbetrieb: alle %.1f Stunden. Beenden mit Strg+C.", interval / 3600)
    try:
        while True:
            try:
                run(cfg, "alles")
            except Exception:  # Lauf darf den Dauerbetrieb nicht beenden
                log.exception("Lauf fehlgeschlagen – nächster Versuch beim nächsten Intervall.")
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("Beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
