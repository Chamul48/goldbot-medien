"""Muster-Videos für dein Portfolio – mit echtem Bildmaterial (9:16).

Jedes Video ist ein fertiger Kurzvideo-Schnitt:
  - echte Stockvideos je Szene (Pixabay, Lizenz erlaubt kommerzielle Nutzung, ohne Quellenangabe)
  - natürliche Sprecherstimme (Microsoft-Neural-Stimme über edge-tts, kostenlos)
  - Untertitel Wort für Wort im Takt der Stimme, aktives Wort in Akzentfarbe
  - Schnitt mit Zoom-Punch, langsamer Push-in, Farbkorrektur, Vignette
  - Fortschrittsbalken, Themen-Etikett, leise Hintergrundmusik und Whoosh bei jedem Schnitt

Fehlt der Pixabay-Schlüssel oder das Internet, nimmt eine Szene einen bewegten Farbverlauf;
fehlt edge-tts, gibt es Musik und zeitlich verteilte Untertitel ohne Stimme.

Inhalte sind allgemeines Wissen ohne Kursdaten, Prognosen oder Anlagetipps.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests

log = logging.getLogger(__name__)

W, H, FPS = 1080, 1920, 30
PIXABAY_URL = "https://pixabay.com/api/videos/"
CACHE_DAYS = 7
MAX_CLIP_BYTES = 80_000_000

DEMOS: list[dict[str, Any]] = [
    {
        "name": "gold_de", "lang": "de", "colors": ("0x14100a", "0x5c4512"), "accent": "0xd4a017",
        "chip": "GOLD-WISSEN",
        "hook": "3 Fakten über Gold, die kaum jemand kennt", "highlight": ["Gold,"],
        "lines": ["Gold rostet nicht – es bleibt jahrtausendelang glänzend.",
                  "Alles je geförderte Gold passt in einen Würfel von rund 22 Metern.",
                  "Blattgold ist sogar essbar: Lebensmittelzusatz E 175."],
        "cta": "Folge für mehr Edelmetall-Wissen",
        "footer": "Beispiel-Edit · keine Anlageberatung",
        "clips": ["gold bars", "gold jewelry", "gold bullion", "gold flakes", "gold coins"],
    },
    {
        "name": "gold_en", "lang": "en", "colors": ("0x14100a", "0x5c4512"), "accent": "0xd4a017",
        "chip": "GOLD FACTS",
        "hook": "3 gold facts most people don't know", "highlight": ["gold"],
        "lines": ["Gold doesn't rust – it stays shiny for thousands of years.",
                  "All the gold ever mined fits in a cube of about 22 metres.",
                  "Gold leaf is even edible: food additive E 175."],
        "cta": "Follow for more precious metal facts",
        "footer": "Sample edit · not financial advice",
        "clips": ["gold bars", "gold jewelry", "gold bullion", "gold flakes", "gold coins"],
    },
    {
        "name": "finanzen_de", "lang": "de", "colors": ("0x07131f", "0x0f4c5c"), "accent": "0x1dbf73",
        "chip": "GELD-BASICS",
        "hook": "Die 50/30/20-Regel in 15 Sekunden", "highlight": ["50/30/20-Regel"],
        "lines": ["50 % deines Nettoeinkommens für Fixkosten: Miete, Essen, Versicherung.",
                  "30 % für Wünsche: Hobbys, Urlaub, Ausgehen.",
                  "20 % zum Sparen und für Rücklagen."],
        "cta": "Speichern und später nachrechnen",
        "footer": "Beispiel-Edit · keine Finanzberatung",
        "clips": ["money counting", "grocery shopping", "travel suitcase", "piggy bank", "calculator money"],
    },
    {
        "name": "finance_en", "lang": "en", "colors": ("0x07131f", "0x0f4c5c"), "accent": "0x1dbf73",
        "chip": "MONEY BASICS",
        "hook": "The 50/30/20 rule in 15 seconds", "highlight": ["50/30/20"],
        "lines": ["50% of your take-home pay for needs: rent, food, insurance.",
                  "30% for wants: hobbies, travel, going out.",
                  "20% for savings and an emergency fund."],
        "cta": "Save this for your next budget",
        "footer": "Sample edit · not financial advice",
        "clips": ["money counting", "grocery shopping", "travel suitcase", "piggy bank", "calculator money"],
    },
    {
        "name": "krypto_de", "lang": "de", "colors": ("0x120a1f", "0x3b1e6b"), "accent": "0xf7931a",
        "chip": "KRYPTO-BASICS",
        "hook": "Was ist eine Blockchain? Einfach erklärt", "highlight": ["Blockchain?"],
        "lines": ["Eine Blockchain ist eine Kette aus Datenblöcken.",
                  "Jeder Block enthält einen Fingerabdruck des vorherigen.",
                  "Wer einen Block ändert, müsste alle folgenden mit ändern."],
        "cta": "Folge für mehr Krypto-Grundlagen",
        "footer": "Beispiel-Edit · keine Anlageberatung",
        "clips": ["blockchain", "network technology", "fingerprint", "dominoes falling", "bitcoin coin"],
    },
    {
        "name": "crypto_en", "lang": "en", "colors": ("0x120a1f", "0x3b1e6b"), "accent": "0xf7931a",
        "chip": "CRYPTO BASICS",
        "hook": "What is a blockchain? Explained simply", "highlight": ["blockchain?"],
        "lines": ["A blockchain is a chain of data blocks.",
                  "Every block holds a fingerprint of the one before it.",
                  "Changing one block means changing every block after it."],
        "cta": "Follow for more crypto basics",
        "footer": "Sample edit · not financial advice",
        "clips": ["blockchain", "network technology", "fingerprint", "dominoes falling", "bitcoin coin"],
    },
]

VOICES = {"de": "de-DE-ConradNeural", "en": "en-US-AndrewNeural"}

# (Datei, Familienname für libass)
FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\seguibl.ttf", "Segoe UI Black"),
    (r"C:\Windows\Fonts\segoeuib.ttf", "Segoe UI"),
    (r"C:\Windows\Fonts\arialbd.ttf", "Arial"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVu Sans"),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "Arial"),
]


# --------------------------------------------------------------------------- #
# Werkzeuge finden
# --------------------------------------------------------------------------- #

def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    # WinGet installiert ffmpeg oft außerhalb des PATH der aktuellen Sitzung
    base = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for exe in base.glob("*FFmpeg*/**/bin/ffmpeg.exe"):
        return str(exe)
    return None


def _ffprobe(ffmpeg: str) -> str:
    p = Path(ffmpeg)
    probe = p.with_name("ffprobe" + p.suffix)
    return str(probe) if probe.exists() else (shutil.which("ffprobe") or "ffprobe")


def find_font() -> tuple[str, str] | None:
    return next(((f, fam) for f, fam in FONT_CANDIDATES if Path(f).exists()), None)


def duration(path: Path, ffmpeg: str) -> float:
    out = subprocess.run([_ffprobe(ffmpeg), "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


# --------------------------------------------------------------------------- #
# Bildmaterial: Pixabay
# --------------------------------------------------------------------------- #

def pixabay_key(cfg: dict[str, Any] | None = None) -> str | None:
    """Schlüssel aus der Umgebung, aus .env im Projekt oder aus muster.pixabay_env (Pfad zu einer .env).

    Der Wert wird nie geloggt.
    """
    if os.environ.get("PIXABAY_API_KEY"):
        return os.environ["PIXABAY_API_KEY"].strip()
    from .config import ROOT
    files = [ROOT / ".env"]
    extra = ((cfg or {}).get("muster") or {}).get("pixabay_env")
    if extra:
        files.append(Path(os.path.expandvars(os.path.expanduser(str(extra)))))
    for f in files:
        try:
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                key, _, value = line.partition("=")
                if key.strip().removeprefix("export ").strip() == "PIXABAY_API_KEY":
                    value = value.strip().strip('"').strip("'")
                    if value and not value.endswith("..."):
                        return value
        except OSError:
            continue
    return None


def _pick_size(videos: dict[str, Any]) -> dict[str, Any] | None:
    """Hochformat: kleinste Fassung mit voller Höhe. Querformat: größte (wird auf 9:16 beschnitten)."""
    sizes = [v for v in videos.values() if isinstance(v, dict) and v.get("url") and v.get("width")]
    if not sizes:
        return None
    vertical = [v for v in sizes if v["height"] > v["width"]]
    if vertical:
        full = [v for v in vertical if v["height"] >= H]
        return min(full, key=lambda v: v.get("size") or 0) if full else max(vertical, key=lambda v: v["height"])
    return max(sizes, key=lambda v: v["width"])


def relevance(hit: dict[str, Any], query: str) -> tuple[bool, int]:
    """(alle Suchwörter in den Schlagwörtern?, Bonus für genaue Wortgruppe/Schlagwort an 1. Stelle)."""
    tags = [t.strip().lower() for t in str(hit.get("tags", "")).split(",") if t.strip()]
    words = query.lower().split()
    tokens = {w for t in tags for w in re.findall(r"[a-z0-9]+", t)}

    def has(word: str) -> bool:  # „bar“ passt auch zu „bars“
        return any(tok == word or tok.rstrip("s") == word.rstrip("s") for tok in tokens)

    if any(re.search(r"green ?screen|chroma|alpha channel|transparent|green background|overlay", t) for t in tags):
        return False, 0  # Freistell-Material (grüner Hintergrund) ist kein fertiges Bild
    phrase = " ".join(words)
    bonus = (2 if any(phrase in t or phrase.rstrip("s") in t for t in tags) else 0) + \
            (1 if tags and phrase.rstrip("s") in tags[0] else 0)
    return all(has(w) for w in words), bonus


class Footage:
    """Sucht und lädt passende Clips; Suchergebnisse und Clips werden zwischengespeichert."""

    def __init__(self, folder: Path, key: str | None, session: requests.Session | None = None):
        self.folder = folder
        self.key = key
        self.session = session or requests.Session()
        self.cache_file = folder / "suche.json"
        try:
            self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.cache = {}

    def search(self, query: str) -> list[dict[str, Any]]:
        entry = self.cache.get(query)
        if entry and time.time() - entry.get("ts", 0) < CACHE_DAYS * 86400:
            return entry["hits"]
        if not self.key:
            return []
        try:
            resp = self.session.get(PIXABAY_URL, params={
                "key": self.key, "q": query, "per_page": 30, "safesearch": "true", "order": "popular"},
                timeout=20)
        except requests.RequestException as exc:
            log.warning("Pixabay nicht erreichbar (%s).", exc.__class__.__name__)
            return []
        if resp.status_code != 200:
            log.warning("Pixabay-Suche '%s' -> HTTP %s", query, resp.status_code)
            return []
        hits = [h for h in resp.json().get("hits", []) if isinstance(h, dict)]
        self.cache[query] = {"ts": time.time(), "hits": hits}
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")
        return hits

    def pick(self, query: str, min_seconds: float, used: set[int]) -> Path | None:
        """Bester unbenutzter Clip, der wirklich zum Suchbegriff passt.

        Pixabay liefert bei „gold bars“ auch gelbe Blumen – daher zählen nur Treffer, deren
        Schlagwörter ALLE Suchwörter enthalten. Danach: genaue Wortgruppe, echtes Video vor
        Animation, Hochformat, volle Auflösung, Beliebtheit.
        """
        hits = [h for h in self.search(query) if h.get("id") not in used
                and float(h.get("duration") or 0) >= min(min_seconds, 6) and relevance(h, query)[0]]

        def rank(h: dict[str, Any]) -> tuple:
            size = _pick_size(h.get("videos") or {}) or {}
            # Echtes Video schlägt Animation (3D-Schriftzüge wirken billig)
            return (h.get("type") == "film", relevance(h, query)[1], size.get("height", 0) > size.get("width", 1),
                    size.get("height", 0) >= H or size.get("width", 0) >= 3000, h.get("downloads", 0))

        for hit in sorted(hits, key=rank, reverse=True)[:5]:
            path = self.download(hit)
            if path:
                used.add(hit["id"])
                return path
        return None

    def download(self, hit: dict[str, Any]) -> Path | None:
        size = _pick_size(hit.get("videos") or {})
        if not size or (size.get("size") or 0) > MAX_CLIP_BYTES:
            return None
        target = self.folder / f"pixabay_{hit['id']}_{size['width']}x{size['height']}.mp4"
        if target.exists() and target.stat().st_size > 10_000:
            return target
        self.folder.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(".teil")
        try:
            with self.session.get(size["url"], stream=True, timeout=60) as r:
                if r.status_code != 200:
                    return None
                with open(part, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
            os.replace(part, target)
        except (requests.RequestException, OSError) as exc:
            log.warning("Clip %s nicht geladen (%s).", hit.get("id"), exc.__class__.__name__)
            part.unlink(missing_ok=True)
            return None
        return target


# --------------------------------------------------------------------------- #
# Stimme
# --------------------------------------------------------------------------- #

def speak(text: str, voice: str, target: Path, timeout: float = 60.0) -> list[tuple[float, float, str]] | None:
    """Text vertonen (edge-tts). Gibt Wortgrenzen (von, bis, wort) zurück oder None, wenn keine Stimme."""
    try:
        import edge_tts
    except ImportError:
        return None
    result: dict[str, Any] = {}

    async def run() -> None:
        try:
            com = edge_tts.Communicate(text, voice, rate="+6%", boundary="WordBoundary")
        except TypeError:  # ältere edge-tts
            com = edge_tts.Communicate(text, voice, rate="+6%")
        audio, marks = [], []
        async for chunk in com.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                audio.append(chunk["data"])
            elif chunk.get("type") == "WordBoundary":
                start = float(chunk.get("offset", 0)) / 1e7
                marks.append((start, start + float(chunk.get("duration", 0)) / 1e7, str(chunk.get("text", ""))))
        result["audio"], result["marks"] = b"".join(audio), marks

    def thread() -> None:
        try:
            asyncio.run(run())
        except BaseException as exc:  # noqa: B902 – Fehler an den Aufrufer melden
            result["error"] = exc

    th = threading.Thread(target=thread, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive() or "error" in result or not result.get("audio"):
        log.warning("Stimme nicht verfügbar (%s) – Video ohne Sprecher.", result.get("error") or "Zeitüberschreitung")
        return None
    target.write_bytes(result["audio"])
    return result["marks"]


def word_times(text: str, marks: list[tuple[float, float, str]] | None, length: float) -> list[tuple[float, float, str]]:
    """Zeit für jedes geschriebene Wort.

    Die Stimme spricht Zahlen anders aus, als sie dastehen („22“ → „zweiundzwanzig“). Daher wird
    nicht Wort für Wort zugeordnet, sondern über den Textanteil: ein Wort bei 40 % des Textes
    startet dort, wo die Stimme 40 % ihrer Wörter gesprochen hat.
    """
    words: list[str] = []
    for token in text.split():
        if words and not re.search(r"\w", token):  # „–“ allein ist kein Wort: an das vorige hängen
            words[-1] += " " + token if token not in "–—-" else ""
        else:
            words.append(token)
    if not words:
        return []
    chars = [len(w) + 1 for w in words]
    total = float(sum(chars))
    pos = [sum(chars[:i]) / total for i in range(len(words))] + [1.0]

    if marks:
        mchars = [len(m[2]) + 1 for m in marks]
        mt = float(sum(mchars))
        xs = [sum(mchars[:i]) / mt for i in range(len(marks))] + [1.0]
        ys = [m[0] for m in marks] + [marks[-1][1]]

        def at(p: float) -> float:
            for i in range(len(xs) - 1):
                if p <= xs[i + 1]:
                    span = xs[i + 1] - xs[i] or 1.0
                    return ys[i] + (ys[i + 1] - ys[i]) * (p - xs[i]) / span
            return ys[-1]
    else:
        def at(p: float) -> float:
            return 0.15 + p * max(length - 0.5, 0.5)

    return [(round(at(pos[i]), 3), round(at(pos[i + 1]), 3), w) for i, w in enumerate(words)]


def estimate_seconds(text: str) -> float:
    return 0.8 + 0.36 * len(text.split())


# --------------------------------------------------------------------------- #
# Untertitel (ASS / libass)
# --------------------------------------------------------------------------- #

def _ass_color(hex_rgb: str, alpha: int = 0) -> str:
    rgb = hex_rgb.removeprefix("0x").removeprefix("#")
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _ts(sec: float) -> str:
    sec = max(sec, 0.0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def chunks(words: list[tuple[float, float, str]], max_words: int = 3, max_chars: int = 16) -> list[list[tuple[float, float, str]]]:
    out: list[list[tuple[float, float, str]]] = []
    cur: list[tuple[float, float, str]] = []
    for w in words:
        text_len = sum(len(x[2]) + 1 for x in cur) + len(w[2])
        if cur and (len(cur) >= max_words or text_len > max_chars):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.:!?–]$", w[2]):  # Satzzeichen beendet eine Gruppe
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def build_ass(demo: dict[str, Any], scenes: list[dict[str, Any]], family: str, total: float) -> str:
    accent = _ass_color(demo["accent"])
    white, black = "&H00FFFFFF", "&H00000000"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{family},84,{white},{white},{black},&H96000000,1,0,0,0,100,100,0,0,1,7,4,5,70,70,0,1
Style: Hook,{family},104,{white},{white},{black},&H96000000,1,0,0,0,100,100,0,0,1,8,5,8,80,80,360,1
Style: Chip,{family},40,{_ass_color('111111')},{white},{accent},{accent},1,0,0,0,100,100,3,0,3,14,0,7,64,64,70,1
Style: Count,{family},60,{accent},{white},{black},&H96000000,1,0,0,0,100,100,2,0,1,5,2,8,70,70,1010,1
Style: Cta,{family},66,{_ass_color('111111')},{white},{accent},{accent},1,0,0,0,100,100,0,0,3,30,0,5,90,90,0,1
Style: Foot,{family},30,&H40FFFFFF,{white},{black},&H96000000,1,0,0,0,100,100,1,0,1,2,0,2,60,60,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Wenig Text: kein Etikett, kein Zähler; der Hinweis nur in der letzten Szene
    cta_start = next((sc["start"] for sc in scenes if sc["kind"] == "cta"), max(total - 3, 0))
    ev = [f"Dialogue: 1,{_ts(cta_start)},{_ts(total)},Foot,,0,0,0,,{{\\fad(200,0)}}{_esc(demo['footer'])}"]
    for sc in scenes:
        start, end = sc["start"], sc["start"] + sc["dur"]
        if sc["kind"] == "hook":
            hl = {h.lower() for h in demo.get("highlight", [])}
            parts = []
            for k, word in enumerate(demo["hook"].split()):
                t0 = 80 + k * 90  # Wörter erscheinen nacheinander mit kleinem Pop
                color = accent if word.lower() in hl else white
                parts.append(f"{{\\alpha&HFF&\\1c{color}\\fscx70\\fscy70\\t({t0},{t0 + 1},\\alpha&H00&)"
                             f"\\t({t0},{t0 + 220},\\fscx100\\fscy100)}}{_esc(word)}")
            ev.append(f"Dialogue: 3,{_ts(start)},{_ts(end - 0.05)},Hook,,0,0,0,,{{\\fad(0,180)}}" + " ".join(parts))
            continue
        if sc["kind"] == "cta":
            ms = int(sc["dur"] * 1000)
            pulse = "".join(f"\\t({t},{t + 400},\\fscx104\\fscy104)\\t({t + 400},{t + 800},\\fscx100\\fscy100)"
                            for t in range(300, max(ms - 800, 301), 800))
            ev.append(f"Dialogue: 3,{_ts(start)},{_ts(end)},Cta,,0,0,0,,"
                      f"{{\\pos({W // 2},{int(H * 0.62)})\\fscx60\\fscy60\\t(0,260,\\fscx100\\fscy100){pulse}}}"
                      f"{_esc(demo['cta'])}")
            continue  # der Knopf zeigt den Text schon – keine doppelten Untertitel
        # Untertitel Wort für Wort im Takt der Stimme
        y = int(H * 0.66)
        groups = chunks(sc["words"], max_words=2, max_chars=14)
        for g, group in enumerate(groups):
            g_start = start + group[0][0]
            g_end = start + (groups[g + 1][0][0] if g + 1 < len(groups) else sc["dur"] - 0.08)
            text = []
            for w0, w1, word in group:
                a = int((start + w0 - g_start) * 1000)
                b = max(int((start + w1 - g_start) * 1000), a + 2)
                text.append(f"{{\\1c{white}\\t({a},{a + 1},\\1c{accent}\\fscx108\\fscy108)"
                            f"\\t({b},{b + 1},\\1c{white}\\fscx100\\fscy100)}}{_esc(word)}")
            ev.append(f"Dialogue: 4,{_ts(g_start)},{_ts(max(g_end, g_start + 0.2))},Cap,,0,0,0,,"
                      f"{{\\pos({W // 2},{y})\\fscx88\\fscy88\\t(0,90,\\fscx100\\fscy100)}}" + " ".join(text))
    return head + "\n".join(ev) + "\n"


# --------------------------------------------------------------------------- #
# Schnitt
# --------------------------------------------------------------------------- #

def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def scene_video(src: Path | None, dur: float, demo: dict[str, Any], target: Path, ffmpeg: str, work: Path,
                src_len: float = 0.0) -> None:
    """Eine Szene: Clip auf 9:16, Zoom-Punch am Schnitt, langsamer Push-in, Farbkorrektur."""
    frames = int(round(dur * FPS))
    # Zoom per Skalierung je Bild (weich, ohne das Ruckeln von zoompan): kurzer Punch am Schnitt
    # (1,10 → 1,0 in 0,25 s), danach langsamer Push-in.
    z = "(if(lt(t,0.25),1.10-0.4*t,1.0+0.012*(t-0.25)))"
    look = (f"fps={FPS},crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
            f"scale={W}:{H}:flags=lanczos,"
            f"scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame:flags=lanczos,"
            f"crop={W}:{H},"
            "eq=contrast=1.04:saturation=1.10,unsharp=5:5:0.5:5:5:0.0,"
            "vignette=angle=PI/6,format=yuv420p")
    if src is not None:
        # Etwas nach dem Anfang einsteigen (Pixabay-Clips beginnen oft mit Einblendung)
        offset = min(0.8, max(src_len - dur, 0.0) / 2) if src_len else 0.0
        inp = ["-stream_loop", "-1", "-ss", f"{offset:.2f}", "-i", str(src)]
    else:
        c0, c1 = demo["colors"]
        inp = ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0={c0}:c1={c1}:x0=0:y0=0:x1={W}:y1={H}:"
                                    f"speed=0.01:d={dur + 1}:r={FPS}"]
    _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *inp, "-vf", look, "-frames:v", str(frames),
          "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-r", str(FPS), str(target)], work)


def _music_expr(total: float) -> str:
    """Ruhiger Klangteppich: 4 Akkorde (je 4 s, weich überblendet) + leiser Puls."""
    roots = [110.0, 87.31, 130.81, 98.0]  # A2 F2 C3 G2
    voices = []
    for k, f in enumerate(roots):
        win = f"pow(sin(PI*min(max((mod(t,16)-{4 * k}+1)/6,0),1)),2)"
        if k == 0:  # Fenster von Akkord 1 auch am Ende des 16-s-Kreises
            win = f"({win}+pow(sin(PI*min(max((mod(t,16)-15)/6,0),1)),2))"
        tone = (f"(0.30*sin(2*PI*{f}*t)+0.18*sin(2*PI*{f * 1.5:.2f}*t)+0.14*sin(2*PI*{f * 2:.2f}*t)"
                f"+0.08*sin(2*PI*{f * 3:.2f}*t))")
        voices.append(f"{win}*{tone}")
    pulse = "0.35*sin(2*PI*52*mod(t,0.625))*exp(-mod(t,0.625)*14)"
    fade = f"min(t/1.5,1)*min(max(({total}-t)/1.5,0),1)"
    return f"0.22*({'+'.join(voices)}+{pulse})*{fade}"


def render(demo: dict[str, Any], out: Path, ffmpeg: str, font: tuple[str, str], footage: Footage | None,
           voice: bool = True, progress: Callable[[str], None] | None = None) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{demo['name']}.mp4"
    font_file, family = font
    say = progress or (lambda msg: log.info("%s", msg))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(font_file, work / Path(font_file).name)
        texts = [("hook", demo["hook"])] + [("line", t) for t in demo["lines"]] + [("cta", demo["cta"])]
        queries = demo.get("clips") or []

        # 1) Stimme je Szene → Länge der Szene
        scenes: list[dict[str, Any]] = []
        start = 0.0
        speaker = VOICES.get(demo.get("lang", "en"), VOICES["en"])
        for i, (kind, text) in enumerate(texts):
            audio = work / f"voice_{i}.mp3"
            marks = speak(text, speaker, audio) if voice else None
            length = duration(audio, ffmpeg) if marks is not None else estimate_seconds(text)
            dur = round(max(length + 0.45, 2.6), 2)
            scenes.append({"kind": kind, "text": text, "index": i, "start": round(start, 3), "dur": dur,
                           "audio": audio if marks is not None else None,
                           "words": word_times(text, marks, length)})
            start += dur
            voice = voice and marks is not None  # ohne Netz nicht jede Szene erneut warten
        total = round(start, 2)

        # 2) Bildmaterial je Szene
        used: set[int] = set()
        files = []
        for i, sc in enumerate(scenes):
            query = queries[i] if i < len(queries) else (queries[-1] if queries else "")
            clip = footage.pick(query, sc["dur"], used) if (footage and query) else None
            say(f"{demo['name']}: Szene {i + 1}/{len(scenes)} – " + (clip.name if clip else "Farbverlauf"))
            part = work / f"scene_{i}.mp4"
            scene_video(clip, sc["dur"], demo, part, ffmpeg, work, duration(clip, ffmpeg) if clip else 0.0)
            files.append(part)
        (work / "list.txt").write_text("".join(f"file '{f.name}'\n" for f in files), encoding="utf-8")

        # 3) Schatten oben/unten für lesbare Schrift, Untertitel
        _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}",
              "-vf", "format=rgba,geq=r=0:g=0:b=0:a='if(lt(Y,300),90*(1-Y/300),"
                     "if(gt(Y,1050),min(140,140*(Y-1050)/600),0))'",
              "-frames:v", "1", "shade.png"], work)
        (work / "subs.ass").write_text(build_ass(demo, scenes, family, total), encoding="utf-8")

        # 4) Ton: Stimme + Musik + Whoosh an jedem Schnitt
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-f", "concat", "-safe", "0", "-i", "list.txt",
               "-loop", "1", "-i", "shade.png",
               "-f", "lavfi", "-i", f"color=c={demo['accent']}:s={W}x14:r={FPS}:d={total}",
               "-f", "lavfi", "-i", f"aevalsrc='{_music_expr(total)}':s=48000:d={total}",
               "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:a=0.6:r=48000"]
        voice_inputs = [sc for sc in scenes if sc["audio"]]
        for sc in voice_inputs:
            cmd += ["-i", sc["audio"].name]
        cuts = [sc["start"] for sc in scenes[1:]]
        n_w = max(len(cuts), 1)
        fg = [
            "[0:v][1:v]overlay=0:0:shortest=1[a]",
            f"[a][2:v]overlay=x='-W+W*t/{total}':y=0:shortest=1[b]",
            "[b]subtitles=subs.ass:fontsdir=.,format=yuv420p[v]",
            f"[3:a]lowpass=f=1800,volume={'0.55' if voice_inputs else '1.0'}[m]",
            "[4:a]highpass=f=500,lowpass=f=5000,afade=t=in:d=0.18,afade=t=out:st=0.18:d=0.32,"
            f"volume=0.35,asplit={n_w}" + "".join(f"[w{k}]" for k in range(n_w)),
        ]
        mix = ["[m]"]
        for k, cut in enumerate(cuts):
            ms = max(int((cut - 0.2) * 1000), 0)
            fg.append(f"[w{k}]adelay={ms}|{ms}[wd{k}]")
            mix.append(f"[wd{k}]")
        if not cuts:
            fg.append("[w0]anullsink")
        for k, sc in enumerate(voice_inputs):
            ms = int((sc["start"] + 0.12) * 1000)
            fg.append(f"[{5 + k}:a]aresample=48000,adelay={ms}|{ms},volume=1.6[vo{k}]")
            mix.append(f"[vo{k}]")
        fg.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,"
                  f"atrim=0:{total},alimiter=limit=0.9[aout]")
        cmd += ["-filter_complex", ";".join(fg), "-map", "[v]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
                "-t", str(total), str(target.resolve())]
        say(f"{demo['name']}: Endschnitt ({total:.1f} s) …")
        _run(cmd, work)
    return target


def render_all(out: Path, only: list[str] | None = None, cfg: dict[str, Any] | None = None,
               voice: bool | None = None) -> list[Path]:
    ffmpeg, font = find_ffmpeg(), find_font()
    if not ffmpeg:
        raise RuntimeError("ffmpeg nicht gefunden – installieren mit: winget install Gyan.FFmpeg")
    if not font:
        raise RuntimeError("Keine passende Schrift gefunden.")
    mcfg = (cfg or {}).get("muster") or {}
    key = pixabay_key(cfg)
    if not key:
        log.warning("Kein Pixabay-Schlüssel – Szenen ohne echtes Bildmaterial (Farbverlauf).")
    footage = Footage(out / "clips", key)
    if voice is None:
        voice = bool(mcfg.get("stimme", True))
    for lang, name in (mcfg.get("stimmen") or {}).items():
        VOICES[lang] = name
    done = []
    for demo in DEMOS:
        if only and demo["name"] not in only:
            continue
        log.info("Erstelle Muster-Video %s …", demo["name"])
        try:
            done.append(render(demo, out, ffmpeg, font, footage, voice=voice))
        except subprocess.CalledProcessError as exc:
            log.error("ffmpeg-Fehler bei %s: %s", demo["name"], (exc.stderr or "").strip()[-600:])
    return done
