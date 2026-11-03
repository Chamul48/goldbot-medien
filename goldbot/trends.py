"""Trend- und Chancen-Scanner.

Nutzt ausschließlich öffentliche Feeds und offizielle APIs (kein Scraping
hinter Logins, keine Umgehung von Schutzmaßnahmen):
  - Google Trends (Tages-Trends als RSS, je Land)
  - Reddit (öffentliche RSS-Feeds von Subreddits, z. B. r/forhire für Aufträge)
  - Hacker News (Algolia-Such-API)
  - beliebige weitere RSS/Atom-Feeds aus der Konfiguration
"""

from __future__ import annotations

import html
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable
from urllib.parse import quote_plus, urlparse

import requests

log = logging.getLogger(__name__)

USER_AGENT = "goldbot-trendscanner/0.1 (personal research tool)"
TIMEOUT = 20

HIRING_RE = re.compile(r"\[(hiring|task|paid)\]", re.I)
# Aufträge ohne Tag, z. B. "Looking for a video editor for TikTok" oder
# "Need someone to edit my videos". Zählt nur in Auftrags-Subreddits.
HIRING_PHRASE_RE = re.compile(
    r"\b(looking for|need(ed|ing)?|seeking|searching for|hiring|suche)\s+"
    r"(an?\s+|some\s+|einen?\s+)?([\w/&+-]+\s+){0,3}?"
    r"(video\s?)?(editors?|cutters?|creators?|videograph\w*)\b"
    r"|\bneed(ed|ing)?\s+(someone|somebody|help)\s+to\s+edit\b",
    re.I,
)
# Fragen und Hilfe-Posts sind keine Aufträge
QUESTION_RE = re.compile(
    r"\b(feedback|advice|tips?|critique|review my|opinions?|how (do|to|can)|do i need|"
    r"is it worth|recommend(ation)?s?)\b",
    re.I,
)
# Unbezahlt / Hobby
UNPAID_RE = re.compile(r"\[(hobby|unpaid|free|collab)\]|\b(unpaid|for free|no budget|rev(enue)? ?share)\b", re.I)
# Anbieter (Konkurrenz) – mit und ohne Tag
FORHIRE_RE = re.compile(
    r"\[(for ?hire|offer|available)\]|^\s*for hire\b|\b(i'?m|i am) an? [\w ]{0,20}?(editor|creator)\b|"
    r"\b(hire me|my services|dm me|available for (work|hire|projects)|searching for clients|"
    r"looking for (new )?(clients|work|projects)|disponível|disponible|creo videos)\b",
    re.I,
)
# Subreddits, in denen auch Posts ohne [Hiring]-Tag als Auftrag zählen
HIRING_SUBREDDITS = {"forhire", "hireaneditor", "videoeditingrequests", "freelance_forhire"}
PRICE_RE = re.compile(r"(?:\$|€|usd|eur)\s?\d[\d.,]*|\d[\d.,]*\s?(?:\$|€|usd|eur)\b", re.I)


@dataclass
class TrendItem:
    source: str
    title: str
    url: str = ""
    published: str = ""
    summary: str = ""
    traffic: int = 0
    kind: str = "trend"  # "trend", "auftrag" oder "konkurrenz"
    price: str = ""
    category: str = ""  # bei Reddit: Subreddit, z. B. "HireAnEditor"
    matched: list[str] = field(default_factory=list)
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def _clean_text(text: str | None, limit: int = 300) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _parse_traffic(value: str) -> int:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else 0


def parse_feed(xml_text: str, source: str) -> list[TrendItem]:
    """Parst RSS 2.0 und Atom. Robust gegenüber fremden Namespaces."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("%s: Feed nicht lesbar (%s)", source, exc)
        return []

    items: list[TrendItem] = []
    for node in root.iter():
        if _strip(node.tag) not in ("item", "entry"):
            continue
        data: dict[str, str] = {}
        for child in node:
            name = _strip(child.tag)
            if name == "link":
                data.setdefault("link", child.get("href") or (child.text or "").strip())
            elif name in ("title", "pubDate", "published", "updated", "approx_traffic"):
                data.setdefault(name, (child.text or "").strip())
            elif name in ("description", "summary", "content"):
                data.setdefault("summary", child.text or "")
            elif name == "category":
                label = child.get("term") or child.get("label") or (child.text or "")
                data.setdefault("category", label.strip().removeprefix("r/"))
        title = _clean_text(data.get("title"), 200)
        if not title:
            continue
        items.append(
            TrendItem(
                source=source,
                title=title,
                url=data.get("link", ""),
                published=data.get("pubDate") or data.get("published") or data.get("updated", ""),
                summary=_clean_text(data.get("summary")),
                traffic=_parse_traffic(data.get("approx_traffic", "")),
                category=data.get("category", ""),
            )
        )
    return items


def parse_hackernews(payload: dict[str, Any], source: str) -> list[TrendItem]:
    items = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title")
        if not title:
            continue
        # HN markiert Vorträge mit "[video]" / "[pdf]" – das ist kein Themen-Treffer
        title = re.sub(r"\s*\[(video|pdf|audio)\]", "", title, flags=re.I)
        items.append(
            TrendItem(
                source=source,
                title=_clean_text(title, 200),
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                published=hit.get("created_at", ""),
                traffic=int(hit.get("points") or 0),
            )
        )
    return items


# --------------------------------------------------------------------------- #
# Abruf
# --------------------------------------------------------------------------- #

class Fetcher:
    """HTTP-Abruf mit Höflichkeits-Pause zwischen Anfragen."""

    def __init__(self, delay: float = 2.0, session: requests.Session | None = None):
        self.delay = delay
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last = 0.0
        self.sleep = time.sleep

    # Reddit drosselt anonyme Abrufe stark – dort länger warten.
    HOST_DELAY = {"www.reddit.com": 8.0}
    MAX_RETRIES = 2

    def _pause(self, url: str) -> None:
        host = urlparse(url).netloc
        delay = max(self.delay, self.HOST_DELAY.get(host, 0.0)) if self.delay else 0.0
        wait = delay - (time.monotonic() - self._last)
        if wait > 0:
            self.sleep(wait)
        self._last = time.monotonic()

    def get(self, url: str) -> requests.Response | None:
        for attempt in range(self.MAX_RETRIES + 1):
            self._pause(url)
            try:
                resp = self.session.get(url, timeout=TIMEOUT)
            except requests.RequestException as exc:
                log.warning("Abruf fehlgeschlagen: %s (%s)", url, exc.__class__.__name__)
                return None
            if resp.status_code == 429 and attempt < self.MAX_RETRIES:
                try:
                    retry_after = float(resp.headers.get("Retry-After", ""))
                except ValueError:
                    retry_after = 15.0 * (attempt + 1)
                retry_after = min(max(retry_after, 5.0), 60.0)
                log.info("%s drosselt (429) – neuer Versuch in %.0f s.", urlparse(url).netloc, retry_after)
                self.sleep(retry_after)
                continue
            if resp.status_code != 200:
                log.warning("Abruf %s -> HTTP %s", url, resp.status_code)
                return None
            return resp
        return None


def collect(
    cfg: dict[str, Any], fetcher: Fetcher | None = None, only: tuple[str, ...] | None = None
) -> tuple[list[TrendItem], list[str]]:
    """Sammelt Einträge aus allen konfigurierten Quellen.

    Gibt (Einträge, Fehlerliste) zurück. Eine ausgefallene Quelle stoppt nicht den Lauf.
    """
    tcfg = cfg.get("trends", {})
    limit = int(tcfg.get("max_items_per_source", 25))
    fetcher = fetcher or Fetcher(delay=float(tcfg.get("request_delay_seconds", 2)))

    jobs: list[tuple[str, str, Callable[[requests.Response, str], list[TrendItem]]]] = []
    feed = lambda r, s: parse_feed(r.text, s)  # noqa: E731
    hn = lambda r, s: parse_hackernews(r.json(), s)  # noqa: E731

    use = lambda kind: only is None or kind in only  # noqa: E731

    for geo in (tcfg.get("google_trends_geo", []) if use("google") else []):
        jobs.append((f"Google Trends {geo}", f"https://trends.google.com/trending/rss?geo={geo}", feed))
    subs = tcfg.get("reddit_subreddits", []) if use("reddit") else []
    if subs:
        # Ein einziger Sammel-Feed statt einer Anfrage pro Subreddit –
        # Reddit drosselt anonyme Abrufe sonst sofort (HTTP 429).
        joined = "+".join(subs)
        jobs.append((f"Reddit r/{joined}", f"https://www.reddit.com/r/{joined}/new/.rss?limit=100", feed))
    for query in (tcfg.get("hackernews_queries", []) if use("hackernews") else []):
        url = ("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage="
               f"{limit}&query={quote_plus(query)}")
        jobs.append((f"Hacker News '{query}'", url, hn))
    for url in (tcfg.get("rss_feeds", []) if use("rss") else []):
        jobs.append((f"RSS {url}", url, feed))

    items: list[TrendItem] = []
    errors: list[str] = []
    for name, url, parser in jobs:
        resp = fetcher.get(url)
        if resp is None:
            errors.append(name)
            continue
        try:
            parsed = parser(resp, name)
        except (ValueError, KeyError) as exc:
            log.warning("%s: Antwort nicht auswertbar (%s)", name, exc)
            errors.append(name)
            continue
        cap = limit * max(len(subs), 1) if name.startswith("Reddit") else limit
        for item in parsed[:cap]:
            if name.startswith("Reddit") and item.category:
                item.source = f"Reddit r/{item.category}"
            items.append(item)
    return items, errors


# --------------------------------------------------------------------------- #
# Bewertung
# --------------------------------------------------------------------------- #

def _plain(title: str) -> str:
    """Markdown-Zeichen wie _FETT_ oder **fett** entfernen, damit Wortgrenzen stimmen."""
    return re.sub(r"[_*~`]+", " ", title)


def is_job_post(item: TrendItem) -> bool:
    """Echter, bezahlter Auftrag? (Anbieter vorher schon aussortiert)"""
    title = _plain(item.title)
    if UNPAID_RE.search(title) or QUESTION_RE.search(title):
        return False
    if HIRING_RE.search(title):
        return True
    # Ohne Tag nur in Subreddits, in denen gezielt Aufträge gepostet werden
    sub = (item.category or "").lower()
    in_hiring_sub = sub in HIRING_SUBREDDITS or (not sub and any(
        f"r/{name}" in item.source.lower() and "+" not in item.source for name in HIRING_SUBREDDITS))
    return in_hiring_sub and bool(HIRING_PHRASE_RE.search(title))


def score(items: Iterable[TrendItem], keywords: list[str]) -> list[TrendItem]:
    """Bewertet Einträge nach Relevanz für deine Nische und sortiert absteigend."""
    # Ab 4 Zeichen auch als Wortanfang (Deutsch: "gold" -> "Goldpreis"),
    # kurze Wörter wie "ai" nur exakt (sonst Treffer in "air").
    patterns = {
        kw: re.compile(rf"\b{re.escape(kw.lower())}" + ("" if len(kw) >= 4 else r"\b"))
        for kw in keywords
    }
    scored = []
    for item in items:
        text = f"{item.title} {item.summary}".lower()
        item.matched = [kw for kw, pat in patterns.items() if pat.search(text)]
        s = 2.0 * len(item.matched)
        is_reddit = item.source.startswith("Reddit")
        if is_reddit and FORHIRE_RE.search(_plain(item.title)):
            # Andere Anbieter: kein Trend, aber nützlich für den Preisvergleich
            item.kind = "konkurrenz"
            price = PRICE_RE.search(f"{item.title} {item.summary}")
            item.price = price.group(0) if price else ""
        elif is_reddit and is_job_post(item):
            item.kind = "auftrag"
            s += 3.0 if item.matched else 0.5
        if item.traffic:
            # Logarithmisch, damit riesige Zahlen nicht alles dominieren
            s += min(len(str(item.traffic)) * 0.5, 3.0)
        item.score = round(s, 2)
        scored.append(item)
    scored.sort(key=lambda i: i.score, reverse=True)
    return scored


def dedupe(items: Iterable[TrendItem]) -> list[TrendItem]:
    seen: set[str] = set()
    out = []
    for item in items:
        key = re.sub(r"\W+", "", item.title.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def scan(
    cfg: dict[str, Any], fetcher: Fetcher | None = None, only: tuple[str, ...] | None = None
) -> tuple[list[TrendItem], list[str]]:
    """only: z. B. ("reddit",) für den schnellen Auftrags-Check."""
    items, errors = collect(cfg, fetcher, only)
    keywords = cfg.get("trends", {}).get("keywords", [])
    return score(dedupe(items), keywords), errors
