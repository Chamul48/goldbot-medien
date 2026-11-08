import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "seite_lesen", Path(__file__).resolve().parent.parent / "windows" / "seite_lesen.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)

PROBE = """<html><head><title>1 oz Wiener Philharmoniker Gold &amp; mehr</title>
<meta property="og:description" content="Goldmünze 1 Unze kaufen">
<script type="application/ld+json">{"@type":"Product","name":"Philharmoniker 1 oz",
 "offers":{"@type":"Offer","price":"3712.50","priceCurrency":"EUR"}}</script>
<script>var x = "€ 9.999,99 nicht zählen";</script>
<style>.p{}</style></head>
<body><p>Verkaufspreis: 3.712,50 €</p><p>Ankauf € 3.590,10</p><p>Basic $25 Standard $60</p>
<p>Verkaufspreis: 3.712,50 €</p></body></html>"""


def test_auswerten_liest_titel_beschreibung_angebote_und_betraege():
    r = sl.auswerten("https://beispiel.at/p", PROBE)
    assert r["titel"] == "1 oz Wiener Philharmoniker Gold & mehr"
    assert r["beschreibung"] == "Goldmünze 1 Unze kaufen"
    assert r["angebote"] == [{"price": "3712.50", "priceCurrency": "EUR", "name": "Philharmoniker 1 oz"}]
    text = " | ".join(r["betraege"])
    assert "Verkaufspreis: 3.712,50 €" in text and "Ankauf € 3.590,10" in text and "$25" in text
    assert "9.999,99" not in text  # Skripte werden nicht mitgezählt
    assert sum(b.endswith("Verkaufspreis: 3.712,50 €") for b in r["betraege"]) == 1  # doppelte Stellen nur einmal
    assert r["captcha"] is False


def test_captcha_wird_erkannt():
    assert sl.auswerten("u", "<div id='px-captcha'></div>")["captcha"] is True


def test_fehler_einer_seite_stoppt_nicht_die_anderen(monkeypatch, capsys):
    def holen(url, timeout=25.0):
        if "kaputt" in url:
            raise OSError("weg")
        return PROBE
    monkeypatch.setattr(sl, "holen", holen)
    monkeypatch.setattr(sl, "PAUSE_JE_DOMAIN", 0.0)
    assert sl.main(["https://a.at/kaputt", "https://b.at/ok"]) == 0
    out = capsys.readouterr().out
    assert '"fehler": "OSError: weg"' in out and "Philharmoniker 1 oz" in out


def test_ausgabe_in_datei_als_utf8(monkeypatch, tmp_path):
    monkeypatch.setattr(sl, "holen", lambda url, timeout=25.0: PROBE)
    ziel = tmp_path / "e.json"
    assert sl.main(["-o", str(ziel), "https://b.at/ok"]) == 0
    assert "3.712,50 €" in ziel.read_text(encoding="utf-8")


def test_profilseite_liefert_bild_und_volle_beschreibung():
    lang = "Hi, I'm Chucha. " + "x" * 300
    seite = ('<script>{"description":"kurz","x":{"description":"' + lang + '",'
             '"profileImageUrl":"https:\\/\\/img.example\\/p.png"}}</script>')
    r = sl.auswerten("https://www.fiverr.com/u", seite)
    assert r["profilbild"] == "https://img.example/p.png"
    assert r["beschreibung_lang"] == lang
    assert sl.auswerten("u", PROBE)["profilbild"] is None
