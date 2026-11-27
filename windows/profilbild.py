"""Macht aus einem normalen Foto von dir ein hochwertiges Fiverr-Profilbild.

Aufruf:  python profilbild.py <foto.jpg>   (oder Foto auf „Profilbild machen.bat“ ziehen)

Ergebnis neben dem Foto, je 1000 x 1000 px (Fiverr zeigt es rund an):
  <name>_fiverr_gold.png    dunkler Hintergrund mit warmem Gold-Licht (passt zu Finanz/Gold)
  <name>_fiverr_hell.png    heller, neutraler Studio-Hintergrund
  <name>_fiverr_vorschau.png  beide nebeneinander, so rund wie auf Fiverr

Es wird nur dein echtes Foto verbessert (Hintergrund, Ausschnitt, Licht) – kein KI-Gesicht.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from rembg import new_session, remove

GROESSE = 1000


def gesicht(rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    """Größtes Gesicht (x, y, b, h) oder None."""
    grau = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    kaskade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    min_seite = max(40, min(grau.shape) // 12)
    treffer = kaskade.detectMultiScale(grau, scaleFactor=1.1, minNeighbors=6, minSize=(min_seite, min_seite))
    if len(treffer) == 0:
        return None
    x, y, b, h = max(treffer, key=lambda t: t[2] * t[3])
    return int(x), int(y), int(b), int(h)


def ausschnitt(maske: np.ndarray, g: tuple[int, int, int, int] | None, breite: int, hoehe: int) -> tuple[int, int, int]:
    """Quadrat (links, oben, seite): Gesicht mittig, etwas über der Mitte, Schultern sichtbar."""
    if g:
        x, y, b, h = g
        seite = int(h * 2.9)
        mx, my = x + b / 2, y + h * 0.55
        links, oben = int(mx - seite / 2), int(my - seite * 0.42)
        seite = min(seite, breite, hoehe)
        links = min(max(links, 0), breite - seite)
        oben = min(max(oben, 0), hoehe - seite)
        return links, oben, seite
    else:  # kein Gesicht erkannt: oberen Teil der freigestellten Person nehmen
        ys, xs = np.nonzero(maske > 128)
        if len(ys) == 0:
            seite = min(breite, hoehe)
            return (breite - seite) // 2, 0, seite
        top = ys.min()
        koerper_b = xs.max() - xs.min()
        seite = int(min(max(koerper_b * 1.1, (ys.max() - top) * 0.6), max(breite, hoehe)))
        oberteil = xs[ys < top + seite // 3]
        mx = oberteil.mean() if len(oberteil) else xs.mean()
        links, oben = int(mx - seite / 2), int(top - seite * 0.08)
    # im Foto bleiben, sonst entstehen harte Kanten, wo das Foto endet
    seite = min(seite, breite, hoehe)
    links = min(max(links, 0), breite - seite)
    oben = min(max(oben, 0), hoehe - seite)
    return links, oben, seite


def hintergrund(art: str) -> Image.Image:
    yy, xx = np.mgrid[0:GROESSE, 0:GROESSE].astype(np.float32) / GROESSE
    abstand = np.sqrt((xx - 0.5) ** 2 + (yy - 0.38) ** 2)
    if art == "gold":  # Nachtblau mit warmem Gold-Licht hinter dem Kopf
        basis = np.array([11, 15, 27]) + (np.array([22, 28, 46]) - np.array([11, 15, 27])) * (1 - yy[..., None])
        licht = np.exp(-(abstand / 0.30) ** 2)[..., None]
        bild = basis + np.array([212, 168, 86]) * 0.55 * licht
    else:  # Studio-Weiß → Hellgrau
        t = np.clip(abstand / 0.85, 0, 1) ** 1.2
        bild = np.array([246, 244, 240]) * (1 - t[..., None]) + np.array([196, 200, 206]) * t[..., None]
    rauschen = np.random.default_rng(7).normal(0, 1.2, bild.shape)  # gegen Farbstreifen
    return Image.fromarray(np.clip(bild + rauschen, 0, 255).astype(np.uint8), "RGB")


def person_verbessern(person: Image.Image) -> Image.Image:
    rgb, alpha = person.convert("RGB"), person.getchannel("A")
    rgb = ImageOps.autocontrast(rgb, cutoff=0.2, preserve_tone=True)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.03)
    rgb = ImageEnhance.Color(rgb).enhance(1.02)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=3))
    rgb.putalpha(alpha)
    return rgb


def zusammensetzen(person: Image.Image, art: str) -> Image.Image:
    bg = hintergrund(art)
    alpha = person.getchannel("A")
    # weicher Schatten hinter der Person für Tiefe
    schatten = Image.new("RGBA", person.size, (0, 0, 0, 0))
    staerke = 110 if art == "gold" else 60
    schatten.putalpha(alpha.point(lambda a: a * staerke // 255).filter(ImageFilter.GaussianBlur(18)))
    bg = bg.convert("RGBA")
    bg.alpha_composite(schatten, (0, 14))
    # Kante minimal weich, damit nichts ausgeschnitten wirkt
    person = person.copy()
    person.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.8)))
    bg.alpha_composite(person)
    return bg.convert("RGB")


def rund(bild: Image.Image, seite: int) -> Image.Image:
    klein = bild.resize((seite, seite), Image.LANCZOS)
    maske = Image.new("L", (seite * 4, seite * 4), 0)
    ImageDraw.Draw(maske).ellipse((0, 0, seite * 4 - 1, seite * 4 - 1), fill=255)
    out = Image.new("RGB", (seite, seite), (255, 255, 255))
    out.paste(klein, (0, 0), maske.resize((seite, seite), Image.LANCZOS))
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_file():
        print(__doc__)
        return 2
    quelle = Path(argv[0])
    foto = ImageOps.exif_transpose(Image.open(quelle)).convert("RGB")
    if max(foto.size) > 3000:  # schneller, Qualität reicht trotzdem für 1000 px
        foto.thumbnail((3000, 3000), Image.LANCZOS)
    print("Stelle dich frei … (beim ersten Mal wird einmalig ein Modell geladen)")
    frei = remove(foto, session=new_session("u2net_human_seg"), post_process_mask=True)
    maske = np.array(frei.getchannel("A"))
    g = gesicht(np.array(foto))
    if g is None:
        print("Hinweis: Kein Gesicht erkannt – Ausschnitt nach Umriss. Am besten ein Foto frontal, Gesicht gut sichtbar.")
    links, oben, seite = ausschnitt(maske, g, *foto.size)

    leer = Image.new("RGBA", (seite, seite), (0, 0, 0, 0))
    leer.paste(frei, (-links, -oben))  # Bereiche außerhalb des Fotos bleiben durchsichtig
    person = person_verbessern(leer.resize((GROESSE, GROESSE), Image.LANCZOS))

    ergebnisse = {}
    for art in ("gold", "hell"):
        ziel = quelle.with_name(f"{quelle.stem}_fiverr_{art}.png")
        bild = zusammensetzen(person, art)
        bild.save(ziel, optimize=True)
        ergebnisse[art] = bild
        print("Gespeichert:", ziel)

    vorschau = Image.new("RGB", (860, 440), (255, 255, 255))
    vorschau.paste(rund(ergebnisse["gold"], 400), (20, 20))
    vorschau.paste(rund(ergebnisse["hell"], 400), (440, 20))
    ziel = quelle.with_name(f"{quelle.stem}_fiverr_vorschau.png")
    vorschau.save(ziel)
    print("Vorschau:", ziel)
    if seite > max(foto.size) * 1.05 or (g and g[3] < 140):
        print("Hinweis: Das Foto ist recht klein oder weit weg – für ein scharfes Bild näher fotografieren.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
