# Journal – tägliche Verbesserung (neueste oben)

## 2026-11-04 (erster Lauf, manuell gestartet)
- **Vorgeschlagen:**
  - Preisspannen für 7 Gold-Produkte (`autopilot/preise-2026-11-04.md`).
  - Fiverr: neue Beschreibung (482 Zeichen), Profilbild ersetzen, Automation-Gig 60/180/450 statt 40/120/280
    (`docs/fiverr-vorschlag-2026-11-04.md`).
- **Im Shop geändert:** Philharmoniker 1 oz – Dicke 2,0 mm eingetragen. Belegt durch gold.de-Tabelle, Kettner,
  pro aurum, Wikipedia und Goldankauf Pro24. Details in `autopilot/aenderungen-2026-11-04.md`.
- **Bewusst nicht geändert:** Dicke von Philharmoniker 1/10 oz und 1/25 oz. Die Quellen widersprechen sich
  (1/10: 1,1/1,2/1,6 mm, 1/25: 0,8/1,0/1,2 mm).
- **Übernommen vom Inhaber:** – (erster Lauf, noch nichts zu vergleichen)
- **Was nicht ging:**
  - Lange PC-Abrufe: `start_process` meldet „läuft“, `read_process_output` wartet aber nicht. Der Abruf lief weiter
    und war erst später fertig. → Höchstens 3 URLs pro Aufruf und mit `> datei` umleiten, damit der Aufruf erst
    endet, wenn alles fertig ist.
  - Falsche gold.de-Adressen (404): richtig sind `kruegerrand`, `kaenguru` und `goldbarren/1-oz`.
  - `seite_lesen.py` behielt nur 40 Beträge, und die gold.de-Kopfzeile verbrauchte viele davon. Dadurch war die
    Känguru-Liste abgeschnitten. → Grenze auf 120 erhöht.
  - Kein Abruf für Bruchstücke (1/10, 1/25 oz) und für einzelne Hersteller.
- **Nächstes Mal:**
  - Bruchstücke und Geschenkprodukte erheben (gold.de-Seiten je Größe finden).
  - Hersteller-Seiten für Heraeus und Münze Österreich lesen.
  - Prüfen, ob der Inhaber Beschreibung und Profilbild auf Fiverr ersetzt hat.
