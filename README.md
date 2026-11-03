# goldbot-medien
Gold-Agent Videos und Reels – plus **Goldbot**, ein Assistent für dein Fiverr-Profil und den Vertrieb.

## Was Goldbot macht

| Befehl | Ergebnis |
|---|---|
| `python -m goldbot auftraege` | Sucht **neue** passende Aufträge (u. a. r/forhire, r/HireAnEditor), schreibt zu jedem einen Antwort-Entwurf und meldet sie per Windows-Hinweis. Bereits gemeldete Aufträge kommen nicht noch einmal. |
| `python -m goldbot profil` | Fertige Profiltexte: Einzeiler, „Über mich“, Fähigkeiten, 3 Gigs mit Paketen und FAQ – Fiverr-Grenzen werden eingehalten. |
| `python -m goldbot einfuegen` | Öffnet die **Einfüge-Hilfe**: eine Seite mit „Kopieren“-Knopf für jedes Fiverr-Feld. |
| `python -m goldbot muster` | Erstellt 6 **Muster-Videos** (9:16, Gold/Finanzen/Krypto, Deutsch + Englisch) mit echtem Stock-Material (Pixabay), Sprecherstimme, Wort-für-Wort-Untertiteln, Zoom-Schnitten und Musik. Braucht ffmpeg und einen kostenlosen Pixabay-Schlüssel (`PIXABAY_API_KEY`). |
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
pip install -r requirements.txt pytest
python -m pytest -q
```
