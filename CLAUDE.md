# Goldbot – Hinweise für Claude

Nutzer schreibt Deutsch. Alles, was auf seinen Geräten erscheint (Fenster, Meldungen, Berichte),
ist Deutsch mit echten Umlauten. Fiverr-Texte und Reddit-Antworten bleiben Englisch (Kundensprache).

## Projekt
- Python-Paket `goldbot/`, Start mit `python -m goldbot <befehl>`; Tests: `python -m pytest -q`.
- Läuft beim Nutzer auf Windows 11 (`C:\Users\User\Documents\goldbot-medien`, venv `.venv`),
  erreichbar über Desktop Commander (Gerät DESKTOP-0GHOAH2). Kein Git auf dem PC – Updates über
  `windows\aktualisieren.ps1` (lädt `main` als ZIP, behält `config.yaml` und `reports\`).
- Lokale KI: Ollama aus dem AMD AI Bundle, Modell `qwen3:14b` (RX 9070). Kein Claude-API-Key gesetzt.
- Fiverr wird nie automatisch bedient (Bot-Erkennung, Nutzungsbedingungen) – nur Texte zum Einfügen.

## Gelernt (bitte beachten)
- **Remote gestartete Prozesse sterben.** Was über Desktop Commander mit `Start-Process` gestartet
  wird, endet mit dessen Sitzung (auch sichtbare Fenster). Goldbot daher immer über die geplante
  Aufgabe starten: `Start-ScheduledTask -TaskName Goldbot`.
- **Reddit drosselt anonyme Abrufe (HTTP 429).** Alle Subreddits in EINEM Sammel-Feed abrufen
  (`r/a+b+c/new/.rss`), das echte Subreddit steht im Atom-`<category term=…>`.
- **Auftragserkennung:** Viele Posts in Auftrags-Subreddits sind Anbieter („For hire“, „I'm a video
  editor…“, „disponível“) oder Fragen. Neue Regeln immer mit echten Titeln in `JOB_CASES` testen.
- **Lokale KI erfindet Erfahrung** („I specialize…“). Entwürfe laufen durch `CLAIM_RE`; das geprüfte
  Recherche-Profil (`docs/profil-paket.json`) hat Vorrang vor der lokalen KI.
- **Windows PowerShell 5.1** liest `.ps1` ohne BOM als ANSI → Umlaute kaputt. `.ps1` mit UTF-8-BOM
  speichern; `$args` ist reserviert; `Copy-Item ordner ziel -Recurse` legt `ziel\ordner` an, wenn
  `ziel` existiert → `ordner\*` kopieren.
- **`.bat` braucht CRLF.** Mit reinen LF-Zeilenenden (plus UTF-8/`chcp 65001`) führt cmd.exe Bruchstücke
  aus („Der Befehl "d" …“) und beendet sich mit Code 0. `.gitattributes` hält `*.bat`/`*.ps1` auf CRLF.
- **ffmpeg drawtext:** `%` ist Platzhalter → `expansion=none`; Ausdrücke mit Kommas in `'…'`.
- **Doppelstart:** Dauerbetrieb hält eine Datei-Sperre (`reports\.dauer.lock`); zweiter Start endet mit Code 2.
- **Prozess-Filter:** Beim Beenden per Befehlszeile (`-like '*xyz*'`) den eigenen Prozess (`$PID`)
  ausnehmen – sonst beendet sich der Befehl selbst.
- **Fehlersuche:** Protokoll in `reports\goldbot.log` (rotiert nur im Dauerbetrieb, 3 × 1 MB). Auch eine
  kaputte `config.yaml` landet dort (das Fenster schließt sich sonst ungesehen).
- **Auftrag vor Anbieter:** Ein `[Hiring]`-Tag schlägt „DM me“/„I'm a creator“; Themenwörter („tips“,
  „How to“) zählen bei Tag nicht als Frage, ein Betrag hebt „revenue share“ auf. Starke Anbieter-Zeichen
  (`FORHIRE_STRONG_RE`) vs. schwache (`FORHIRE_WEAK_RE`, nur ohne Auftrags-Satz) – siehe `trends.is_offer`.
- **Reddit-Dedupe nach URL**, nicht nach Titel (viele Aufträge heißen gleich).
- **Feeds als Bytes parsen** (`resp.content`), sonst Umlaute kaputt ohne charset; unlesbare/leere Feeds
  zählen als „nicht erreichbar“.
- **Eingeschränkter Komplett-Lauf** (kein Netz/keine KI direkt nach der Anmeldung) wird nach 15 min
  wiederholt (max. 3×), die Aufgabe startet 1 min nach der Anmeldung.
- **Gedächtnis atomar schreiben** (`.tmp` + `os.replace`); unlesbares wird als `.defekt` gesichert.
- **ffmpeg drawbox kennt keine Zeit** (`t` = Rahmendicke) → animierte Balken per `overlay` mit `t`.
- **Fiverr-Paketbeschreibung max. 100 Zeichen**; Gig-Titel ohne „I will“ kopieren (Fiverr setzt es davor).
- **Update-Skript** startet Goldbot nach einem Fehler wieder; `$ProgressPreference = 'SilentlyContinue'`.
- `reports\` und `config.yaml` sind nicht im Repo – nichts Persönliches committen.
