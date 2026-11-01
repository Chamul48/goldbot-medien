"""v63d (01.11.): Testläufe (tests/test_*.py) lesen die echte .env nicht mehr. Vorher überschrieben echte Schlüssel am PC die Testwerte
(test_discord_jarvis, test_inhalt, test_jarvis_stimme, test_v61_spiegel, test_fernzugriff rot, obwohl der Bot in Ordnung war).
Im Betrieb (run_agent, run_social, Dashboard) ändert sich nichts. Idempotent, CRLF-fest, erst prüfen dann schreiben, Sicherung *.vor_v63d."""
import sys
from pathlib import Path
B = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
WACHE = "os.path.basename(sys.argv[0] or \"\").startswith(\"test_\") or os.getenv(\"GOLDBOT_TEST\") == \"1\""
P = [
    ("benachrichtigung.py",
     "def env_neu_laden() -> None:\n    \"\"\"Liest die .env erneut, wenn sie sich geändert hat (Werte aus der .env überschreiben die alten).\"\"\"\n    try:\n",
     "def im_test() -> bool:\n    \"\"\"v63d: Läuft gerade ein Test (tests/test_*.py)? Dann wird die echte .env nie gelesen.\"\"\"\n    import sys\n    return " + WACHE + "\n\n\n"
     "def env_neu_laden() -> None:\n    \"\"\"Liest die .env erneut, wenn sie sich geändert hat (Werte aus der .env überschreiben die alten).\"\"\"\n"
     "    if im_test():                                  # v63d: Tests nie mit echten Schlüsseln\n        return\n    try:\n"),
    ("zentrale_llm.py",
     "try:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n",
     "try:\n    from dotenv import load_dotenv\n    import sys as _sys_v63d\n    if not (os.path.basename(_sys_v63d.argv[0] or \"\").startswith(\"test_\") or os.getenv(\"GOLDBOT_TEST\") == \"1\"):   # v63d\n        load_dotenv()\nexcept ImportError:\n    pass\n"),
    ("inhalt.py",
     "try:\n    from dotenv import load_dotenv\n    load_dotenv()\nexcept ImportError:\n    pass\n",
     "try:\n    from dotenv import load_dotenv\n    import sys as _sys_v63d\n    if not (os.path.basename(_sys_v63d.argv[0] or \"\").startswith(\"test_\") or os.getenv(\"GOLDBOT_TEST\") == \"1\"):   # v63d\n        load_dotenv()\nexcept ImportError:\n    pass\n"),
    ("socialagent/daten.py",
     "    if _ENV_GELADEN is False or _ENV_GELADEN != mt:\n",
     "    import sys as _sys_v63d\n"
     "    if os.path.basename(_sys_v63d.argv[0] or \"\").startswith(\"test_\") or os.getenv(\"GOLDBOT_TEST\") == \"1\":   # v63d: Tests nie mit echten Schlüsseln\n"
     "        _ENV_GELADEN = mt\n"
     "    if _ENV_GELADEN is False or _ENV_GELADEN != mt:\n"),
    ("dashboard.py",
     "s.kanal === 'metricool' ? 'über Metricool auf Instagram + TikTok' :",
     "s.kanal === 'metricool' ? 'über Metricool' :"),
]


def main():
    fehler, fertig, gruppen = 0, [], {}
    for datei, alt, neu in P:
        gruppen.setdefault(datei, []).append((alt, neu))
    for datei, paare in gruppen.items():
        p = B / datei
        roh = p.read_bytes().decode("utf-8")
        crlf = "\r\n" in roh
        src = roh.replace("\r\n", "\n")
        geaendert = False
        for alt, neu in paare:
            if neu in src:
                continue
            n = src.count(alt)
            if n != 1:
                print("ANKER fehlt/doppelt (%d) in %s: %s" % (n, datei, alt[:70].replace("\n", " | ")))
                fehler += 1
                continue
            src = src.replace(alt, neu, 1)
            geaendert = True
        if geaendert:
            compile(src, str(p), "exec")
            fertig.append((p, src, crlf))
        else:
            print("schon drin:", datei)
    if fehler:
        print("ABBRUCH: nichts geschrieben"); sys.exit(1)
    for p, src, crlf in fertig:
        s = p.with_name(p.name + ".vor_v63d")
        if not s.exists():
            s.write_bytes(p.read_bytes())
        p.write_bytes((src.replace("\n", "\r\n") if crlf else src).encode("utf-8"))
        print("gepatcht:", p.relative_to(B))
    print("v63d OK")


if __name__ == "__main__":
    main()
