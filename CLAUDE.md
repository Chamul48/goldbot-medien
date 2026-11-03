# goldbot-medien – Arbeitsregeln für Claude

Antworten auf Deutsch, Ergebnis zuerst, einfach erklärt (der Inhaber ist kein Programmierer).

## Projekt
- `shopify_agent/` – Shopify-Agent (Chat, `--autopilot`, `--audit`, `--restore`), Tests in `tests/` (`python -m pytest tests`).
- Shop: **chuchcapone** (`chuchcapone.myshopify.com`, AT, EUR). Der frühere Shop „Jamul$“ ist geschlossen,
  „Mein Shop 2“ (`ha1m9z-rp`) wird nicht genutzt. Sortiment: Gold (Barren, Münzen, Geschenke).
- Stand und Änderungen am Shop: `autopilot/audit-*.md`, `autopilot/aenderungen-*.md`, Sicherungen `autopilot/backup-*.json`.
- Texte für Gold-Produkte: immer nach `docs/produkttexte-gold.md`.
- Windows-PC des Inhabers: `C:\Users\User\Desktop\goldbot-medien` (eigene `.venv`, `.env`, Start: „Shop starten.bat“).

## Was Claude allein darf – und was nie
- Allein (umkehrbar, vorher `autopilot/backup-<datum>.json` schreiben): Produkttexte, SEO, Alt-Texte, Tags,
  Kollektionen anlegen/beschreiben (unveröffentlicht), Seiten als Entwurf (`isPublished: false`), Produkte als `DRAFT`.
- Nie selbst, nur empfehlen: Preise, Veröffentlichen/Archivieren, Theme veröffentlichen, Rechtstexte
  (Impressum, AGB, Widerruf, Datenschutz), Löschen, Bestellungen, Zugangsdaten anlegen oder eingeben.
- Nie erfinden: Gewichte, Feingehalte, Hersteller, Zertifikate, Preise, Lieferzeiten. Fehlt etwas: `[BITTE ERGAENZEN: …]`.
- Keine Rendite-, Steuer- oder Rechtsaussagen als Tatsache.
- Jede Änderung mit ID in `autopilot/aenderungen-<datum>.md` festhalten.

## Lehren aus Fehlern (nicht wiederholen)
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
