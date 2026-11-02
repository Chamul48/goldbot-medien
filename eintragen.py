"""Uebernimmt die Zwischenablage in die .env, ohne den Wert anzuzeigen.

Aufruf: python eintragen.py SHOPIFY_CLIENT_ID|SHOPIFY_CLIENT_SECRET|SHOPIFY_ACCESS_TOKEN|SHOPIFY_STORE
"""
import re
import sys
import tkinter
from pathlib import Path

ERLAUBT = {"SHOPIFY_STORE", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET", "SHOPIFY_ACCESS_TOKEN"}
key = sys.argv[1] if len(sys.argv) > 1 else ""
if key not in ERLAUBT:
    sys.exit("Unbekannter Name: " + key)

root = tkinter.Tk()
root.withdraw()
try:
    wert = root.clipboard_get().strip()
except tkinter.TclError:
    sys.exit("Zwischenablage ist leer.")
root.destroy()

if not wert or "\n" in wert or " " in wert:
    sys.exit("In der Zwischenablage steht kein einzelner Wert (leer oder mehrere Woerter).")
if key == "SHOPIFY_STORE":
    m = re.search(r"([a-z0-9][a-z0-9-]*)\.myshopify\.com", wert.lower())
    # admin.shopify.com/store/<name>/... is what the browser shows in the admin
    m2 = re.search(r"admin\.shopify\.com/store/([a-z0-9][a-z0-9-]*)", wert.lower())
    if m:
        wert = m.group(1) + ".myshopify.com"
    elif m2:
        wert = m2.group(1) + ".myshopify.com"
    elif re.fullmatch(r"[a-z0-9][a-z0-9-]*", wert.lower()):
        wert = wert.lower() + ".myshopify.com"
    else:
        sys.exit("Das sieht nicht nach einer ...myshopify.com-Adresse aus.")

env = Path(__file__).with_name(".env")
zeilen = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
muster = re.compile(r"^\s*#?\s*" + key + r"\s*=")
neu, gesetzt = [], False
for z in zeilen:
    if muster.match(z):
        if not gesetzt:
            neu.append(key + "=" + wert)
            gesetzt = True
        continue
    neu.append(z)
if not gesetzt:
    neu.append(key + "=" + wert)
env.write_text("\n".join(neu) + "\n", encoding="utf-8")

try:  # Zwischenablage leeren, damit das Geheimnis nicht liegen bleibt
    r = tkinter.Tk(); r.withdraw(); r.clipboard_clear(); r.update(); r.destroy()
except Exception:
    pass

if key == "SHOPIFY_STORE":
    print("Gespeichert: SHOPIFY_STORE=" + wert)
else:
    print("Gespeichert: " + key + " (" + str(len(wert)) + " Zeichen)")
