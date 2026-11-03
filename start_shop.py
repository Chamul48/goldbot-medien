"""Gefuehrter Start: Zugang eintragen (falls noetig), Verbindung testen, Shop-Kontrolle starten.

Unter Windows per Doppelklick auf "Shop starten.bat". Aendert im Shop nichts:
die Kontrolle liest nur, sichert die Originalwerte und schreibt einen Bericht.
"""
import os
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
os.chdir(HIER)
sys.path.insert(0, str(HIER))
PY = sys.executable


def env_werte():
    werte = {}
    env = HIER / ".env"
    if env.exists():
        for z in env.read_text(encoding="utf-8").splitlines():
            z = z.strip()
            if z and not z.startswith("#") and "=" in z:
                k, v = z.split("=", 1)
                werte[k.strip()] = v.strip()
    return werte


def hat(k):
    v = env_werte().get(k, "")
    return bool(v) and not v.endswith("_")


def eintragen(key, anleitung):
    while True:
        print()
        print(anleitung)
        input("  -> Wenn kopiert (Strg+C), hier ENTER druecken ... ")
        r = subprocess.run([PY, "eintragen.py", key])
        if r.returncode == 0:
            return
        print("  Das hat nicht geklappt, bitte nochmal kopieren.")


def main():
    print("=" * 60)
    print("  Goldbot Shop-Start")
    print("=" * 60)
    if not hat("SHOPIFY_STORE"):
        eintragen("SHOPIFY_STORE",
                  "1) Shop-Adresse: Oeffne deinen Shopify-Admin und kopiere die ganze\n"
                  "   Adresszeile oben im Browser (oder nur 'deinshop.myshopify.com').")
    if not (hat("SHOPIFY_ACCESS_TOKEN") or (hat("SHOPIFY_CLIENT_ID") and hat("SHOPIFY_CLIENT_SECRET"))):
        print()
        print("Jetzt der Zugang aus dem Shopify Dev Dashboard (https://dev.shopify.com/dashboard):")
        print("App 'Goldbot Agent' -> Settings.")
        if not hat("SHOPIFY_CLIENT_ID"):
            eintragen("SHOPIFY_CLIENT_ID", "2) Kopiere die 'Client ID' (Kopier-Symbol daneben).")
        if not hat("SHOPIFY_CLIENT_SECRET"):
            eintragen("SHOPIFY_CLIENT_SECRET", "3) Kopiere das 'Secret' (erst anzeigen lassen, dann kopieren).")

    print()
    print("Teste die Verbindung ...")
    from shopify_agent.shopify import ShopifyClient, ShopifyError
    try:
        shop = ShopifyClient()
        info = shop.graphql("{ shop { name myshopifyDomain } }")["shop"]
    except ShopifyError as exc:
        print("Verbindung fehlgeschlagen:", str(exc)[:300])
        print("Tipp: Ist die App im Shop installiert? Stimmen Client ID und Secret?")
        print("Zum Neu-Eintragen einfach diese Datei nochmal starten,")
        print("vorher in der .env die falsche Zeile loeschen.")
        return 1
    print("Verbunden mit:", info["name"], "(" + info["myshopifyDomain"] + ")")

    print()
    print("Starte die Shop-Kontrolle (nur lesen, aendert nichts) ...")
    from shopify_agent.audit import run_audit
    report_path, backup_path, found = run_audit(shop, HIER / "autopilot")
    print("Fertig:", len(found), "Punkte gefunden.")
    print("Bericht:  ", report_path)
    print("Sicherung:", backup_path)
    try:
        os.startfile(str(report_path))  # oeffnet den Bericht
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        code = 1
    print()
    input("ENTER zum Schliessen ...")
    sys.exit(code)
