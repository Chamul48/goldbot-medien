# goldbot-medien
Gold-Agent Videos und Reels

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
(`--yes` schaltet das ab).

**Einrichtung**
1. In Shopify: *Einstellungen → Apps → Apps entwickeln* → App erstellen, Admin-API-Berechtigungen
   `read_products, write_products, read_orders, read_files, write_files, read_themes, write_themes, read_content, write_content` vergeben, installieren und
   den Admin-API-Zugriffstoken (`shpat_...`) kopieren.
2. `pip install -r requirements.txt`
3. `.env.example` nach `.env` kopieren, Werte eintragen und laden: `set -a; . ./.env; set +a`

**Starten**
```bash
python -m shopify_agent                       # interaktiver Chat
python -m shopify_agent "Welche Produkte sind noch Entwürfe?"
python -m shopify_agent --media-dir social "Lade das neueste Reel hoch und häng es an den Goldbarren"
```

## Autopilot – der Shop läuft allein

`python -m shopify_agent --autopilot` macht einen Durchlauf ohne dich:

| Darf der Bot allein | Gibt er immer an dich ab |
|---|---|
| Neue Reels/Bilder aus `social/` hochladen und ans passende Produkt hängen | Preise ändern |
| Fehlende Produktbeschreibungen und Tags schreiben (max. 10 pro Lauf, keine erfundenen Fakten) | Produkte veröffentlichen, archivieren, löschen |
| Bestellungen prüfen | Bestellungen ändern, Kundenprobleme, Unklares |

Jeder Lauf schreibt einen Bericht nach `autopilot/reports/<datum>.md`. Schon
hochgeladene Dateien merkt er sich in `autopilot/state.json`.

**Automatisch jeden Tag (GitHub Actions):** `.github/workflows/autopilot.yml`
läuft täglich um 06:17 UTC, sofort nach jedem neuen Upload in `social/` auf
`main`, und auf Knopfdruck (*Actions → Shopify Autopilot → Run workflow*).
Braucht der Shop dich, öffnet er ein GitHub-Issue „Shop braucht dich“ – GitHub
schickt dir dazu eine E-Mail. Schlägt ein Lauf fehl, gibt es ebenfalls ein Issue.

Einmalig einrichten: *Repo → Settings → Secrets and variables → Actions* und
drei Secrets anlegen: `ANTHROPIC_API_KEY`, `SHOPIFY_STORE`, `SHOPIFY_ACCESS_TOKEN`.

**Tests** (ohne Netzwerk, Shopify und Claude werden simuliert)
```bash
python -m pytest tests
```
