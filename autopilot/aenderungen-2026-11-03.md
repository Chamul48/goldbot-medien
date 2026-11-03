# Änderungen am Shop chuchcapone – 3. November 2026

Vorher gesichert: `autopilot/backup-2026-11-03.json` (17 Produkte, 3 Kollektionen, 1 Seite).
Bestehende Produkte, Kollektionen und Seiten wurden **nicht** verändert. Nur neu angelegt, alles unsichtbar für Kunden:

| Was | Titel | Handle | ID | Sichtbar |
|---|---|---|---|---|
| Smart-Kollektion (Tag `goldbarren`) | Goldbarren | goldbarren | gid://shopify/Collection/734414242132 | nein (unveröffentlicht) |
| Smart-Kollektion (Tag `goldmuenzen`) | Goldmünzen | goldmuenzen | gid://shopify/Collection/734414274900 | nein (unveröffentlicht) |
| Smart-Kollektion (Tag `geschenk`) | Gold als Geschenk | gold-als-geschenk | gid://shopify/Collection/734414307668 | nein (unveröffentlicht) |
| Seite (Entwurf) | Häufige Fragen | faq | gid://shopify/Page/716932153684 | nein (isPublished=false) |
| Seite (Entwurf) | Über uns | ueber-uns | gid://shopify/Page/716932186452 | nein (isPublished=false) |

Alle Texte: Deutsch, ohne erfundene Fakten, ohne Rendite-, Steuer- oder Rechtsversprechen.
Fehlende Angaben stehen als `[BITTE ERGAENZEN: …]` im Text – vor dem Veröffentlichen ersetzen.
Jeder Text wurde von zwei unabhängigen Prüfern (Fakten/Recht, Sprache/SEO) gegengelesen und überarbeitet.

Produkte erscheinen automatisch in den Kollektionen, sobald sie den passenden Tag tragen.

**Rückgängig machen:** Die fünf Einträge oben im Shopify-Admin löschen (Kollektionen bzw. Onlineshop → Seiten).
Löschen mache ich nicht selbst.

Neu im Repo: `docs/produkttexte-gold.md` – Schreibleitfaden für alle künftigen Gold-Produkttexte.


## Nachtrag: 12 Gold-Produkte als Entwurf (Sortiment nach Trend)

Ausgangsstand vorher gelesen: weiterhin genau die 17 Beispielprodukte aus `autopilot/backup-2026-11-03.json`, nichts verändert.
Neu angelegt mit `productCreate`, **Status DRAFT** (für Kunden unsichtbar). **Kein Preis gesetzt** (Shopify legt die Variante mit 0 € an, der Preis kommt von dir), keine Bilder, kein Bestand.
Fakten: nur Werte, bei denen zwei unabhängige Prüfer übereinstimmten. Alles Unsichere steht als `[BITTE ERGAENZEN: …]` im Text.
Die Tags ordnen die Produkte automatisch den Kollektionen zu.

| # | Titel | Kollektion (Tag) | ID |
|---|---|---|---|
| 1 | Goldbarren 1 g – Münze Österreich | goldbarren, geschenk | gid://shopify/Product/15939489530196 |
| 2 | Wiener Philharmoniker 1 oz Gold – Münze Österreich | goldmuenzen | gid://shopify/Product/15939489595732 |
| 3 | Krugerrand 1 oz Gold – South African Mint | goldmuenzen | gid://shopify/Product/15939489628500 |
| 4 | Goldbarren 50 x 1 g CombiBar – Valcambi | goldbarren, geschenk | gid://shopify/Product/15939489694036 |
| 5 | Goldbarren 10 g – Münze Österreich | goldbarren | gid://shopify/Product/15939489726804 |
| 6 | Wiener Philharmoniker 1/25 oz Gold in Geschenkverpackung – Münze Österreich | goldmuenzen, geschenk | gid://shopify/Product/15939489792340 |
| 7 | Maple Leaf 1 oz Gold – Royal Canadian Mint | goldmuenzen | gid://shopify/Product/15939489825108 |
| 8 | Wiener Philharmoniker 1/10 oz Gold – Münze Österreich | goldmuenzen, geschenk | gid://shopify/Product/15939489890644 |
| 9 | Goldbarren 1 oz (31,10 g) – Heraeus | goldbarren | gid://shopify/Product/15939489956180 |
| 10 | Goldbarren 1 g auf Geschenkkarte – Valcambi | goldbarren, geschenk | gid://shopify/Product/15939490021716 |
| 11 | Krugerrand 1/10 oz Gold – South African Mint | goldmuenzen | gid://shopify/Product/15939490054484 |
| 12 | Känguru 1 oz Gold – The Perth Mint | goldmuenzen | gid://shopify/Product/15939490120020 |

Begründung, Quellen und offene Punkte je Produkt: `autopilot/sortiment-2026-11-03.md`.
**Rückgängig:** die 12 Entwürfe im Admin unter Produkte → Status „Entwurf“ löschen (Löschen mache ich nicht selbst).
