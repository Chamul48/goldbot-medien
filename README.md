# goldbot-medien
Gold-Agent Videos und Reels – plus **Goldbot**, ein Assistent für dein Fiverr-Profil und den Vertrieb.

## Was Goldbot macht

| Befehl | Ergebnis |
|---|---|
| `python -m goldbot profil` | Fertige Profiltexte zum Einfügen: Einzeiler, „Über mich“ (150–600 Zeichen), Fähigkeiten, 3 Gigs mit Titel, Tags, Beschreibung, Basic/Standard/Premium-Paketen und FAQ. Die Fiverr-Grenzen werden automatisch geprüft und eingehalten. |
| `python -m goldbot trends` | Scannt Google Trends (AT/DE), Reddit (z. B. r/forhire mit **[Hiring]**-Aufträgen), Hacker News und eigene RSS-Feeds, und bewertet alles nach Relevanz für deine Nische. |
| `python -m goldbot ideen` | Trends + 8 konkrete Vertriebsideen für die nächsten 7 Tage (mit Schritten, Kanal, Aufwand, Umsatzpotenzial). |
| `python -m goldbot alles` | Alles zusammen (Standard). |
| `python -m goldbot dauer --alle 24` | Läuft dauerhaft und erstellt alle 24 Stunden einen neuen Bericht. |

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
