# Fiverr-Vorschlag – 4. November 2026 (erster Lauf)

**Du entscheidest und fügst selbst ein. Claude bedient Fiverr nie.**
Grundlage: dein öffentliches Profil (gelesen 04.11.2026), Websuche zu Fiverr-Preisen 2026 und die
Konkurrenz-Angebote, die dein Goldbot auf Reddit sammelt.

## 1. Sofort: Profilbild und Beschreibung
- **Profilbild:** Zuletzt war die Testvorschau mit einem fremden Fußballer hochgeladen. Ersetzen durch
  `Downloads\fiverr_uebergangsbild.png`, später durch dein echtes Foto (Werkzeug: Desktop-Ordner „Profilbild“).
- **Beschreibung:** Deine jetzige bricht nach 600 Zeichen mitten im Wort ab („…best solut“). Ersetzen durch
  diese Fassung (482 Zeichen, ohne erfundene Erfahrung, geprüft mit `CLAIM_RE`):

```
Hi, I'm Chucha from Austria. I build practical AI solutions that save you time.

What I offer:
- AI automation: custom AI agents and workflows for repetitive tasks
- Trading bots: Python bots for gold, silver and crypto, incl. backtesting
- Social media reels: short videos for Instagram and TikTok
- AI content: captions, scripts and short texts

I speak German and English, deliver on time and keep you updated. Message me before ordering so we can find the best solution for you.
```

## 2. Preise im Vergleich
| Gig (aus `docs/profil-paket.json`) | Deine Pakete (USD) | Markt 2026 | Einschätzung |
|---|---|---|---|
| Short-Form-Reels/Shorts schneiden | 25 / 60 / 150 | Basic 15–50, Standard 50–120, Premium 150–300 (Flocksy, Increditors, BIOOQ); viele Gigs „ab 25–36“; Reddit-Anbieter: „$50 per video flat rate“ | **Passt.** Für den Start ohne Bewertungen beibehalten. |
| Faceless Gold-/Finanz-Shorts | 35 / 90 / 220 | Basic 25–40, Standard 80–150, Premium 400–700 für Kanal-Setup mit 10 Videos (aicap.in); 45 von 48 Gigs der ersten Seite starten bei 5–45 (Mark Studios) | **Basic/Standard passen.** Premium nur so lassen, wenn es *keinen* Kanal-Aufbau enthält. Sonst 400+. |
| KI-Video-Automation einrichten | 40 / 120 / 280 | n8n-/Make-Gigs starten meist bei 50–100; ein Workflow 100–500, mehrere 500–1.500 (Memvers, Cybernaira, Fiverr-Listen) | **Zu günstig.** Vorschlag: **60 / 180 / 450**. Unter 50 wirkt es unseriös, und der Aufwand ist hoch. |

Hinweis: Fiverr behält von dir 20 % ein. Käufer zahlen zusätzlich 5,5 % plus 3,50 $ unter 200 $ (laut Mark Studios).

## 3. Kleine Verbesserungen
- **Profil und Gigs passen nicht zusammen.** Dein Profil nennt „Trading Bots“, die Gigs sind Video und
  Automation. Entweder einen Gig „Python trading bot with backtesting“ anlegen oder „Trading Bots“ aus dem Titel
  nehmen. Bei Trading-Bots **keine Gewinnversprechen**.
- Paketbeschreibungen kurz halten (max. 100 Zeichen) und Lieferzeit und Revisionen klar nennen. So machen es die
  gut bewerteten Gigs.

## Quellen
- [Flocksy: Short-Form Video Editing 2026](https://flocksy.com/resources/short-form-video-editing-subscription/)
- [Increditors: Fiverr Video Editors Review](https://increditors.com/fiverr-video-editors-review/)
- [BIOOQ: Fiverr Skills 2026](https://biooq.com/fiverr-skills-that-will-actually-work/)
- [aicap.in: AI Fiverr Gigs 2026](https://aicap.in/high-paying-ai-fiverr-gigs-2026/)
- [Mark Studios: Faceless YouTube Video Cost 2026](https://www.markstudios.com/blog/faceless-youtube-video-cost-2026)
- [Memvers: AI Services on Fiverr 2026](https://memvers.com/blog/ai-services-fiverr-2026)
- [Cybernaira: Fiverr AI Agent Developers 2026](https://cybernaira.com/fiverr-ai-agent-automation-developers/)
- [Fiverr: n8n automation](https://www.fiverr.com/gigs/n8n-automation)
- Goldbot-Bericht `reports\2026-11-04_0146\daten.json` (30 Konkurrenz-Einträge, z. B. „Video Editing $50 per video“)
