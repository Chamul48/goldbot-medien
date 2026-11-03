"""Kommandozeile:  python -m goldbot <befehl>

Befehle:
  profil   Profiltexte + Gigs erzeugen
  trends   Trends und Auftrags-Chancen scannen
  ideen    Trends scannen und Vertriebsideen erzeugen
  auftraege  Nur neue passende Aufträge suchen (mit Antwort-Entwurf + Hinweis)
  einfuegen  Einfüge-Hilfe für Fiverr öffnen (Kopieren-Knöpfe für jedes Feld)
  muster   Muster-Videos (9:16) für dein Portfolio erstellen – braucht ffmpeg
  alles    Alles zusammen (Standard)
  dauer    Dauerbetrieb: Aufträge jede Stunde (--auftraege-alle),
           alles andere alle 24 Stunden (--alle)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from . import helper
from . import ideas as ideas_mod
from . import leads as leads_mod
from . import llm, profile as profile_mod, report, trends as trends_mod
from .config import load_config, output_dir
from .lock import AlreadyRunning, single_instance

log = logging.getLogger("goldbot")


def run(cfg: dict, command: str) -> None:
    out_dir = output_dir(cfg)
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

    if scanned:
        try:  # ein Fehler beim Auftrags-Check darf den fertigen Bericht nicht gefährden
            leads_mod.check(cfg, scanned[0])
        except Exception:
            log.exception("Auftrags-Check fehlgeschlagen.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="goldbot", description="Profil-, Trend- und Vertriebsassistent")
    parser.add_argument("befehl", nargs="?", default="alles",
                        choices=["profil", "trends", "ideen", "auftraege", "einfuegen", "muster", "alles", "dauer"])
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

    if args.befehl == "muster":
        from . import demo
        target = output_dir(cfg) / "muster"
        try:
            made = demo.render_all(target)
        except RuntimeError as exc:
            log.error("%s", exc)
            return 1
        print(f"{len(made)} Muster-Videos erstellt in: {target}")
        return 0 if made else 1
    if args.befehl == "einfuegen":
        pack, source, _ = profile_mod.build_profile(cfg)
        languages = pack.get("languages") or cfg.get("profile", {}).get("languages")
        page = helper.write(output_dir(cfg) / "einfuegen.html", pack, languages)
        print(f"Einfüge-Hilfe ({source}): {page}")
        import webbrowser
        webbrowser.open(page.as_uri())
        return 0
    if args.befehl == "auftraege":
        leads_mod.check(cfg)
        return 0
    if args.befehl != "dauer":
        run(cfg, args.befehl)
        return 0

    full = max(args.alle, 1.0) * 3600
    lead_hours = args.auftraege_alle or float((cfg.get("leads") or {}).get("check_every_hours", 1))
    # nicht öfter als alle 15 min (Reddit) und nicht seltener als der Komplett-Lauf
    lead = max(min(lead_hours * 3600, full), 15 * 60)
    log.info("Dauerbetrieb: Aufträge alle %.2g h, Komplett-Lauf alle %.3g h. Beenden mit Strg+C.",
             lead / 3600, full / 3600)
    try:
        lock = single_instance(output_dir(cfg) / ".dauer.lock")
        lock.__enter__()
    except AlreadyRunning:
        log.error("Goldbot läuft schon im Dauerbetrieb (anderes Fenster). Dieses Fenster beendet sich.")
        return 2
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
