"""Muster-Videos für dein Portfolio (9:16, mit Untertiteln im Kurzvideo-Stil).

Erstellt mit ffmpeg kurze Vorlagen zu Gold, Finanzen und Krypto – auf Deutsch
und Englisch. Sie zeigen deinen Schnitt-Stil (Hook, animierte Captions,
Fortschrittsbalken). Es sind DEMOS: Ersetze den Hintergrund nach und nach durch
eigenes Material, dann werden echte Arbeitsproben daraus.

Inhalte sind allgemeines Wissen ohne Kursdaten, Prognosen oder Anlagetipps.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

W, H, FPS = 1080, 1920, 30
HOOK, LINE, CTA = 3.0, 3.0, 2.5  # Sekunden

DEMOS: list[dict[str, Any]] = [
    {
        "name": "gold_de", "colors": ("0x14100a", "0x5c4512"), "accent": "0xd4a017",
        "hook": "3 Fakten über Gold, die kaum jemand kennt",
        "lines": ["Gold rostet nicht – es bleibt jahrtausendelang glänzend.",
                  "Alles je geförderte Gold passt in einen Würfel von rund 22 Metern.",
                  "Blattgold ist sogar essbar: Lebensmittelzusatz E 175."],
        "cta": "Folge für mehr Edelmetall-Wissen",
        "footer": "DEMO · Beispielvideo · keine Anlageberatung",
    },
    {
        "name": "gold_en", "colors": ("0x14100a", "0x5c4512"), "accent": "0xd4a017",
        "hook": "3 gold facts most people don't know",
        "lines": ["Gold doesn't rust – it stays shiny for thousands of years.",
                  "All the gold ever mined fits in a cube of about 22 metres.",
                  "Gold leaf is even edible: food additive E 175."],
        "cta": "Follow for more precious metal facts",
        "footer": "DEMO · sample video · not financial advice",
    },
    {
        "name": "finanzen_de", "colors": ("0x07131f", "0x0f4c5c"), "accent": "0x1dbf73",
        "hook": "Die 50/30/20-Regel in 15 Sekunden",
        "lines": ["50 % deines Nettoeinkommens für Fixkosten: Miete, Essen, Versicherung.",
                  "30 % für Wünsche: Hobbys, Urlaub, Ausgehen.",
                  "20 % zum Sparen und für Rücklagen."],
        "cta": "Speichern und später nachrechnen",
        "footer": "DEMO · Beispielvideo · keine Finanzberatung",
    },
    {
        "name": "finance_en", "colors": ("0x07131f", "0x0f4c5c"), "accent": "0x1dbf73",
        "hook": "The 50/30/20 rule in 15 seconds",
        "lines": ["50% of your take-home pay for needs: rent, food, insurance.",
                  "30% for wants: hobbies, travel, going out.",
                  "20% for savings and an emergency fund."],
        "cta": "Save this for your next budget",
        "footer": "DEMO · sample video · not financial advice",
    },
    {
        "name": "krypto_de", "colors": ("0x120a1f", "0x3b1e6b"), "accent": "0xf7931a",
        "hook": "Was ist eine Blockchain? Einfach erklärt",
        "lines": ["Eine Blockchain ist eine Kette aus Datenblöcken.",
                  "Jeder Block enthält einen Fingerabdruck des vorherigen.",
                  "Wer einen Block ändert, müsste alle folgenden mit ändern."],
        "cta": "Folge für mehr Krypto-Grundlagen",
        "footer": "DEMO · Beispielvideo · keine Anlageberatung",
    },
    {
        "name": "crypto_en", "colors": ("0x120a1f", "0x3b1e6b"), "accent": "0xf7931a",
        "hook": "What is a blockchain? Explained simply",
        "lines": ["A blockchain is a chain of data blocks.",
                  "Every block holds a fingerprint of the one before it.",
                  "Changing one block means changing every block after it."],
        "cta": "Follow for more crypto basics",
        "footer": "DEMO · sample video · not financial advice",
    },
]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    # WinGet installiert ffmpeg oft außerhalb des PATH der aktuellen Sitzung
    base = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for exe in base.glob("*FFmpeg*/**/bin/ffmpeg.exe"):
        return str(exe)
    return None


def find_font() -> str | None:
    return next((f for f in FONT_CANDIDATES if Path(f).exists()), None)


def _fade(start: float, end: float, ramp: float = 0.25) -> str:
    """Alpha-Ausdruck für ffmpeg drawtext: ein- und ausblenden."""
    return (f"if(lt(t,{start}),0,if(lt(t,{start + ramp}),(t-{start})/{ramp},"
            f"if(lt(t,{end - ramp}),1,if(lt(t,{end}),({end}-t)/{ramp},0))))")


def _lines(work: Path, key: str, text: str, width: int, size: int, center_y: str,
           alpha: str, style: str) -> list[str]:
    """Eine drawtext-Anweisung pro Zeile – jede Zeile einzeln zentriert."""
    rows = textwrap.wrap(text, width, break_on_hyphens=False)
    step = int(size * 1.45)
    out = []
    for k, row in enumerate(rows):
        name = f"{key}_{k}.txt"
        (work / name).write_text(row, encoding="utf-8")
        offset = int((k - (len(rows) - 1) / 2) * step)
        out.append(
            # expansion=none: "%" (z. B. "50 %") ist sonst ein Platzhalter-Zeichen
            f"drawtext=fontfile=font.ttf:textfile={name}:expansion=none:fontsize={size}:x=(w-text_w)/2:"
            f"y='{center_y}+({offset})-text_h/2':alpha='{alpha}':{style}"
        )
    return out


def filtergraph(demo: dict[str, Any], work: Path) -> tuple[str, float]:
    total = HOOK + LINE * len(demo["lines"]) + CTA
    accent = demo["accent"]
    shadow = "fontcolor=white:shadowcolor=black@0.6:shadowx=4:shadowy=4"
    # Der Fortschrittsbalken kommt per overlay in render() dazu – drawbox kennt keine Zeit
    # ("t" ist dort die Rahmendicke), der Balken stünde sonst die ganze Zeit voll da.
    parts: list[str] = []
    # Hook: groß, gleitet leicht nach oben
    parts += _lines(work, "hook", demo["hook"], 16, 92, f"(h*0.40-30*min(t/{HOOK},1))", _fade(0, HOOK), shadow)
    for i, line in enumerate(demo["lines"]):
        start = HOOK + i * LINE
        alpha = _fade(start, start + LINE)
        # Caption-Stil: jede Zeile mit eigener Box, dunkle Schrift für guten Kontrast
        parts += _lines(work, f"l{i}", line, 20, 68, "h/2", alpha,
                        f"fontcolor=0x111111:box=1:boxcolor={accent}@0.95:boxborderw=22")
        parts.append(
            f"drawtext=fontfile=font.ttf:text='{i + 1}/{len(demo['lines'])}':fontsize=54:"
            f"x=(w-text_w)/2:y=h*0.27:alpha='{alpha}':{shadow}"
        )
    cta_start = HOOK + LINE * len(demo["lines"])
    parts += _lines(work, "cta", demo["cta"], 18, 80, "h/2", _fade(cta_start, total + 0.3), shadow)
    parts += _lines(work, "foot", demo["footer"], 60, 34, "h-130", "1", "fontcolor=white@0.75")
    return ",".join(parts), total


def render(demo: dict[str, Any], out: Path, ffmpeg: str, font: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{demo['name']}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(font, work / "font.ttf")
        graph, total = filtergraph(demo, work)
        c0, c1 = demo["colors"]
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i",
            f"gradients=s={W}x{H}:c0={c0}:c1={c1}:x0=0:y0=0:x1={W}:y1={H}:speed=0.008:d={total}:r={FPS}",
            "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={total}",
            "-f", "lavfi", "-i", f"color=c={demo['accent']}:s={W}x14:r={FPS}:d={total}",
            "-filter_complex",
            # Balken schiebt sich von links herein: x läuft von -W bis 0
            f"[0:v][2:v]overlay=x='-W+W*t/{total}':y=0:shortest=1,{graph}[v]",
            "-map", "[v]", "-map", "1:a", "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
            str(target.resolve()),
        ]
        subprocess.run(cmd, cwd=work, check=True, capture_output=True, text=True)
    return target


def render_all(out: Path, only: list[str] | None = None) -> list[Path]:
    ffmpeg, font = find_ffmpeg(), find_font()
    if not ffmpeg:
        raise RuntimeError("ffmpeg nicht gefunden – installieren mit: winget install Gyan.FFmpeg")
    if not font:
        raise RuntimeError("Keine passende Schrift gefunden.")
    done = []
    for demo in DEMOS:
        if only and demo["name"] not in only:
            continue
        log.info("Erstelle Muster-Video %s …", demo["name"])
        try:
            done.append(render(demo, out, ffmpeg, font))
        except subprocess.CalledProcessError as exc:
            log.error("ffmpeg-Fehler bei %s: %s", demo["name"], (exc.stderr or "").strip()[-400:])
    return done
