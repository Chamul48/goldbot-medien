# Agent P – High-End-Roadmap (Stand 01.11.2026)

Grundlage: Code-Stand `pc66` (nur gelesen), die 14 Dashboard-Fotos vom PC (desk_/handy_*), geprüfte Ideen aus den Bereichen Optik, Funktion und Strategie sowie eine eigene Sichtung von `team/`, `socialagent/` und `zentrale_llm.py`.
Es gelten die REGELN: nur Spielgeld, kein Rendite-Tuning, keine Änderung an Parametern, REGEL oder Freeze der laufenden Konten (swing, jarvis_gold, trend_korb), die 61 Pausen bleiben, Budgets nur nach deiner Wahl, Python 3.9, keine neuen pip-Pakete ohne Grund.

## Kurzfassung

1. Am Bot selbst muss für „High End“ wenig neu erfunden werden. Der größte Gewinn kommt aus **Ehrlichkeit und Klarheit in der Anzeige**: Die 61 Pausen hast du selbst gewählt, sie dürfen nicht als „61 Hinweise“ erscheinen. Die große Geldzahl soll zeigen, woraus sie besteht. Kleine Stichproben bekommen ein „n = 1“-Badge statt leuchtender 100 %.
2. **Zeitkritisch ist genau ein Punkt:** Heute ist der erste Vorwärts-Tag von trend_korb. Wenn der Erwartungs-Trichter jetzt eingefroren wird, kann man später ehrlich prüfen, ob das Konto im vorher festgelegten Rahmen liegt.
3. „Mehr Rendite“ entsteht hier nicht durch Nachdrehen, sondern durch **bessere Prüfung** (MinTRL, PBO, Baustein-Auswertung) und **neue, sauber registrierte Kandidaten nur im Labor** (Trend-Korb Breit, Carry). Ein neues Konto startet erst, wenn du es ausdrücklich wählst.
4. Jarvis und das Agenten-Team werden **messbar und günstiger**: Treffer- und Fehlalarm-Quote der Agenten, ein Zahlen-Prüfer für Jarvis-Antworten und die Batch-API für nächtliche Aufgaben. Alles bleibt innerhalb von 2,20 $/Tag.
5. Fast alles kostet **0 € extra im Monat** und lässt sich in 4 Wellen umsetzen. Welle 1 sind kleine, sichere Anzeige-Änderungen und eine Datensicherung für diese Woche.

---

## Sofort sichtbar (Top 5 Optik)

| # | Idee | Was du merkst | Aufwand | €/Monat |
|---|------|---------------|---------|---------|
| 1 | **Jarvis-Kugel verdeckt nichts mehr** | Auf dem Handy rutscht die Kugel beim Herunterscrollen weg, am PC bekommt der Inhalt rechts einen Rand. Zahlen in Einstellungen, Journal-KOSTEN und News-ZULETZT sind wieder lesbar. | klein | 0 |
| 2 | **Pausen = deine Wahl, kein Alarm** | „61 Konten pausiert, deine Wahl ▸“ steht als graue, einklappbare Zeile. Gelb und Rot kommen nur noch bei echten Problemen. Pausen durch eine Schutz-Regel und Pausen mit nicht überwachtem Stop bleiben Warnungen. | klein | 0 |
| 3 | **Ehrliche Hauptzahl „Dein Geld“** | Ein Balken teilt die Summe in IBKR-Papier, Bitget-Demo und Rechengeld auf. Getrennte oder veraltete Teile sind schraffiert und tragen „Stand …“. | mittel | 0 |
| 4 | **n-Badge für kleine Stichproben** | „Trefferquote 100 % (n = 1)“ erscheint grau mit gestricheltem Rand, „Bestes Konto“ heißt bei wenig Daten „vorläufig vorn“. Das Muster aus dem Journal gilt dann überall. | klein | 0 |
| 5 | **Kompakter Handy-Kopf** | Die Unter-Tabs liegen in einer wischbaren Zeile, der Spruch steht nur noch auf der Übersicht, und der Kopf schrumpft beim Scrollen. Statt 30–38 % nimmt er etwa 12 % des Bildschirms ein. | mittel | 0 |

Weitere Optik-Ideen kommen in späteren Wellen: Zentrale-Liste bündeln und filtern, Chart-Werkzeugleiste mit „Markt geschlossen“-Hinweis, „Alles schließen“ räumlich trennen, Vergleichschart mit laufenden Konten vorne.

## Am meisten Nutzen (Top 5 Funktion)

| # | Idee | Nutzen | Aufwand | €/Monat |
|---|------|--------|---------|---------|
| 1 | **Datensicherung mit einem Knopf + nachts automatisch** (zipfile, 14 Stände, Sperrliste für .env/Schlüssel/fernzugriff.json, mit Test) | Der Langzeittest und der Freeze-Nachweis von trend_korb bleiben lückenlos. Bisher gibt es keine laufende Sicherung. | klein | 0 |
| 2 | **Frische-Anzeige + Akku sparen** (keine Abfragen bei verstecktem Tab, „vor 2 s“, nach 10 s gelb, nach 60 s rot) | Du siehst ehrlich, ob die Zahlen aktuell sind, und das Handy spart Akku. Den Anker in dashboard_nav.py Z. 338 dabei mitpflegen. | klein | 0 |
| 3 | **Erklärungen an jeder Zahl** ((i)-Punkte aus jarvis.GLOSSAR, Checkliste „Erste Schritte“) | Begriffe wie R, Profitfaktor, Freeze oder DSR erklären sich dort, wo sie stehen. | klein | 0 |
| 4 | **Eigene Kursalarme mit fester Marke** („/alarm gold 3950“, Glocke am Ticker) | Zunächst nur für Märkte mit laufendem Konto. Fehlt ein frischer Kurs, steht dort ehrlich „kein frischer Kurs“. | klein | 0 |
| 5 | **Meldungs-Zentrale mit Ruhezeit** (Glocke mit Verlauf, nachts nur Notbremse, Stummschalten je Art) | Weniger Meldungs-Müdigkeit. Notbremse, „Agent hängt“ und Datenfehler kommen immer durch, das sichert ein Test ab. | mittel | 0 |

## Ehrlich mehr Rendite-Chance (Strategie-Kandidaten fürs Labor)

„Ehrlich“ heißt hier: Keine laufende Strategie wird verändert. Es gibt bessere Messung und neue, vorab registrierte Hypothesen. Jede neue Hypothese zählt als Versuch und macht die DSR strenger.

| # | Kandidat / Werkzeug | Warum es echte Chance statt Glück misst | Quelle | Aufwand | €/Monat |
|---|---------------------|----------------------------------------|--------|---------|---------|
| 1 | **Erwartungs-Trichter trend_korb – HEUTE einfrieren** (eigene erwartung.json mit SHA-256, Normalband SR 0,3/0,5 und gestricheltes Bootstrap-Band aus zeugnis.py) | Vergleicht die Kurve mit der Erwartung, die vor dem Start festgelegt war. Ein Minus nach 6 Monaten ist dann als „normal“ oder „Warnsignal“ einzuordnen. | Lempérière et al. 2014, arXiv 1404.3274; Hurst/Ooi/Pedersen 2017 | klein | 0 |
| 2 | **MinTRL „Wie lange noch bis zum Beleg?“** (min_trl() in robustheit.py, Fortschrittsbalken je Konto) | Zeigt, warum 4 Wochen Gewinn nichts beweisen. Bei SR 0,4 sind es etwa 17 Jahre. | Bailey & López de Prado 2012, J. of Risk | klein | 0 |
| 3 | **PBO mit CSCV im Labor** (dafür tägliche Lernteil-Renditen speichern, einmal nachts nachrechnen) | Misst direkt, wie wahrscheinlich der Labor-Sieger nur Zufall ist. | Bailey/Borwein/López de Prado/Zhu 2017, SSRN 2326253 | mittel | 0 |
| 4 | **Neue Hypothese „Trend-Korb Breit“** (15–20 Märkte, importiert die Funktionen von trend_korb, eigener Freeze, zuerst nur Lernteil-Bericht) | Trendfolge lebt von der Breite, 9 Märkte liegen am unteren Rand. Das Konto startet nur nach deiner Wahl. | Moskowitz/Ooi/Pedersen 2012; Hurst/Ooi/Pedersen 2017 | mittel | 0 |
| 5 | **Carry als zweite Vorhersage (Devisen), nur Labor** (FRED-Zinsen per pandas, Finanzierung im Backtest mitbuchen) | Carry liefert eine von Trend unabhängige Ertragsquelle. Das Crash-Risiko ist dokumentiert. | Koijen et al. 2018, JFE 127(2); Menkhoff et al. 2012 | groß | 0 |

Dazu kommt die **Baustein-Auswertung** (labor.baustein_effekte, nur auf dem Lernteil, mittel). Kosten-Realitätscheck, Harvey-Liu-Abschlag und SPA-Test folgen in Welle 3/4.

## KI & Agenten (Top 5)

Die folgenden Punkte stammen aus der eigenen Sichtung von `team/` (leiter, risiko, doktor, markt, news, social, ki), `zentrale_llm.py` (Prompt-Caching schon aktiv) und `jarvis*.py`. Alle bleiben innerhalb des Budgets von 2,20 $/Tag, und das Team bleibt Stufe 1 (nur beobachten).

| # | Idee | Was / Warum | Aufwand | €/Monat |
|---|------|-------------|---------|---------|
| 1 | **Agenten-Zeugnis vor jeder Stufe 2** | leiter.py zählt schon Episoden. Daraus wird je Agent eine Quote: Treffer, Fehlalarm, verpasst (z. B. 4 Wochen lang Befunde gegen spätere Ereignisse). Ohne diese Zahl gibt es keine Entscheidung über mehr Rechte. | klein | 0 |
| 2 | **Zahlen-Prüfer für Jarvis-Antworten** | Eine Regelprüfung ohne KI: Jede Zahl in einer Jarvis-Antwort muss in einem Werkzeug-Ergebnis derselben Runde vorkommen. Sonst bekommt die Zahl die Markierung „nicht belegt“. Das schützt vor erfundenen Kontoständen. | klein | 0 |
| 3 | **Batch-API für nächtliche KI-Aufgaben** | Teamleiter-Zusammenfassung, Social-Tagesanalyse und Wochenzeugnis haben keine Eile. Über die Message-Batches-API kosten sie etwa 50 % weniger. Das spart Budget, das Budget selbst bleibt gleich. | mittel | 0 (spart) |
| 4 | **Fester Prüfsatz für Jarvis (Mini-Eval)** | 20 Standardfragen mit erwarteten Fakten („Wie viele Konten laufen?“ → 3), wöchentlich ein Lauf, das Ergebnis kommt in die Zentrale. Nach Prompt- oder Modellwechseln sieht man so, ob Jarvis schlechter wurde. Kosten etwa 0,05 $ je Lauf aus dem bestehenden Budget. | klein | 0 |
| 5 | **News-Analyst gegen Prompt-Injection härten** | News-Texte gelten nur als Daten. Kein Werkzeug darf durch News ausgelöst werden, die Quelle steht an jedem Befund, und ein Test nutzt eine präparierte Schlagzeile („ignoriere Regeln…“). | klein | 0 |

## Social-Wachstum (Top 5)

Grundlage ist die eigene Sichtung von `socialagent/` (autopilot, qa, drehbuch mit Spielgeld-Hinweis, Hook-Varianten, reichweite_stand). Die KI-Clip-Budgets bleiben 0, media_publish wird nie wiederholt, der Modus wird nur über /api/social gesteuert.

| # | Idee | Was / Warum | Aufwand | €/Monat |
|---|------|-------------|---------|---------|
| 1 | **Lern-Schleife aus echten Zahlen** | Die Reichweite je Reel (Aufrufe, Wiedergabedauer, Speichern, Teilen) kommt über Metricool-Analytics in reichweite.json. Hook-Variante, Thema und Länge werden je Reel mitgeschrieben. Ein Gewinner wird erst ab ca. 10 Reels je Variante genannt, also gilt die Ehrlichkeitsregel auch hier. | mittel | 0 |
| 2 | **Feste Serie „Bot-Tagebuch: Woche X“** | Ehrliche Wochenzahlen von swing, jarvis_gold und trend_korb inklusive Verlusten, dazu der Trichter (siehe Strategie 1). Wiedererkennbare Formate binden Follower besser als Einzelthemen, und das Material ist schon vorhanden. | klein | 0 |
| 3 | **Karussell-Beiträge ohne KI-Clips** | Ein Standbild-Karussell (bild.py, 5–8 Folien: „Was ist ein Freeze?“, „Warum 100 % nichts heißt“). Es kostet 0 $ an Clips, und Karussells werden oft gespeichert, was für Lern-Inhalte gut passt. | mittel | 0 |
| 4 | **Testreels für Nicht-Follower** | Neue Hook-Varianten zuerst als Instagram-„Testreel“ (Trial Reel) nur an Nicht-Follower zeigen, die bessere später regulär posten. Ob Metricool diese Option anbietet, muss vorher geprüft werden. Sonst wird manuell freigegeben. | klein | 0 |
| 5 | **Rechtssicherer Finfluencer-Rahmen** | Der Hinweis „Spielgeld, keine Anlageberatung“ ist schon da. Dazu kommen ein fester Text-Check (keine Kauf-/Verkaufsaufforderung, keine Gewinnversprechen, Werbung klar gekennzeichnet) in qa.py, der den Beitrag als Schranke vor dem Posten aufhält, und ein Link auf die Hinweise von ESMA/BaFin für Finfluencer. | klein | 0 |

---

## Fahrplan in 4 Wellen

**Welle 1 – diese Woche (klein, 0 € extra, nur Anzeige oder neue Dateien):**
- Erwartungs-Trichter trend_korb einfrieren (zeitkritisch) – klein – 0 €
- MinTRL-Fortschrittsbalken im Labor – klein – 0 €
- Datensicherung ZIP (Knopf + nachts, Sperrliste + Test) – klein – 0 €
- Jarvis-Kugel verdeckt nichts mehr – klein – 0 €
- Pausen bündeln + Fokus-Ansicht „Nur meine 3 laufenden“ (mit Stop-Überwachungs-Etikett) – klein – 0 €
- n-Badge für kleine Stichproben – klein – 0 €
- Frische-Anzeige + Abfrage-Stopp bei verstecktem Tab – klein – 0 €
- Chart „im Ausschnitt“ in Grau (Einzeiler) + „Alles schließen“ räumlich trennen – klein – 0 €

**Welle 2 – nächste 2 Wochen (klein/mittel, 0 €):**
- Ehrliche Hauptzahl mit Aufschlüsselung und Alters-Stempel – mittel – 0 €
- Kompakter Handy-Kopf (wischbare Tabs, schrumpfender Kopf) – mittel – 0 €
- Zentrale-Liste bündeln, filtern, nach Tag gruppieren – mittel – 0 €
- Erklärungen (i) an jeder Zahl + Checkliste „Erste Schritte“ – klein – 0 €
- Eigene Kursalarme (nur Märkte mit laufendem Konto) – klein – 0 €
- Baustein-Auswertung (nur Lernteil) – klein – 0 €
- Agenten-Zeugnis (Treffer/Fehlalarm je Agent) – klein – 0 €
- Zahlen-Prüfer für Jarvis-Antworten – klein – 0 €
- News-Analyst gegen Prompt-Injection + Test – klein – 0 €
- Social: Serie „Bot-Tagebuch“ + Finfluencer-Text-Check – klein – 0 €

**Welle 3 – im Laufe des Monats (mittel, 0 €):**
- Tägliche Lernteil-Renditen speichern + PBO-Kachel – mittel – 0 €
- Kosten-Realitätscheck (Median/90 %/n der Spiegel-Fills, „Untergrenze“) – klein – 0 €
- Meldungs-Zentrale mit Ruhezeit – mittel – 0 €
- Vergleichschart: laufende Konten vorne, Abstand zu „Gold halten“ – mittel – 0 €
- Chart-Werkzeugleiste bündeln + „Markt geschlossen“-Wasserzeichen – mittel – 0 €
- Telegram-Schnellmenü mit Knöpfen (regelbasiert, ohne KI) – klein – 0 €
- Batch-API für nächtliche KI-Aufgaben – mittel – 0 € (spart)
- Mini-Eval für Jarvis (wöchentlich) – klein – 0 € (im Budget)
- Social: Lern-Schleife aus Metricool-Zahlen + Karussells + Testreels prüfen – mittel – 0 €
- PWA: eigenes Maskable-Icon (Pillow vorher prüfen) – klein – 0 €

**Welle 4 – später, teils nur nach deiner ausdrücklichen Wahl:**
- PWA: HTTPS über „tailscale serve“ + Service Worker mit Offline-Seite (die .bat führst du selbst aus) – mittel – 0 €
- Journal: eigene Notizen und Tags (Auswertung erst ab 30 Trades) – mittel – 0 €
- Was-wäre-wenn-Rechner bzw. erst eine Stop-Abstand-Spalte – mittel – 0 €
- Lernteil-Bericht „Trend-Korb Breit“ (Kontostart nur nach deiner Wahl) – mittel – 0 €
- SPA-Test und Harvey-Liu-Abschlag (nach PBO) – mittel/klein – 0 €
- Carry-Kandidat Devisen nur im Labor – groß – 0 €
- Regime-HMM nur als Anzeige – mittel – 0 €
- Positionsgrößen-Rechner (ATR/Vol-Regel), ICS-Termine, Kerzen-Trainer – klein bis groß – 0 €
- Kelly-Anzeige, Handy-Widget mit Token, Web-Push – nur bei klarem Bedarf und deiner Zustimmung – 0 €

---

## Was wir bewusst NICHT tun

| Nicht | Grund |
|-------|-------|
| Pausen aufheben oder Konten „aufwecken“ | Deine Wahl, REGELN. Die Pausen werden nur ehrlicher angezeigt. |
| Parameter, Schwellen, REGEL oder Freeze von swing, jarvis_gold und trend_korb anpassen | Das wäre Rendite-Tuning und würde den Vorwärts-Test von trend_korb wertlos machen. |
| Den Prüfteil oder Übungs-/Journal-Ergebnisse zur Auswahl neuer Bausteine nutzen | Das ist ein verdeckter Blick in die Zukunft (Labor-Ehrlichkeitsregel). |
| KI-Clip-Budget erhöhen oder das Jarvis-Budget über 2,20 $/Tag heben | Budgets ändern sich nur nach deiner Wahl. Social läuft weiter ohne KI-Clips. |
| Agenten-Team Stufe 2 (Agenten mit Händen) | Erst wenn das Agenten-Zeugnis über Wochen eine niedrige Fehlalarm-Quote zeigt, und dann nur nach deiner Wahl. |
| Web-Push mit pywebpush oder ntfy.sh | Neues pip-Paket oder fremder Server, kleiner Nutzen, weil Telegram schon pusht. |
| Widget- oder Kalender-Token ohne deine Zustimmung | Das wäre ein zweiter Zugangsweg neben Passwort und Cookie, also eine Sicherheitsänderung. |
| CPCV für ml_strategie | Das Konto ist pausiert, eine Diagnose bringt jetzt keinen Nutzen. |
| FX-Value/PPP-Kandidat | Bei 3–5 Jahren Halbwertszeit und ca. 20 Jahren Daten gibt es zu wenige unabhängige Beobachtungen, das Ergebnis wäre nicht prüfbar. |
| Jarvis als 8. Knopf in der unteren Leiste | Bei 360 px Breite wird die Leiste zu eng (ca. 45 px je Knopf). |
| Echte Orders, Live-Konten bei IBKR oder Bitget | REGELN: nur Papierkonto und Demo. |
| media_publish wiederholen oder Social am API-Weg vorbei schalten | REGELN, sonst drohen doppelte Posts. |

---

## Quellen

**Statistik und Strategie**
- Bailey, Borwein, López de Prado, Zhu (2017): The Probability of Backtest Overfitting – https://papers.ssrn.com/abstract=2326253 ; R-Paket pbo – https://ftp.fau.de/cran/web/packages/pbo/readme/README.html
- Bailey, López de Prado (2012): The Sharpe Ratio Efficient Frontier (PSR, MinTRL) – https://www.risk.net/journal-risk/2223785/sharpe-ratio-efficient-frontier ; https://rdrr.io/cran/PerformanceAnalytics/man/MinTrackRecord.html
- Harvey, Liu (2015): Backtesting – https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF ; https://www.man.com/insights/backtesting
- Hansen (2005): Test for Superior Predictive Ability, JBES 23(4) – https://scilit.com/publications/3acb201045eb64ffec5aeeb2043454cc ; White (2000), Econometrica 68 ; Sheppard-Handout – https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/AFE_Week_4_handout.pdf
- Lempérière et al. (2014): Two centuries of trend following – https://ar5iv.arxiv.org/html/1404.3274
- Moskowitz, Ooi, Pedersen (2012): Time Series Momentum, JFE 104(2) ; Hurst, Ooi, Pedersen (2017): A Century of Evidence on Trend-Following
- Koijen, Moskowitz, Pedersen, Vrugt (2018): Carry – https://econpapers.repec.org/RePEc:eee:jfinec:v:127:y:2018:i:2:p:197-225 ; Menkhoff et al. (2012) – https://openaccess.city.ac.uk/id/eprint/3391/ ; QuantConnect Carry+Trend – https://www.quantconnect.com/research/16001/combined-carry-and-trend/
- Carver (2015): Systematic Trading ; Carver (2023): Advanced Futures Trading Strategies – https://www.harriman-house.com/advancedfuturestradingstrat ; Perold (1988): Implementation Shortfall, JPM 14(3)
- Moreira, Muir (2017) – https://www.nber.org/papers/22208 ; Cederburg et al. (2020) – https://econpapers.repec.org/RePEc:eee:jfinec:v:138:y:2020:i:1:p:95-117
- Nystrup, Madsen, Lindström (2018) – https://econpapers.repec.org/RePEc:taf:quantf:v:18:y:2018:i:1:p:83-95 ; https://www2.imm.dtu.dk/pubdb/pubs/6808-full.html
- MacLean, Thorp, Ziemba (2010): Kelly – https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf

**Optik, UX und App**
- Page Visibility API – https://web.dev/pagevisibility-intro ; Service Worker – https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- Tailscale Serve und HTTPS – https://tailscale.com/kb/1312/serve ; https://tailscale.com/kb/1153/enabling-https (in einer Teilsitzung nicht erreichbar, vor der Umsetzung erneut prüfen)
- iOS-Web-Push – https://documentation.onesignal.com/docs/web-push-for-ios ; https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide
- Material Dark Theme – https://m2.material.io/design/color/dark-theme ; Finanz-Dashboard-UX – https://olivertriunfodotcom.pages.dev/ux-financial-dashboards ; https://www.designrush.com/agency/ui-ux-design/trends/dashboard-design-principles
- NN/g Mobile Tutorials – https://www.nngroup.com/articles/mobile-tutorials/

**Funktion**
- TradingView Preisalarme – https://www.tradingview.com/support/solutions/43000520149 ; Bar Replay – https://www.tradingview.com/support/solutions/43000712747-bar-replay-how-and-why-to-test-a-strategy-in-the-past/
- Tradezella Tags – https://help.tradezella.com/en/articles/5858193-applying-tags-to-trades
- IBKR Risk Navigator / Szenarien – https://www.interactivebrokers.com/campus/trading-lessons/using-custom-scenarios-on-a-portfolio/
- Telegram Bot-Knöpfe – https://core.telegram.org/api/bots/buttons ; iCalendar RFC 5545 – https://datatracker.ietf.org/doc/html/rfc5545 ; Scriptable-Widget – https://github.com/SmonSE/IOS-Widget_load_JSON

**KI und Social** (nicht im Einzelnen nachgeprüft, vor der Umsetzung kontrollieren)
- Anthropic: Prompt Caching und Message Batches API (ca. 50 % Rabatt) – https://docs.anthropic.com/en/docs/build-with-claude/batch-processing
- Instagram Testreels (Trial Reels) – https://creators.instagram.com
- ESMA/BaFin-Hinweise zu Finfluencern – https://www.esma.europa.eu ; https://www.bafin.de
- Metricool-Analytics und beste Posting-Zeit (Metricool-Schnittstelle, im Bot schon angebunden)

**Eigene Prüfung (nur gelesen)**
- Code: `pc66/` – dashboard.py (Z. 726, 757–777, 807, 1163, 1176, 2104, 2405, 2413, 2473, 3226, 3277), dashboard_nav.py (219, 338), dashboard_jarvis.py, dashboard_betrieb.py (124), agent.py (498, 703), backtest.py (56), kurse.py, journal.py (581), fernzugriff.py, telegram_jarvis.py (108), zentrale_llm.py (768–777 Caching), team/leiter.py, team/ki.py, socialagent/autopilot.py (598), socialagent/drehbuch.py (30, 410), socialagent/qa.py
- Fotos: `C:\Users\User\Desktop\golden_bot\live\v63_neu\fotos\desk_*.png` und `handy_*.png` (alle 14)
