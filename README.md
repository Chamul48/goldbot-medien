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
   `read_products, write_products, read_orders, read_files, write_files` vergeben, installieren und
   den Admin-API-Zugriffstoken (`shpat_...`) kopieren.
2. `pip install -r requirements.txt`
3. `.env.example` nach `.env` kopieren, Werte eintragen und laden: `set -a; . ./.env; set +a`

**Starten**
```bash
python -m shopify_agent                       # interaktiver Chat
python -m shopify_agent "Welche Produkte sind noch Entwürfe?"
python -m shopify_agent --media-dir social "Lade das neueste Reel hoch und häng es an den Goldbarren"
```

**Tests** (ohne Netzwerk, Shopify und Claude werden simuliert)
```bash
python -m pytest tests
```
