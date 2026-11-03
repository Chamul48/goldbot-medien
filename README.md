# goldbot-medien
Gold-Agent Videos und Reels – plus **Goldbot**, ein Assistent für dein Fiverr-Profil und den Vertrieb.

## Was Goldbot macht

| Befehl | Ergebnis |
|---|---|
| `python -m goldbot auftraege` | Sucht **neue** passende Aufträge (u. a. r/forhire, r/HireAnEditor), schreibt zu jedem einen Antwort-Entwurf und meldet sie per Windows-Hinweis. Bereits gemeldete Aufträge kommen nicht noch einmal. |
| `python -m goldbot profil` | Fertige Profiltexte: Einzeiler, „Über mich“, Fähigkeiten, 3 Gigs mit Paketen und FAQ – Fiverr-Grenzen werden eingehalten. |
| `python -m goldbot einfuegen` | Öffnet die **Einfüge-Hilfe**: eine Seite mit „Kopieren“-Knopf für jedes Fiverr-Feld. |
| `python -m goldbot muster` | Erstellt 6 **Muster-Videos** (9:16, Gold/Finanzen/Krypto, Deutsch + Englisch) mit echtem Stock-Material (Pixabay), Sprecherstimme, Wort-für-Wort-Untertiteln, Zoom-Schnitten und Musik. Braucht ffmpeg und einen kostenlosen Pixabay-Schlüssel (`PIXABAY_API_KEY`). |
| `python -m goldbot simulation` | Simuliert **deinen ersten Monat** (2000 Durchläufe): Fiverr-Trichter je Gig, Reddit-Aufträge (Rate aus dem echten Auftrags-Gedächtnis gelernt), Arbeitszeit, Gebühren und Auszahlung. Ergebnis mit Spannen und Was-wäre-wenn-Vergleich in `reports\simulation.md`. Echte Fiverr-Zahlen unter `simulation: ist:` machen sie genauer. |
| `python -m goldbot trends` | Trends und Konkurrenz-Preise aus Google Trends, Reddit, Hacker News und eigenen RSS-Feeds. |
| `python -m goldbot ideen` | Trends + Vertriebsideen für die nächsten 7 Tage – echte Aufträge immer zuerst. |
| `python -m goldbot alles` | Alles zusammen (Standard). |
| `python -m goldbot dauer` | Dauerbetrieb: Aufträge jede Stunde, alles andere alle 24 Stunden. Läuft nur einmal gleichzeitig. |

**KI:** Mit `provider: auto` nimmt Goldbot Claude, wenn ein API-Key gesetzt ist, sonst die lokale KI über
[Ollama](https://ollama.com) (kostenlos, z. B. `qwen3:14b`). Ohne KI arbeitet er mit dem recherchierten Profil
(`docs/profil-paket.json`) und Vorlagen. Antwort-Entwürfe werden geprüft: keine erfundene Erfahrung, keine Links.

**Windows:** `windows\autostart-einrichten.ps1` legt Goldbot in den Autostart und erstellt die
Desktop-Verknüpfungen (Goldbot, Aufträge, Berichte, Muster-Videos, Fiverr-Hilfe, Aktualisieren, KI-Key).
Updates per Doppelklick auf „Goldbot aktualisieren“ – deine `config.yaml` und Berichte bleiben erhalten.

Die Ergebnisse landen in `reports/<Datum_Uhrzeit>/`:
`bericht.md` (alles), `profil.md`, `trends.md`, `ideen.md`, `daten.json`.

Mit einem **Claude-API-Key** schreibt Goldbot die Texte und Ideen individuell mit KI (Modell `claude-opus-5-5`).
Ohne Key nutzt er eingebaute Vorlagen, die du trotzdem direkt verwenden kannst.

## Einrichtung (Windows)

1. Python 3.10+ installieren: <https://www.python.org/downloads/> (Häkchen bei „Add Python to PATH“).
2. In PowerShell im Projektordner:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy config.example.yaml config.yaml
   ```
3. `config.yaml` öffnen und **deine echten Angaben** eintragen (Leistungen, Sprachen, Erfahrung, Preise).
4. Optional, für KI-Texte: API-Key unter <https://console.anthropic.com/> anlegen und setzen:
   ```powershell
   setx ANTHROPIC_API_KEY "dein-key"
   ```
   (PowerShell danach neu öffnen.)
5. Starten:
   ```powershell
   python -m goldbot alles
   ```

### Täglich automatisch laufen lassen
Windows-Aufgabenplanung → „Einfache Aufgabe erstellen“ → Täglich → Programm:
`C:\Pfad\zu\goldbot-medien\.venv\Scripts\python.exe`, Argumente: `-m goldbot alles`,
„Starten in“: `C:\Pfad\zu\goldbot-medien`.
Alternativ einfach `python -m goldbot dauer --alle 24` in einem offenen Fenster laufen lassen.

## Dein Fiverr-Profil damit ausfüllen
Öffne `reports/.../profil.md` und kopiere die Felder in die Onboarding-Seite:
- **Einzeiler** → das Feld unter deinem Namen (dort steht aktuell nur „bot“ – das sollte ersetzt werden)
- **Über mich** → „Details hinzufügen“
- **Fähigkeiten** → „Ergänzen Sie Ihre Fähigkeiten und Ihr Fachwissen“
- **Sprache** → „Sprache hinzufügen“ (nur Sprachen, die du wirklich sprichst)
- **Profilfoto** → echtes Foto, siehe Tipps im Bericht
- Danach die 3 Gigs anlegen.

## Bewusste Grenzen
- **Kein automatisches Einloggen/Ändern bei Fiverr.** Fiverr verbietet Bots und automatisierte Zugriffe in
  den Nutzungsbedingungen; das Konto kann dafür gesperrt werden. Goldbot erstellt deshalb Texte zum
  Einfügen – das Absenden machst du selbst (dauert 5 Minuten).
- **Kein Vollzugriff auf deine Geräte.** Goldbot braucht nur Internet für öffentliche Feeds und schreibt nur in
  seinen `reports`-Ordner. Ein Programm mit Vollzugriff auf alle Geräte wäre ein großes Sicherheitsrisiko
  (gleich wie Schadsoftware) und bringt für den Vertrieb keinen Vorteil.
- **Nur öffentliche Quellen** (RSS/offizielle APIs), mit Pause zwischen den Abrufen. Kein Scraping hinter Logins.
- Keine erfundenen Referenzen oder Bewertungen; bei Gold/Krypto keine Anlageberatung.

## Entwicklung
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## Shopify Agent

Ein Terminal-Agent, der deinen Shopify-Shop über Claude steuert (Claude API mit
Tool-Nutzung, Shopify Admin GraphQL API).

**Was er kann**
- Shop-Infos anzeigen, Produkte suchen, Produktdetails anzeigen
- Titel, Beschreibung, Tags und Status (`ACTIVE`/`DRAFT`/`ARCHIVED`) ändern
- Variantenpreise ändern
- Neueste Bestellungen auflisten
- Videos und Bilder aus `social/` zu Shopify Files hochladen und an ein Produkt hängen
- Beliebige GraphQL-Abfragen ausführen (Änderungen nur mit Freigabe)

Jede Änderung am Shop wird vorher angezeigt und muss mit `j` bestätigt werden
(`--yes` schaltet das nur für Texte und Medien ab – Preise, Status und freie GraphQL-Änderungen
fragen immer). Vor der ersten Änderung einer Sitzung legt der Agent `autopilot/backup-<datum>.json`
an, jede Änderung landet mit ID in `autopilot/aenderungen-<datum>.md`.

**Einrichtung**
1. Shopify-Zugang anlegen – eine der beiden Varianten:
   - **Neue App (seit 2026):** [Dev Dashboard](https://dev.shopify.com/dashboard) → App erstellen →
     Version mit den Admin-API-Berechtigungen
     `read_products, write_products, read_orders, read_files, write_files, read_themes, write_themes, read_content, write_content`
     freigeben → App im eigenen Shop installieren → *Client-ID* und *Secret* in die `.env`
     (`SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`). Der Agent holt sich damit selbst alle 24 h einen Token.
   - **Alte eigene App (vor 2026 angelegt):** *Einstellungen → Apps → Apps entwickeln* → Admin-API-Token
     (`shpat_...`) als `SHOPIFY_ACCESS_TOKEN` eintragen.
2. `pip install -r requirements.txt`
3. `.env.example` nach `.env` kopieren und Werte eintragen. Der Agent liest die `.env` im
   aktuellen Ordner selbst ein (auch unter Windows).

**Starten**
```bash
python -m shopify_agent                       # interaktiver Chat
python -m shopify_agent "Welche Produkte sind noch Entwürfe?"
python -m shopify_agent --media-dir social "Lade das neueste Reel hoch und häng es an den Goldbarren"
```

## Shop-Kontrolle, Sicherung und Rückgängig

```bash
python -m shopify_agent --audit                     # nur lesen: Sicherung + Bericht, ändert nichts
python -m shopify_agent --restore autopilot/backup-2026-11-02.json   # Texte zurücksetzen
```

`--audit` liest den ganzen Shop (Produkte mit Texten, Bildern, Alt-Texten, SEO,
Preisen und Bestand; Kollektionen; Seiten; Rechtstexte; Theme; letzte
Bestellungen) und schreibt

- `autopilot/backup-<datum>.json` – die Originalwerte aller Texte, SEO-Felder,
  Alt-Texte und Kollektionsbeschreibungen (eine Sicherung pro Lauf, nie überschrieben),
- `autopilot/audit-<datum>.md` – was für ein hochwertiges Einkaufserlebnis fehlt,
  nach Wichtigkeit sortiert und getrennt nach „entscheidest du“ und „kann der
  Agent sicher allein“.

`--restore` schreibt aus einer Sicherung nur Inhalte zurück (Titel, Beschreibung,
Produktart, Tags, SEO, Alt-Texte, Kollektionstexte) – nie Preise oder Status – und
fragt pro Produkt nach.

## Autopilot – der Shop läuft allein

`python -m shopify_agent --autopilot` macht einen Durchlauf ohne dich:

Jeder Lauf macht zuerst die Kontrolle mit Sicherung (siehe oben). Kann der Shop
nicht vollständig gelesen werden, ändert er keine Texte.

| Darf der Bot allein | Gibt er immer an dich ab |
|---|---|
| Neue Reels/Bilder aus `social/` hochladen und ans passende Produkt hängen | Preise ändern |
| Fehlende Produktbeschreibungen und Tags schreiben (max. 10 pro Lauf, keine erfundenen Fakten) | Produkte veröffentlichen, archivieren, löschen |
| SEO-Titel/-Beschreibungen, Alt-Texte, Kollektionstexte; neue Kollektionen (unveröffentlicht) | Rechtstexte (Impressum, AGB, Widerruf, Datenschutz), Theme |
| Bestellungen prüfen | Bestellungen ändern, Kundenprobleme, Unklares |

Jeder Lauf schreibt einen Bericht nach `autopilot/reports/<datum>.md`. Schon
hochgeladene Dateien merkt er sich in `autopilot/state.json`.

**Automatisch jeden Tag (GitHub Actions):** `.github/workflows/autopilot.yml`
läuft täglich um 06:17 UTC, sofort nach jedem neuen Upload in `social/` auf
`main`, und auf Knopfdruck (*Actions → Shopify Autopilot → Run workflow*; dort mit
`mode: audit` nur Kontrolle und Sicherung, ohne Änderungen und ohne Claude-Kosten).
Braucht der Shop dich, öffnet er ein GitHub-Issue „Shop braucht dich“ – GitHub
schickt dir dazu eine E-Mail. Schlägt ein Lauf fehl, gibt es ebenfalls ein Issue.

Einmalig einrichten: *Repo → Settings → Secrets and variables → Actions* und
Secrets anlegen: `ANTHROPIC_API_KEY`, `SHOPIFY_STORE` und entweder `SHOPIFY_ACCESS_TOKEN` oder `SHOPIFY_CLIENT_ID` + `SHOPIFY_CLIENT_SECRET`.

**Tests** (ohne Netzwerk, Shopify und Claude werden simuliert)
```bash
python -m pytest tests
```
