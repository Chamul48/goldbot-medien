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

## Andere Agenten auf demselben PC (nicht verwechseln)
- **Gold-Bot** (Trading-Spielgeld + Social-Autopilot): `C:\Users\User\Desktop\golden_bot`, eigene Regeln im
  Skill `gold-bot-pc`. Andere Claude-Sitzungen arbeiten dort parallel → nur lesen/prüfen, ändern nur nach
  Rückfrage beim Nutzer. Seine `.env` liefert den Pixabay-Schlüssel für die Muster-Videos (nur lesen).
- **Shopify-Agent**: Paket `shopify_agent/` (seit 2026-11-03 in `main`), am PC `C:\Users\User\Desktop\goldbot-medien`
  (Desktop, nicht Documents!), Start „Shop starten.bat“, Abgleich nur mit `python pc_sync.py <commit-sha>`.
  Regeln: Abschnitt „Shopify-Agent“ unten.

## Stand 2026-11-03
- Goldbot 0.6.0 läuft im Dauerbetrieb (geplante Aufgabe „Goldbot“). 122 Tests grün, alles in `main`.
- `python -m goldbot simulation`: Monte-Carlo des ersten Monats (Fiverr + Reddit). Quoten sind Beta-Annahmen,
  `simulation.ist` (echte Fiverr-Zahlen) verrechnet sie; Reddit-Rate wird aus `.gesehen.json` gelernt
  (erster Abruf = Rückstand, zählt nicht). Ergebnis 1. Lauf: Median ~130 $, Reddit bringt ~80 %.
- Muster-Videos neu: `python -m goldbot muster` (alle) bzw. `--nur krypto_de finance_en` (einzelne).
  Clip pro Szene über `DEMOS[...]["clips"]` steuern; vorher Treffer prüfen (Tags + Bild ansehen).
- Shopify-Agent: Review-Fixes in Commit `5d89200` am PC eingespielt; läuft erst nach Neustart des Fensters.
- Offen beim Nutzer: Fiverr-Profil mit „Goldbot Fiverr-Hilfe“ ausfüllen, Muster-Videos als Portfolio
  hochladen, `[PORTFOLIO-LINK]` ersetzen, Reddit-Aufträge selbst beantworten.

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
- **Muster-Videos** = echtes Material: Pixabay-Clips (Schlüssel aus `muster.pixabay_env`, Standard
  `~/Desktop/golden_bot/.env`, nie ausgeben), Stimme edge-tts, Untertitel als ASS (libass,
  `fontsdir=.`). Pixabay-„popular“ liefert Unpassendes → nur Treffer mit ALLEN Suchwörtern in den Tags, echtes
  Video vor Animation, kein Green-Screen/Freistell-Material.
  Nutzer will **wenig Text** und **hohe Bildqualität**: max. 2 Wörter je Untertitel, kein Zähler/Etikett;
  Zoom per `scale …:eval=frame` (zoompan ruckelt). Test am PC: `reports\muster_test.py` lädt `demo.py`
  per Commit-SHA (raw.githubusercontent cacht Branch-URLs).
- **ffmpeg drawbox kennt keine Zeit** (`t` = Rahmendicke) → animierte Balken per `overlay` mit `t`.
- **Gig-Titelbilder:** links kurzer Text aus `demo.COVER_TEXT` (Pillow misst die Breite, max. 520 px), rechts
  3 Standbilder als Handys (`COVER_STILLS`), Shorts-Untertitel auf dem mittleren (`COVER_CAPTION`). Gig 3 zeigt
  drei Kanäle (Krypto/Ozean/Finanzen, Ozean-Videos `ozean_de`/`ocean_en`) = Automatisierung, nicht Krypto. Kleine Etiketten sind als Vorschau unlesbar. Nur die Titelbilder neu: `demo.render_covers(...)` statt ganzem `muster`.
- **Fiverr-Paketbeschreibung max. 100 Zeichen**; Gig-Titel ohne „I will“ kopieren (Fiverr setzt es davor).
- **Update-Skript** startet Goldbot nach einem Fehler wieder; `$ProgressPreference = 'SilentlyContinue'`.
- **Testbilder nie mit echten fremden Personen zeigen.** Eine Vorschau mit einem bekannten Fußballer (OpenCV-Beispiel)
  wurde vom Nutzer heruntergeladen und als Fiverr-Profilbild hochgeladen. Für Tests nur neutrale/eigene Motive,
  Testdateien nie in den Chat oder auf den PC legen.
- **Fiverr-Beschreibung max. 600 Zeichen** – längere Texte schneidet Fiverr mitten im Wort ab.
- `reports\` und `config.yaml` sind nicht im Repo – nichts Persönliches committen.

## Shopify-Agent (`shopify_agent/`)

### Projekt
- `shopify_agent/` – Shopify-Agent (Chat, `--autopilot`, `--audit`, `--restore`), Tests in `tests/` (`python -m pytest tests`).
- Shop: **chuchcapone** (`chuchcapone.myshopify.com`, AT, EUR). Der frühere Shop „Jamul$“ ist geschlossen,
  „Mein Shop 2“ (`ha1m9z-rp`) wird nicht genutzt. Sortiment: Gold (Barren, Münzen, Geschenke).
- Stand und Änderungen am Shop: `autopilot/audit-*.md`, `autopilot/aenderungen-*.md`, Sicherungen `autopilot/backup-*.json`.
- Texte für Gold-Produkte: immer nach `docs/produkttexte-gold.md`.
- Windows-PC des Inhabers: `C:\Users\User\Desktop\goldbot-medien` (eigene `.venv`, `.env`, Start: „Shop starten.bat“).

### Was Claude allein darf – und was nie
- Allein (umkehrbar, vorher `autopilot/backup-<datum>.json` schreiben): Produkttexte, SEO, Alt-Texte, Tags,
  Kollektionen anlegen/beschreiben (unveröffentlicht), Seiten als Entwurf (`isPublished: false`), Produkte als `DRAFT`.
- Nie selbst, nur empfehlen: Preise, Veröffentlichen/Archivieren, Theme veröffentlichen, Rechtstexte
  (Impressum, AGB, Widerruf, Datenschutz), Löschen, Bestellungen, Zugangsdaten anlegen oder eingeben.
- Nie erfinden: Gewichte, Feingehalte, Hersteller, Zertifikate, Preise, Lieferzeiten. Fehlt etwas: `[BITTE ERGAENZEN: …]`.
- Keine Rendite-, Steuer- oder Rechtsaussagen als Tatsache.
- Jede Änderung mit ID in `autopilot/aenderungen-<datum>.md` festhalten.

### Tägliche Verbesserung (Shop + Fiverr)
- Geplante Claude-Code-Aufgabe **„Shop & Fiverr täglich verbessern“** (täglich 19:17 Wiener Zeit, neue Cloud-Sitzung,
  Connectors Shopify + Remote Desktop Commander) arbeitet `docs/taeglich-verbessern.md` ab: Preisvergleich →
  `autopilot/preise-<datum>.md`, Fiverr-Vorschlag → `docs/fiverr-vorschlag-<datum>.md`, Lernkurve → `autopilot/journal.md`.
- Abschalten/ändern: claude.ai → Code → geplante Aufgaben, oder in einer Sitzung `list_triggers` / `update_trigger enabled=false`.
- Öffentliche Seiten vom PC lesen: `windows/seite_lesen.py` (Cloud-WebFetch ist für Händlerseiten gesperrt).

### Lehren aus Fehlern (nicht wiederholen)
1. **Shopify-Connector**: Connectors werden nur beim **Start einer Sitzung** geladen. Meldet ein Tool „sign in again“,
   hilft nur: auf claude.ai → Einstellungen → Connectors neu verbinden **und eine neue Sitzung starten**.
   Vorher `get-shop-info` prüfen, *welcher* Shop verbunden ist (einmal war es ein geschlossener Shop).
2. **Fremde Apps**: Unter „Claude“ im Shopify App Store gibt es Apps anderer Firmen (z. B. `…ondigitalocean.app`).
   Der echte Weg läuft nur über claude.ai → Connectors; die Anmeldeseite muss auf `shopify.com` liegen.
3. **GraphQL nie aus dem Gedächtnis**: Vor dem Einsatz jede Operation über den Connector (`graphql_schema` bzw.
   eine lesende `graphql_query`, die serverseitig validiert) gegen das Live-Schema prüfen. 2026-10 hat z. B.
   `Collection.ruleSet` und `collectionCreate/Update(input:)` abgelöst → `collection:` mit `sources`.
4. **PC-Abgleich**: Auf dem PC arbeiten auch andere Sitzungen. Einmal hat ein Abgleich deren lokale
   Verbesserungen überschrieben. Code nur noch mit `python pc_sync.py <commit>` auf den PC bringen – das Skript
   überspringt Dateien, die seit dem letzten Abgleich lokal geändert wurden, und meldet sie.
5. **Windows**: Pfade für Zustandsdateien mit `as_posix()` speichern; `.env` liest der Agent selbst ein;
   Platzhalter aus `.env.example` (`shpat_...`, `dein-shop…`) gelten als leer.
6. **Tests isolieren**: Tests, die Umgebungsvariablen lesen, mit `monkeypatch.chdir(tmp_path)` von einer echten
   `.env` abschirmen.
7. **Workflow-Agenten, die Dateien bearbeiten**: Ihr Rückgabewert ist oft nur eine Zusammenfassung. Nie den
   Rückgabewert blind in eine Datei schreiben, wenn der Agent die Datei selbst bearbeitet haben könnte – erst
   `git diff`/Länge prüfen. Besser: Agenten ausdrücklich sagen „keine Dateien schreiben, Inhalt nur zurückgeben“.
8. **Prüf-Abgleich zweier Agenten**: Nie Zeichen für Zeichen vergleichen („AG (Wien)“ ≠ „AG, Wien“ hat alle
   12 Produkte verworfen). Ein Abgleich-Agent vergleicht inhaltlich und verwirft nur echte Widersprüche.
9. **Netzwerk in der Cloud-Sitzung**: WebFetch auf Händler- und Herstellerseiten (gold.de, philoro.at,
   muenzeoesterreich.at, kettner-edelmetalle.de, …) ist von der Netzwerkregel gesperrt (`ENOTFOUND`); nur
   WebSearch-Auszüge gehen. Agenten anweisen: nach dem ersten `ENOTFOUND` nicht weiter WebFetch versuchen,
   sondern mit Suchauszügen arbeiten und das kennzeichnen. Freigabe nur durch den Inhaber (Umgebung → Netzwerk →
   Allowed domains).
10. **Zugangsdaten**: Werte nie in den Chat. Auf dem PC nur über `eintragen.py` (Zwischenablage) bzw.
    `env_pruefen.py` (zeigt nur „gesetzt/fehlt“).
11. **Review 2026-11-03** (behoben, Tests in `tests/test_review_fixes.py`): Produktabfrage lag über Shopifys
    Kostengrenze 1000 (jetzt `PRODUCT_PAGE = 10`); abgeschnittene/abgelehnte Antworten ließen ein `tool_use` ohne
    `tool_result` zurück (jede weitere Chat-Anfrage HTTP 400); `--yes` gab auch Preise/Status frei; Chat schrieb ohne
    Sicherung; Änderungen wurden nicht protokolliert; keine Wiederholung bei THROTTLED/429/5xx; Dateien ohne
    `encoding="utf-8"` (Windows cp1252). Gilt auch für Tests: `read_text`/`write_text` mit Umlauten immer mit `encoding="utf-8"`, sonst schlagen sie nur auf dem PC fehl – nach jedem PC-Abgleich dort `pytest` laufen lassen.
