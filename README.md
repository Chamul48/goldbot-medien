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
