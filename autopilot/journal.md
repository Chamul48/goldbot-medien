# Journal – tägliche Verbesserung (neueste oben)

## 2026-11-07 (Läufe vom 4., 5. und 6.11. kamen erst heute an – Sitzung war nicht aktiv)
- **Erledigt aus „Nächstes Mal“:**
  - Preise für Philharmoniker 1/10 oz und 1/25 oz (Geschenk), Krügerrand 1/10 oz, Valcambi 1 g Taufe und
    Heraeus 1 oz erhoben (`autopilot/preise-2026-11-07.md`).
  - Die Münze Österreich bietet die 1/25-oz-Geschenkverpackung selbst zum Preis der Einzelmünze an (186,92 €).
- **Vorgeschlagen:** Preisspannen zum neuen Kurs. Gold ist seit dem 04.11. um 4,2 % auf 3.649,55 €/oz gestiegen.
- **Im Shop geändert:** nichts. Für die offenen Maße widersprechen sich die Quellen weiterhin: Heraeus-Dicke 1,6 oder
  1,8 mm, Krügerrand 1/10 oz mit nur einer Quelle (16,55 × 1,35 mm). Deshalb war auch keine neue Sicherung nötig.
- **Übernommen vom Inhaber:** Im Shop bisher nichts (keine Preise, keine Fotos, Testdaten noch da). Ob Fiverr-Bild
  und -Beschreibung ersetzt wurden, ließ sich nicht prüfen (PC offline).
- **Was nicht ging:**
  - PC offline, daher keine Live-Händlerseiten und kein Fiverr-Profil. Alles stammt aus Suchauszügen ohne Datum →
    nur die Aufgeld-Spannen sind aussagekräftig.
  - Desktop Commander wartet bei Fernaufrufen höchstens 3 s und lässt längere Prozesse im Hintergrund weiterlaufen.
    Deshalb in die Checkliste: im Hintergrund in eine Datei schreiben und die Datei später lesen.
  - 4 aufgestaute Läufe → nur EIN Lauf für heute, kein Nachholen alter Tage, weil die Kurse von damals ohnehin vorbei
    sind.
- **Nächstes Mal:**
  - Ist der PC an: Live-Preise für die Bruchstücke von gold.de holen (Seiten je Größe suchen) und das Fiverr-Profil
    prüfen.
  - Gibt es weiter keine Reaktion im Shop, den Bericht kürzer fassen und die 3 wichtigsten To-dos für den Inhaber
    nach oben stellen.

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
