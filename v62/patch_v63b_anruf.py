"""v63b (01.11.): „Ruf mich an“ (Telegram, Dashboard, Discord) → Jarvis ruft sofort an, auch in der Ruhezeit und ohne 6-h-Sperre.
Eigenes Limit für Anrufe auf Wunsch (10 pro Tag, Schutz vor einer Sperre bei CallMeBot); sie zählen nicht gegen die 3 automatischen Anrufe.
„Ruf mich nicht an“ löst nichts aus. Idempotent, CRLF-fest, erst prüfen dann schreiben, Sicherung *.vor_v63b."""
import sys
from pathlib import Path
B = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
P = [
    ("anruf.py", "MAX_TAG = 3\n", "MAX_TAG = 3\nWUNSCH_MAX_TAG = 10                       # v63b: Anrufe, um die du ausdrücklich bittest (eigenes Limit)\n"),
    ("anruf.py",
     "def pruefe_grenzen(schluessel: str, notbremse: bool, jetzt: float, d: dict = None):\n",
     "def pruefe_grenzen(schluessel: str, notbremse: bool, jetzt: float, d: dict = None, auf_wunsch: bool = False):\n"),
    ("anruf.py",
     "    lokal = datetime.fromtimestamp(jetzt)\n    if in_ruhezeit(lokal.hour) and not notbremse:\n",
     "    lokal = datetime.fromtimestamp(jetzt)\n"
     "    if auf_wunsch:                                       # v63b: du hast ausdrücklich gebeten – keine Ruhezeit, keine 6-h-Sperre\n"
     "        tag_w = lokal.strftime(\"%Y-%m-%d\")\n"
     "        n_w = sum(1 for a in d.get(\"anrufe\") or [] if a.get(\"tag\") == tag_w and a.get(\"versucht\") and str(a.get(\"schluessel\", \"\")).startswith(\"wunsch:\"))\n"
     "        return None if n_w < WUNSCH_MAX_TAG else \"heute schon %d Anrufe auf Wunsch (höchstens %d, Schutz vor einer Sperre bei CallMeBot)\" % (n_w, WUNSCH_MAX_TAG)\n"
     "    if in_ruhezeit(lokal.hour) and not notbremse:\n"),
    ("anruf.py",
     "    heute = [a for a in d.get(\"anrufe\") or [] if a.get(\"tag\") == tag and a.get(\"versucht\")]\n",
     "    heute = [a for a in d.get(\"anrufe\") or [] if a.get(\"tag\") == tag and a.get(\"versucht\")\n"
     "             and not str(a.get(\"schluessel\", \"\")).startswith(\"wunsch:\")]      # v63b: Wunsch-Anrufe zählen hier nicht\n"),
    ("anruf.py",
     "def anrufen(grund: str, schluessel: str = None, notbremse: bool = False, jetzt: float = None, sende=None, http_get=None, http_post=None) -> dict:\n",
     "def anrufen(grund: str, schluessel: str = None, notbremse: bool = False, jetzt: float = None, sende=None, http_get=None, http_post=None,\n"
     "            auf_wunsch: bool = False) -> dict:\n"),
    ("anruf.py",
     "        sperre = pruefe_grenzen(schluessel, notbremse, jetzt, d)\n",
     "        sperre = pruefe_grenzen(schluessel, notbremse, jetzt, d, auf_wunsch=auf_wunsch)\n"),
    ("dashboard.py",
     "    # 1b) Frage nach der Stimmung der Nachrichten/Telegram/X (nur Zahlen, nie der rohe Fremdtext)\n",
     "    # 1a) v63b: „Ruf mich an“ → sofort anrufen (auch nachts), „ruf mich nicht an“ → nichts\n"
     "    if anruf_wunsch(text):\n"
     "        import anruf\n"
     "        import time as _t\n"
     "        res = anruf.anrufen(\"Du hast mich gebeten, dich anzurufen.\", \"wunsch:%d\" % int(_t.time()), auf_wunsch=True)\n"
     "        return {\"antwort\": (\"📞 \" + res[\"text\"]) if res.get(\"ok\") else res[\"text\"], \"aktionen\": [], \"bestaetigen\": None,\n"
     "                \"vorschlaege\": jarvis.VORSCHLAEGE, \"fest\": True}\n\n"
     "    # 1b) Frage nach der Stimmung der Nachrichten/Telegram/X (nur Zahlen, nie der rohe Fremdtext)\n"),
    ("dashboard.py",
     "def _jarvis_antwort_kern(text: str, offen, verlauf) -> dict:\n",
     "def anruf_wunsch(text: str) -> bool:\n"
     "    \"\"\"v63b: Bittet der Nutzer ausdrücklich um einen Anruf? (\\\"ruf mich an\\\", \\\"kannst du mich anrufen\\\", \\\"call me\\\"; nie mit \\\"nicht/kein\\\")\"\"\"\n"
     "    n = \" \" + re.sub(r\"[^a-zäöüß ]\", \" \", str(text or \"\").lower()) + \" \"\n"
     "    if any(w in n for w in (\" nicht \", \" kein \", \" keinen \", \" nie \", \" nö \", \" no \", \" don t \", \" dont \")):\n"
     "        return False\n"
     "    return bool(re.search(r\" ruf (mich )?(bitte |mal |jetzt |sofort |gleich )*an | ruf mich | mich (bitte |mal |jetzt |sofort |gleich )*an(rufen)? | anrufen | call me \", n))\n\n\n"
     "def _jarvis_antwort_kern(text: str, offen, verlauf) -> dict:\n"),
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
        s = p.with_name(p.name + ".vor_v63b")
        if not s.exists():
            s.write_bytes(p.read_bytes())
        p.write_bytes((src.replace("\n", "\r\n") if crlf else src).encode("utf-8"))
        print("gepatcht:", p.name)
    print("v63b OK")


if __name__ == "__main__":
    main()
