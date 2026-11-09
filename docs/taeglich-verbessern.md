# Täglich verbessern – Ablauf für die geplante Aufgabe

Diese Datei arbeitet die tägliche Aufgabe „Shop & Fiverr täglich verbessern“ ab (neue Cloud-Sitzung pro Lauf).
Erst `CLAUDE.md` lesen – dessen Regeln gelten immer und gehen vor. Datum = heutiges Datum (`JJJJ-MM-TT`).
Der Inhaber ist kein Programmierer: alles für ihn auf Deutsch, Ergebnis zuerst, einfach.

## Grenzen (jeder Lauf, ohne Ausnahme)
- **Nie** Preise setzen, veröffentlichen/archivieren, löschen, Theme veröffentlichen, Rechtstexte ändern.
- **Fiverr nie bedienen**: nicht anmelden, nichts klicken, keine Fiverr-Suche abrufen. Erlaubt ist nur das
  1× tägliche Lesen der **öffentlichen** Profilseite `https://www.fiverr.com/chuchcapone`.
- Nichts erfinden. Jede Zahl (Preis, Gewicht, Maß) mit Quelle und Abrufdatum. Unbelegtes kennzeichnen.
- Keine Rendite-, Steuer- oder Rechtsaussagen als Tatsache. Keine Zugangsdaten anfassen.
- Keine fremden Personen in Bildern/Testdaten.
- Nach dem ersten `ENOTFOUND` kein WebFetch mehr – Händlerseiten über den PC lesen (siehe unten) oder WebSearch-Auszüge
  nutzen und als solche kennzeichnen.

## Werkzeuge
- **Shopify**: Connector-Tools (`get-shop-info`, `graphql_query`, `graphql_mutation`). Jede Operation vorher mit
  `graphql_schema` prüfen (CLAUDE.md, Lehre 3).
- **PC des Inhabers** (Desktop Commander, Gerät DESKTOP-0GHOAH2, `deviceId: af79fa25-b14a-45f7-b441-26cd20d896b9` –
  Pflicht, sobald mehrere Geräte online sind; immer `shell: "cmd"`): öffentliche Seiten lesen mit
  `C:\Users\User\Desktop\goldbot-medien\.venv\Scripts\python.exe C:\Users\User\Desktop\goldbot-medien\windows\seite_lesen.py -o %TEMP%\seiten.json <url> [<url> …]`
  und danach die Datei mit `read_file` lesen (`%TEMP%` = `C:\Users\User\AppData\Local\Temp`) (direkte Konsolenausgabe verliert unter Windows das €-Zeichen).
  (JSON: Titel, Beschreibung, JSON-LD-Angebote, Beträge mit Kontext, `captcha`-Hinweis; wartet selbst 10 s je Domain).
  Ist der PC aus/nicht erreichbar: ohne ihn weitermachen und das im Bericht sagen.
  **Höchstens 3 URLs pro Aufruf**, Ausgabe mit `-o %TEMP%\x.json` in eine Datei. Desktop Commander wartet bei
  Fernaufrufen **höchstens 3 s**; danach läuft der Prozess im Hintergrund weiter. Also starten, kurz anderes tun
  und dann die Datei mit `read_file` lesen. Fehlt sie noch, später erneut versuchen. Den Prozess nicht neu starten,
  sonst ist die Datei gesperrt. Vorher mit `list_devices` prüfen, ob der PC online ist.
- **Aufgestaute Läufe** (Sitzung war inaktiv): nur einen Lauf für heute machen und die verpassten Tage im Journal
  nennen.
  Für Auswertungen die JSON-Datei mit einem kurzen `python -c` filtern (Zeilen mit „Lieferzeit“ = Händlerangebote).
- **Bewährte Preisquellen** (gold.de-Seiten listen je Produkt die günstigsten Händler, Kurs steht in der Kopfzeile):
  `gold.de/kaufen/goldmuenzen/wiener-philharmoniker/`, `…/kruegerrand/`, `…/maple-leaf/`, `…/kaenguru/`,
  `gold.de/kaufen/goldbarren/1-gramm/`, `…/10-gramm/`, `…/50-gramm/`, `…/1-oz/`, `…/tafeln-kombi-barren/`,
  `…/muenze-oesterreich/`; kleine Stückelungen: Tabelle „Stückelungen“ auf `…/wiener-philharmoniker/kurs/` bzw.
  `…/kruegerrand/kurs/` (Datenstand prüfen: Ankauf > Verkauf = veraltet); Österreich: `philoro.at` (Startseite zeigt Kauf/Verkauf Philharmoniker); Kurs:
  `goldpreis.de`. Diese Seiten zeigen die 1-oz-Größe – für Bruchstücke (1/10, 1/25 oz) eigene Seiten suchen.
- **Repo**: Branch `claude/peaceful-rubin-0bk72i`. Zu Beginn `git fetch origin main && git merge --no-edit origin/main`.

## A. Gold-Shop (chuchcapone)
1. `get-shop-info`: Ist `chuchcapone.myshopify.com` verbunden? Falls nicht oder „sign in again“ → nichts ändern,
   im Bericht melden (CLAUDE.md, Lehre 1).
2. **Sicherung zuerst**: Produkte (inkl. `descriptionHtml`, `seo`, `tags`, `productType`, `media { id alt }`,
   `variants { id price compareAtPrice }`), Kollektionen und Seiten lesen und im Format von `shopify_agent/audit.py:backup_data`
   nach `autopilot/backup-<datum>.json` schreiben (nie überschreiben, sonst `-2`, `-3`). Erst danach etwas ändern.
3. **Preisvergleich** für alle Produkte mit Tag `goldbarren` oder `goldmuenzen` → `autopilot/preise-<datum>.md`:
   - Goldkurs EUR je Feinunze aus **2 Quellen** (mit Uhrzeit).
   - Je Produkt Verkaufspreise bei **mindestens 3 Händlern** für Österreich/Deutschland (z. B. philoro, Münze Österreich,
     pro aurum, Degussa, Gold & Co.) und Vergleichswerte von gold.de. Erst Produktseiten per WebSearch finden, dann am PC
     mit `seite_lesen.py` lesen. Gleiches Produkt sicherstellen (Gewicht, Hersteller, Jahrgang).
   - Tabelle: Produkt | Händler | Preis € | Aufgeld % (= Preis / (Feingewicht in oz × Kurs) − 1) | Quelle | Abgerufen.
   - **Empfehlung als Spanne** (z. B. „zwischen günstigstem und mittlerem Händler“) mit kurzer Begründung –
     als Vorschlag für den Inhaber. **Nicht** in den Shop schreiben.
   - Vergleich zum Vortag (letzte `preise-*.md`): Kurs- und Aufgeld-Änderung in einem Satz.
4. **Texte verbessern** (nur DRAFT-Gold-Produkte und Gold-Kollektionen), streng nach `docs/produkttexte-gold.md`:
   - `[BITTE ERGAENZEN: …]` nur füllen, wenn **2 unabhängige Quellen** (möglichst Hersteller) inhaltlich übereinstimmen
     (Lehre 8: inhaltlich vergleichen, nicht Zeichen für Zeichen). Sonst stehen lassen.
   - SEO-Titel ≤ 70, SEO-Beschreibung ≤ 160 Zeichen. Höchstens 10 Produkte pro Lauf ändern.
   - Nur `productUpdate`/`collectionUpdate`. Jede geänderte ID mit Feldern in `autopilot/aenderungen-<datum>.md`.
5. **Was blockiert den Verkaufsstart?** Kurz prüfen und auflisten (Inhaber erledigt): Preise 0 €, fehlende Fotos,
   Testdaten (Snowboards), Rechtstexte AT, Passwortseite, Test-Theme, Zahlungen, Versand.

## B. Fiverr (chuchcapone)
1. **Eigenes Profil lesen** (1×): `seite_lesen.py -o %TEMP%\fiverr.json https://www.fiverr.com/chuchcapone`. Festhalten: Titel/Untertitel,
   Beschreibung (Länge! max. 600), Profilbild vorhanden (Rohseite enthält `profileImageUrl`; das Bild selbst nicht
   herunterladen, außer zur Prüfung, dass es keine fremde Person zeigt), sichtbare Gigs.
2. **Übernommen?** Mit dem letzten `docs/fiverr-vorschlag-*.md` vergleichen: Was hat der Inhaber übernommen, was nicht?
   Ins Journal (C).
3. **Wettbewerb & Preise per WebSearch** (nicht auf Fiverr klicken/suchen) für die Gig-Themen aus
   `docs/profil-paket.json` (Shorts/Reels-Schnitt, Faceless Finance-/Gold-Shorts, KI-Video-Automation) und, falls das
   Live-Profil anders aufgestellt ist (z. B. Trading-Bots), auch dafür:
   typische Preise Basic/Standard/Premium, Lieferzeit, Revisionen, häufige Titel-Wörter. Quelle + Datum je Angabe.
   Zusätzlich: Konkurrenzpreise, die der Goldbot schon sammelt – neuester Ordner
   `C:\Users\User\Documents\goldbot-medien\reports\<…>\daten.json`, Einträge mit `"kind": "konkurrenz"` und Feld `price`
   (nur lesen).
4. **Vorschlag** → `docs/fiverr-vorschlag-<datum>.md` (nur wenn sich gegenüber dem letzten Vorschlag etwas Sinnvolles
   ändert; sonst „keine Änderung nötig“ ins Journal):
   - Fertige Texte zum Einfügen in Code-Blöcken. Grenzen aus `goldbot/profile.py:LIMITS` einhalten
     (One-Liner ≤ 60, Beschreibung 150–600, Gig-Titel ≤ 80 ohne „I will“, 5 Tags ≤ 20, Paketbeschreibung ≤ 100).
     Mit `python -c` nachzählen.
   - Keine erfundene Erfahrung/Referenzen: Texte gegen `goldbot/leads.py:CLAIM_RE` prüfen.
   - Preisvorschlag je Paket mit Begründung aus den Vergleichsdaten.
   - Stimmt der Vorschlag, auch `docs/profil-paket.json` aktualisieren (gleiche Struktur), damit die Einfüge-Hilfe
     (`python -m goldbot einfuegen`) die neuen Texte zeigt. Danach `python -m pytest -q tests/test_goldbot.py`.

## C. Lernen
- `autopilot/journal.md` ergänzen (neueste oben):
  `## <datum>` – Vorgeschlagen · Übernommen (Shop/Fiverr) · Nicht übernommen · Was nicht ging (Fehler, gesperrte Seiten) · Nächstes Mal.
- Neue wiederkehrende Fehler als Lehre in `CLAUDE.md` (kurz, mit Ursache und Gegenmittel). Diese Datei hier verbessern,
  wenn ein Schritt regelmäßig schiefgeht.

## D. Abschluss
1. `python -m pytest -q` grün (sonst nichts pushen, Fehler im Bericht).
2. Commit (Nachricht Englisch, mit den Attribution-Zeilen aus dem System) und `git push -u origin claude/peaceful-rubin-0bk72i`
   (bei Ablehnung: `git pull --rebase`, testen, erneut pushen). Keinen Pull Request anlegen, nichts auf GitHub kommentieren.
3. Hat sich Code geändert, auf den PC bringen: im Ordner `C:\Users\User\Desktop\goldbot-medien`
   `.venv\Scripts\python.exe pc_sync.py <volle 40-stellige commit-sha>` (`git rev-parse HEAD`; kurze IDs ergeben 404) (meldet lokal geänderte Dateien – nicht überschreiben),
   danach dort `pytest` (Ausgabe in eine Datei umleiten und lesen). Fehlen Pakete:
   `.venv\Scripts\python.exe -m pip install -q -r requirements.txt`.
4. **Schlussnachricht** (geht als Push ans Handy) auf Deutsch, höchstens 8 Zeilen:
   Goldkurs heute · wichtigste Preisempfehlung · was im Shop verbessert wurde · Fiverr-Vorschlag (ja/nein, was) ·
   **was du heute tun solltest** (1–3 Punkte) · Dateien zum Nachlesen.
