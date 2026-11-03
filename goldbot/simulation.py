"""Simulation: Wie könnte der erste Monat als Verkäufer laufen?

Monte-Carlo-Modell (Standard 2000 Durchläufe × 30 Tage) für zwei Kanäle:

* **Fiverr** – je Gig: Impressionen → Klicks → Bestellungen/Anfragen, mit „Neuer-Gig-Schub“
  in den ersten zwei Wochen und besserer Umwandlung durch Bewertungen.
* **Reddit-Aufträge** – Auftragsrate wird aus dem echten Gedächtnis des Auftrags-Wächters
  (`.gesehen.json`) gelernt; du antwortest auf X passende Aufträge am Tag.

Dazu: begrenzte Arbeitszeit pro Tag (Warteschlange, Lieferfristen, verspätete Lieferung →
Stornierung), Fiverr-Gebühr 20 % und 14 Tage bis zur Auszahlung.

**Lernen:** Alle Quoten sind Beta-Verteilungen (Annahmen, keine Fiverr-Zahlen). Trägst du unter
`simulation.ist` deine echten Zahlen aus der Fiverr-Statistik ein, werden die Annahmen mit
diesen Beobachtungen verrechnet – je mehr echte Daten, desto weniger zählen die Annahmen.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ROOT, output_dir

# --------------------------------------------------------------------------- #
# Annahmen (Vorwissen) – bewusst vorsichtig, alles über config überschreibbar
# --------------------------------------------------------------------------- #

DEFAULTS: dict[str, Any] = {
    "tage": 30,
    "laeufe": 2000,
    "seed": 7,
    "stunden_pro_tag": 3.0,          # deine Arbeitszeit für Aufträge
    "fiverr_gebuehr": 0.20,
    "auszahlung_nach_tagen": 14,      # Fiverr gibt Geld neuer Verkäufer nach 14 Tagen frei
    "zahlung_gebuehr_reddit": 0.04,  # PayPal & Co.
    # Fiverr-Trichter je Gig (Mittelwerte; Unsicherheit über Beta/Log-Normal)
    "impressionen_pro_tag": 25.0,     # nach dem Start-Schub
    "start_schub": 2.0,               # Faktor in den ersten 14 Tagen
    "start_schub_tage": 14,
    "impressionen_streuung": 0.7,     # Log-Normal-Sigma: wie stark sich Monate unterscheiden
    "klickrate": [3, 197],            # Beta(a, b) → Mittel 1,5 %
    "bestellrate": [2, 198],          # je Klick, ohne Bewertungen → Mittel 1 %
    "anfragerate": [6, 194],          # Nachrichten je Klick → Mittel 3 %
    "anfrage_zu_auftrag": [2, 8],     # → Mittel 20 %
    "bewertungs_bonus": 0.15,         # +15 % Impressionen und Umwandlung je Bewertung (max. 5)
    "paket_mix": [0.6, 0.3, 0.1],     # Basic / Standard / Premium
    "stunden_je_paket": [1.5, 4.0, 10.0],
    "gig_aufwand": [1.0, 1.3, 1.6],   # Gig 2 (Faceless) und 3 (Automatisierung) brauchen mehr Zeit
    "bewertung_quote": 0.75,          # so viele Kunden bewerten
    # Reddit
    "reddit_auftraege_pro_tag": None,  # None = aus .gesehen.json lernen
    "reddit_passend": 0.35,           # Anteil, der zu deinen Gigs passt (Shorts/Reels/Faceless)
    "antworten_pro_tag": 5,
    "antwort_rueckmeldung": [2, 28],  # Kunde meldet sich → Mittel 7 % (viel Konkurrenz)
    "rueckmeldung_zu_auftrag": [3, 7],  # → Mittel 30 %
    "reddit_preis_median": 40.0,      # $; meist bezahlter Testschnitt, selten mehr
    "reddit_stunden": 2.0,
    "reddit_lieferfrist": 3,
    "storno_bei_verspaetung": 0.5,
}

PAKETE = ["Basic", "Standard", "Premium"]


# --------------------------------------------------------------------------- #
# Zufall
# --------------------------------------------------------------------------- #

def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 50:  # Normal-Näherung
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def binomial(rng: random.Random, n: int, p: float) -> int:
    if n <= 0 or p <= 0:
        return 0
    if n > 200:
        return poisson(rng, n * p) if p < 0.05 else max(0, min(n, round(rng.gauss(n * p, math.sqrt(n * p * (1 - p))))))
    return sum(1 for _ in range(n) if rng.random() < p)


def beta_mean(ab: list[float]) -> float:
    a, b = ab
    return a / (a + b)


# --------------------------------------------------------------------------- #
# Lernen aus echten Daten
# --------------------------------------------------------------------------- #

def learn_reddit_rate(state: dict[str, str]) -> tuple[float | None, int, float]:
    """Neue Aufträge pro Tag aus dem Gedächtnis des Auftrags-Wächters.

    Der erste Abruf enthält den Rückstand (alles, was schon online war) und zählt nicht mit.
    Liefert (Rate, Anzahl, beobachtete Stunden); Rate None bei zu wenig Daten (< 6 h).
    """
    times = sorted(datetime.fromisoformat(ts) for ts in state.values() if ts)
    if len(times) < 3:
        return None, len(times), 0.0
    first = times[0]
    later = [t for t in times if (t - first).total_seconds() > 60]
    hours = (times[-1] - first).total_seconds() / 3600
    if hours < 6 or not later:
        return None, len(later), hours
    return len(later) / hours * 24, len(later), hours


def apply_observed(params: dict[str, Any], ist: dict[str, Any]) -> list[str]:
    """Echte Zahlen (Fiverr-Statistik, eigene Reddit-Bilanz) mit den Annahmen verrechnen."""
    notes: list[str] = []
    if not ist:
        return notes
    gigs = max(1, int(ist.get("gigs", 3)))
    days = float(ist.get("tage") or 0)

    def update(key: str, hits: Any, trials: Any, label: str) -> None:
        if hits is None or trials is None or int(trials) <= 0:
            return
        hits, trials = int(hits), int(trials)
        hits = min(hits, trials)
        a, b = params[key]
        params[key] = [a + hits, b + trials - hits]
        notes.append(f"{label}: {hits} von {trials} → jetzt {beta_mean(params[key]):.1%} (vorher {a / (a + b):.1%})")

    imp, klicks = ist.get("impressionen"), ist.get("klicks")
    if imp and days > 0:
        observed = float(imp) / days / gigs
        weight = min(1.0, days / 14)  # zwei Wochen echte Daten zählen voll
        old = params["impressionen_pro_tag"]
        params["impressionen_pro_tag"] = (1 - weight) * old + weight * observed / (params["start_schub"] if days <= params["start_schub_tage"] else 1)
        notes.append(f"Impressionen je Gig und Tag: {observed:.0f} beobachtet → Grundwert {params['impressionen_pro_tag']:.0f} (vorher {old:.0f})")
    update("klickrate", klicks, imp, "Klickrate")
    update("bestellrate", ist.get("bestellungen"), klicks, "Bestellungen je Klick")
    update("anfragerate", ist.get("anfragen"), klicks, "Anfragen je Klick")
    update("antwort_rueckmeldung", ist.get("reddit_rueckmeldungen"), ist.get("reddit_antworten"), "Reddit-Rückmeldungen")
    update("rueckmeldung_zu_auftrag", ist.get("reddit_auftraege"), ist.get("reddit_rueckmeldungen"), "Reddit-Aufträge je Rückmeldung")
    return notes


# --------------------------------------------------------------------------- #
# Ein Monat
# --------------------------------------------------------------------------- #

@dataclass
class Order:
    day: int
    hours: float
    due: int
    gross: float
    net: float
    channel: str
    left: float = 0.0
    done_day: int | None = None
    cancelled: bool = False

    def __post_init__(self) -> None:
        self.left = self.hours


@dataclass
class Month:
    orders: list[Order] = field(default_factory=list)
    inquiries: int = 0
    impressions: int = 0
    clicks: int = 0
    replies: int = 0
    callbacks: int = 0
    reviews: int = 0
    hours: float = 0.0
    first_order_day: int | None = None

    def done(self) -> list[Order]:
        return [o for o in self.orders if o.done_day is not None and not o.cancelled]


def simulate_month(p: dict[str, Any], gigs: list[dict[str, Any]], rng: random.Random) -> Month:
    m = Month()
    days = int(p["tage"])
    # Monats-Unsicherheit: jeder Durchlauf zieht seine eigenen „wahren“ Quoten
    ctr = rng.betavariate(*p["klickrate"])
    conv = rng.betavariate(*p["bestellrate"])
    inq = rng.betavariate(*p["anfragerate"])
    inq_conv = rng.betavariate(*p["anfrage_zu_auftrag"])
    callback = rng.betavariate(*p["antwort_rueckmeldung"])
    callback_conv = rng.betavariate(*p["rueckmeldung_zu_auftrag"])
    sigma = float(p["impressionen_streuung"])
    reach = [math.exp(rng.gauss(-sigma * sigma / 2, sigma)) for _ in gigs]  # Mittel 1
    lam_reddit = float(p["reddit_auftraege_pro_tag"] or 0) * float(p["reddit_passend"])
    queue: list[Order] = []

    for day in range(days):
        bonus = 1 + p["bewertungs_bonus"] * min(m.reviews, 5)
        boost = p["start_schub"] if day < p["start_schub_tage"] else 1.0
        for g, gig in enumerate(gigs):
            imp = poisson(rng, p["impressionen_pro_tag"] * boost * reach[g] * bonus)
            clicks = binomial(rng, imp, ctr)
            m.impressions += imp
            m.clicks += clicks
            n_orders = binomial(rng, clicks, min(0.5, conv * bonus))
            n_inq = binomial(rng, clicks, inq)
            m.inquiries += n_inq
            n_orders += binomial(rng, n_inq, inq_conv)
            for _ in range(n_orders):
                k = rng.choices(range(3), weights=p["paket_mix"])[0]
                pkg = gig["packages"][k]
                gross = float(pkg["price_usd"])
                hours = p["stunden_je_paket"][k] * p["gig_aufwand"][g % len(p["gig_aufwand"])]
                queue.append(Order(day, hours, day + int(pkg["delivery_days"]), gross,
                                   gross * (1 - p["fiverr_gebuehr"]), f"Gig {g + 1} {PAKETE[k]}"))
        # Reddit: passende Aufträge des Tages, du antwortest auf höchstens X
        fitting = poisson(rng, lam_reddit)
        sent = min(fitting, int(p["antworten_pro_tag"]))
        m.replies += sent
        back = binomial(rng, sent, callback)
        m.callbacks += back
        for _ in range(binomial(rng, back, callback_conv)):
            gross = round(p["reddit_preis_median"] * math.exp(rng.gauss(0, 0.5)), 0)
            queue.append(Order(day, p["reddit_stunden"] * max(1.0, gross / 60), day + int(p["reddit_lieferfrist"]),
                               gross, gross * (1 - p["zahlung_gebuehr_reddit"]), "Reddit"))
        # Arbeiten: Fristen zuerst
        hours = float(p["stunden_pro_tag"])
        for o in sorted((o for o in queue if o.done_day is None and not o.cancelled), key=lambda o: o.due):
            if hours <= 0:
                break
            step = min(hours, o.left)
            o.left -= step
            hours -= step
            m.hours += step
            if o.left <= 1e-9:
                o.done_day = day
                if day > o.due and rng.random() < p["storno_bei_verspaetung"]:
                    o.cancelled = True  # Kunde storniert, Geld zurück
                    continue
                if m.first_order_day is None:
                    m.first_order_day = day
                if o.channel != "Reddit" and rng.random() < p["bewertung_quote"] * (0.5 if day > o.due else 1):
                    m.reviews += 1
        # Weit überfällige, unbegonnene Aufträge storniert Fiverr automatisch
        for o in queue:
            if o.done_day is None and not o.cancelled and day > o.due + 2 and o.left == o.hours:
                o.cancelled = True
        m.orders = queue
    return m


# --------------------------------------------------------------------------- #
# Auswertung
# --------------------------------------------------------------------------- #

def percentiles(values: list[float], qs: tuple[float, ...] = (0.1, 0.5, 0.9)) -> list[float]:
    s = sorted(values)
    if not s:
        return [0.0 for _ in qs]
    return [s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))] for q in qs]


def summarize(months: list[Month], p: dict[str, Any]) -> dict[str, Any]:
    days, pay = int(p["tage"]), int(p["auszahlung_nach_tagen"])
    rows: dict[str, list[float]] = {k: [] for k in (
        "bestellungen", "fiverr", "reddit", "umsatz", "netto", "ausgezahlt", "bewertungen",
        "stunden", "storniert", "impressionen", "klicks", "anfragen", "antworten", "erster_tag")}
    weeks: list[list[float]] = [[] for _ in range((days + 6) // 7)]
    channels: dict[str, float] = {}
    for m in months:
        done = m.done()
        rows["bestellungen"].append(len(done))
        rows["fiverr"].append(sum(1 for o in done if o.channel != "Reddit"))
        rows["reddit"].append(sum(1 for o in done if o.channel == "Reddit"))
        rows["umsatz"].append(sum(o.gross for o in done))
        rows["netto"].append(sum(o.net for o in done))
        rows["ausgezahlt"].append(sum(o.net for o in done if o.channel == "Reddit" or o.done_day + pay < days))
        rows["bewertungen"].append(m.reviews)
        rows["stunden"].append(m.hours)
        rows["storniert"].append(sum(1 for o in m.orders if o.cancelled))
        rows["impressionen"].append(m.impressions)
        rows["klicks"].append(m.clicks)
        rows["anfragen"].append(m.inquiries)
        rows["antworten"].append(m.replies)
        rows["erster_tag"].append(m.first_order_day + 1 if m.first_order_day is not None else days + 1)
        for w in range(len(weeks)):
            weeks[w].append(sum(o.net for o in done if o.done_day // 7 == w))
        for o in done:
            key = " ".join(o.channel.split()[:2])  # „Gig 2 Basic“ → „Gig 2“
            channels[key] = channels.get(key, 0) + o.net
    n = len(months)
    return {
        "n": n,
        "p": {k: percentiles(v) for k, v in rows.items()},
        "mittel": {k: sum(v) / n for k, v in rows.items()},
        "mind_ein_auftrag": sum(1 for v in rows["bestellungen"] if v >= 1) / n,
        "null_euro": sum(1 for v in rows["netto"] if v <= 0) / n,
        "ueber_500": sum(1 for v in rows["netto"] if v >= 500) / n,
        "wochen": [sum(w) / n for w in weeks],
        "kanaele": {k: v / n for k, v in sorted(channels.items(), key=lambda kv: -kv[1])},
    }


def run_scenario(p: dict[str, Any], gigs: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random(p["seed"])
    return summarize([simulate_month(p, gigs, rng) for _ in range(int(p["laeufe"]))], p)


def load_gigs(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    raw = (cfg.get("profile") or {}).get("pack_file") or "docs/profil-paket.json"
    path = Path(raw)
    path = path if path.is_absolute() else ROOT / path
    gigs = json.loads(path.read_text(encoding="utf-8")).get("gigs") or []
    return [g for g in gigs if len(g.get("packages") or []) == 3]


def build_params(cfg: dict[str, Any], overrides: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    from . import leads
    user = dict(cfg.get("simulation") or {})
    ist = user.pop("ist", None) or {}
    p = {**DEFAULTS, **{k: v for k, v in user.items() if v is not None}, **(overrides or {})}
    p = {k: (list(v) if isinstance(v, list) else v) for k, v in p.items()}
    notes: list[str] = []
    if p.get("reddit_auftraege_pro_tag") is None:
        rate, count, hours = learn_reddit_rate(leads.load_state(leads.state_path(cfg)))
        if rate is None:
            p["reddit_auftraege_pro_tag"] = 15.0
            notes.append("Reddit: noch zu wenig Daten im Auftrags-Gedächtnis – Annahme 15 neue Aufträge pro Tag.")
        else:
            p["reddit_auftraege_pro_tag"] = rate
            notes.append(f"Reddit: {count} neue Aufträge in {hours:.0f} h beobachtet → {rate:.0f} pro Tag "
                         f"(davon {p['reddit_passend']:.0%} passend ≈ {rate * p['reddit_passend']:.0f}/Tag).")
    notes += apply_observed(p, ist)
    return p, notes


SCENARIOS = [
    ("So wie geplant", {}),
    ("Doppelt so viele Reddit-Antworten (10/Tag)", {"antworten_pro_tag": 10}),
    ("Ohne Reddit, nur Fiverr", {"antworten_pro_tag": 0}),
    ("Nur 1,5 h Zeit pro Tag", {"stunden_pro_tag": 1.5}),
    ("Basic-Preise −20 % (mehr Bestellungen)", {"_rabatt": 0.2}),
]


def _gigs_for(gigs: list[dict[str, Any]], rabatt: float) -> list[dict[str, Any]]:
    if not rabatt:
        return gigs
    out = []
    for g in gigs:
        pk = [dict(x) for x in g["packages"]]
        pk[0]["price_usd"] = round(pk[0]["price_usd"] * (1 - rabatt))
        out.append({**g, "packages": pk})
    return out


def money(v: float) -> str:
    return f"{v:,.0f} $".replace(",", ".")


def report(cfg: dict[str, Any], overrides: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    p, notes = build_params(cfg, overrides)
    gigs = load_gigs(cfg)
    if not gigs:
        raise ValueError("Keine Gigs mit 3 Paketen im Profil-Paket gefunden.")
    base = run_scenario(p, gigs)
    scen = []
    for name, ov in SCENARIOS[1:]:
        ov = dict(ov)
        rabatt = ov.pop("_rabatt", 0)
        q = {**p, **ov}
        if rabatt:  # Rabatt verschiebt den Mix Richtung Basic und hebt die Umwandlung leicht
            a, b = q["bestellrate"]
            q["bestellrate"] = [a * (1 + rabatt), b]
        scen.append((name, run_scenario(q, _gigs_for(gigs, rabatt))))

    P, M = base["p"], base["mittel"]
    L: list[str] = []
    L.append(f"# Simulation: dein erster Monat ({p['tage']} Tage)\n")
    L.append(f"{base['n']} simulierte Monate, ab Veröffentlichung der 3 Gigs. Beträge in US-Dollar nach Gebühren. "
             "**Das ist keine Vorhersage**, sondern eine Spanne aus Annahmen. Sie wird genauer, sobald du unter "
             "`simulation: ist:` deine echten Fiverr-Zahlen einträgst.\n")
    L.append("## Auf einen Blick\n")
    L.append("| | schlecht (10 %) | typisch (Median) | gut (90 %) |")
    L.append("|---|---:|---:|---:|")
    for key, label, fmt in [
        ("bestellungen", "Erledigte Aufträge", "{:.0f}"), ("fiverr", "davon Fiverr", "{:.0f}"),
        ("reddit", "davon Reddit", "{:.0f}"), ("netto", "Verdient (netto)", None),
        ("ausgezahlt", "Schon auf dem Konto", None), ("bewertungen", "Bewertungen", "{:.0f}"),
        ("stunden", "Arbeitsstunden", "{:.0f} h"), ("impressionen", "Fiverr-Impressionen", "{:.0f}"),
        ("klicks", "Fiverr-Klicks", "{:.0f}"), ("erster_tag", "Erster Auftrag an Tag", "{:.0f}"),
    ]:
        vals = P[key] if key != "erster_tag" else list(reversed(P[key]))
        cells = [money(v) if fmt is None else fmt.format(v) for v in vals]
        if key == "erster_tag":
            cells = [c if float(c) <= p["tage"] else "keiner" for c in cells]
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L.append("")
    L.append(f"- Wahrscheinlichkeit für **mindestens einen Auftrag**: {base['mind_ein_auftrag']:.0%}")
    L.append(f"- Wahrscheinlichkeit für **0 $**: {base['null_euro']:.0%}")
    L.append(f"- Wahrscheinlichkeit für **500 $ oder mehr**: {base['ueber_500']:.0%}")
    L.append(f"- Fiverr-Geld wird erst {p['auszahlung_nach_tagen']} Tage nach Abschluss frei, deshalb ist „auf dem Konto“ kleiner als „verdient“.\n")
    L.append("## Verlauf (Durchschnitt netto je Woche)\n")
    labels = [f"Tag {7 * i + 1}–{min(7 * i + 7, p['tage'])}" for i in range(len(base["wochen"]))]
    L.append("| | " + " | ".join(labels) + " |")
    L.append("|---|" + "---:|" * len(base["wochen"]))
    L.append("| netto | " + " | ".join(money(v) for v in base["wochen"]) + " |\n")
    w = base["wochen"]
    if len(w) >= 4 and w[3] > w[0] * 1.2:
        L.append("Die Kurve steigt: Jede Bewertung bringt mehr Sichtbarkeit auf Fiverr.\n")
    else:
        L.append("Die Kurve bleibt flach: Ohne Bewertungen wächst Fiverr kaum, und nach dem „Neuer-Gig-Schub“ "
                 f"({p['start_schub_tage']} Tage) sinkt die Sichtbarkeit wieder. Die letzte Spalte ist kürzer.\n")
    L.append("## Woher das Geld kommt (Durchschnitt)\n")
    names = {f"Gig {i + 1}": g.get("title", "")[:60] for i, g in enumerate(gigs)}
    for k, v in base["kanaele"].items():
        L.append(f"- {k}{(' – ' + names[k]) if k in names else ''}: {money(v)}")
    L.append("")
    L.append("## Was wäre, wenn …\n")
    L.append("| Variante | Aufträge (Median) | netto Median | netto 90 % | ≥ 1 Auftrag |")
    L.append("|---|---:|---:|---:|---:|")
    for name, s in [(SCENARIOS[0][0], base)] + scen:
        L.append(f"| {name} | {s['p']['bestellungen'][1]:.0f} | {money(s['p']['netto'][1])} | "
                 f"{money(s['p']['netto'][2])} | {s['mind_ein_auftrag']:.0%} |")
    L.append("")
    L.append("## Was die Zahlen sagen\n")
    L += advice(base, scen, p)
    L.append("\n## Gelernt aus deinen Daten\n")
    L += [f"- {n}" for n in notes] or ["- Noch keine echten Zahlen eingetragen, alles beruht auf Annahmen."]
    L.append("\n## Annahmen (in `config.yaml` unter `simulation:` änderbar)\n")
    L.append(f"- Fiverr je Gig: {p['impressionen_pro_tag']:.0f} Impressionen/Tag (×{p['start_schub']} in den ersten "
             f"{p['start_schub_tage']} Tagen), Klickrate {beta_mean(p['klickrate']):.1%}, "
             f"Bestellung je Klick {beta_mean(p['bestellrate']):.1%}, Anfragen je Klick {beta_mean(p['anfragerate']):.1%}, "
             f"davon {beta_mean(p['anfrage_zu_auftrag']):.0%} Auftrag")
    L.append(f"- Jede Bewertung: +{p['bewertungs_bonus']:.0%} Sichtbarkeit und Umwandlung (bis 5 Bewertungen); "
             f"{p['bewertung_quote']:.0%} der Kunden bewerten")
    L.append(f"- Paket-Mix Basic/Standard/Premium: {' / '.join(f'{x:.0%}' for x in p['paket_mix'])}; "
             f"Aufwand {' / '.join(f'{x:g} h' for x in p['stunden_je_paket'])}")
    L.append(f"- Reddit: {p['reddit_auftraege_pro_tag']:.0f} neue Aufträge/Tag, {p['reddit_passend']:.0%} passend, "
             f"du antwortest auf {p['antworten_pro_tag']}/Tag; {beta_mean(p['antwort_rueckmeldung']):.0%} melden sich, "
             f"davon {beta_mean(p['rueckmeldung_zu_auftrag']):.0%} Auftrag, typisch {money(p['reddit_preis_median'])}")
    L.append(f"- Arbeitszeit {p['stunden_pro_tag']:g} h/Tag; verspätet geliefert → {p['storno_bei_verspaetung']:.0%} Stornierung; "
             f"Fiverr-Gebühr {p['fiverr_gebuehr']:.0%}")
    L.append("\n## Echte Zahlen eintragen (macht die Simulation genauer)\n")
    L.append("In der Fiverr-App unter *Analytics* bzw. *Gigs → Impressions/Clicks* ablesen und in `config.yaml` eintragen:\n")
    L.append("```yaml\nsimulation:\n  ist:\n    tage: 7            # seit wie vielen Tagen die Gigs online sind\n    gigs: 3\n"
             "    impressionen: 0    # Summe aller Gigs\n    klicks: 0\n    bestellungen: 0\n    anfragen: 0\n"
             "    reddit_antworten: 0       # wie viele Antworten du verschickt hast\n"
             "    reddit_rueckmeldungen: 0  # wie viele zurückgeschrieben haben\n    reddit_auftraege: 0\n```\n")
    L.append("Danach `python -m goldbot simulation` neu starten.")
    return "\n".join(L) + "\n", {"base": base, "scenarios": scen, "params": p, "notes": notes}


def advice(base: dict[str, Any], scen: list[tuple[str, dict[str, Any]]], p: dict[str, Any]) -> list[str]:
    out: list[str] = []
    med = base["p"]["netto"][1]
    reddit_share = base["kanaele"].get("Reddit", 0) / max(1e-9, sum(base["kanaele"].values()))
    by = dict(scen)
    if reddit_share > 0.4:
        out.append(f"- **Reddit ist im ersten Monat dein wichtigster Kanal** ({reddit_share:.0%} des Geldes). "
                   "Fiverr braucht erst Bewertungen. Jeden Tag auf die passenden Aufträge antworten lohnt sich am meisten.")
    more = by.get("Doppelt so viele Reddit-Antworten (10/Tag)")
    if more and more["p"]["netto"][1] > med * 1.15:
        out.append(f"- 10 statt {p['antworten_pro_tag']} Antworten am Tag heben den Median von {money(med)} auf "
                   f"{money(more['p']['netto'][1])}. Das sind etwa 15 Minuten mehr am Tag.")
    elif more:
        out.append("- Mehr als 5 Antworten am Tag bringen wenig. Es gibt nicht mehr passende Aufträge, "
                   "Qualität vor Menge.")
    less = by.get("Nur 1,5 h Zeit pro Tag")
    if less and less["p"]["netto"][1] < med * 0.9:
        out.append(f"- Mit nur 1,5 h am Tag gehen Aufträge verloren (verspätet → storniert): Median {money(less['p']['netto'][1])}.")
    else:
        out.append("- Zeit ist im ersten Monat nicht der Engpass, sondern Sichtbarkeit. 1,5 h am Tag reichen meist.")
    cheap = by.get("Basic-Preise −20 % (mehr Bestellungen)")
    if cheap:
        a, b = cheap["mind_ein_auftrag"], base["mind_ein_auftrag"]
        if a > b + 0.02:
            out.append(f"- Günstigere Basic-Pakete machen den ersten Auftrag wahrscheinlicher ({a:.0%} statt {b:.0%}). "
                       "Für die ersten Bewertungen sinnvoll, danach wieder anheben.")
        else:
            out.append(f"- Billigere Basic-Pakete bringen kaum etwas ({a:.0%} statt {b:.0%} für ≥ 1 Auftrag). "
                       "Lieber bei den jetzigen Preisen bleiben.")
    out.append("- Die erste Bewertung ist der Wendepunkt: schnell liefern (vor der Frist) und den Kunden freundlich "
               "um eine Bewertung bitten.")
    return out


def write(cfg: dict[str, Any], overrides: dict[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    text, data = report(cfg, overrides)
    path = output_dir(cfg) / "simulation.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, data
