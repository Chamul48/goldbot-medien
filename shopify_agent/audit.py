"""Read-only shop audit, backup and restore.

`snapshot()` reads everything the agent may later edit (texts, SEO, alt texts,
collections, pages) plus context (policies, theme, orders). `backup()` stores
the original values in autopilot/backup-<date>.json before anything changes,
`findings()` turns the snapshot into a prioritised German to-do list and
`restore()` writes the backed-up content back. Nothing here changes the shop
except `restore()`, and that asks for approval per item.
"""

from __future__ import annotations

import datetime
import html
import json
import re
from pathlib import Path
from typing import Any, Callable

from .shopify import ShopifyError

PAGE = 50

SHOP_Q = """
{ shop {
    name myshopifyDomain primaryDomain { url } currencyCode contactEmail
    plan { publicDisplayName }
    shopPolicies { type title body url }
} }
"""

PRODUCTS_Q = """
query($n: Int!, $after: String) {
  products(first: $n, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id title handle status vendor productType tags descriptionHtml onlineStoreUrl
      seo { title description }
      media(first: 30) { edges { node { id alt mediaContentType } } }
      variants(first: 100) { edges { node { id title sku price compareAtPrice inventoryQuantity } } }
    } }
  }
}
"""

COLLECTIONS_Q = """
query($n: Int!, $after: String) {
  collections(first: $n, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id title handle descriptionHtml sortOrder
      seo { title description }
      image { altText url }
      productsCount { count }
    } }
  }
}
"""

PAGES_Q = """
query($n: Int!, $after: String) {
  pages(first: $n, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges { node { id title handle isPublished body } }
  }
}
"""

THEMES_Q = "{ themes(first: 20) { edges { node { id name role } } } }"

ORDERS_Q = """
{ orders(first: 25, sortKey: CREATED_AT, reverse: true) {
    edges { node {
      id name createdAt displayFinancialStatus displayFulfillmentStatus
      totalPriceSet { shopMoney { amount currencyCode } }
    } }
} }
"""


def _edges(conn: dict[str, Any]) -> list[dict[str, Any]]:
    return [e["node"] for e in conn["edges"]]


def _paged(shop: Any, query: str, key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    after = None
    while True:
        conn = shop.graphql(query, {"n": PAGE, "after": after})[key]
        out += _edges(conn)
        info = conn.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return out
        after = info["endCursor"]


def read_products(shop: Any) -> list[dict[str, Any]]:
    items = _paged(shop, PRODUCTS_Q, "products")
    for p in items:
        p["media"] = _edges(p["media"])
        p["variants"] = _edges(p["variants"])
    return items


def text_of(html_str: str | None) -> str:
    """Visible text of an HTML snippet, whitespace collapsed."""
    s = re.sub(r"<[^>]+>", " ", html_str or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def snapshot(shop: Any) -> dict[str, Any]:
    """Read the whole shop. A failing section is recorded in `errors`, not raised."""
    snap: dict[str, Any] = {"date": datetime.date.today().isoformat(), "errors": {}}

    def section(name: str, fn: Callable[[], Any], default: Any) -> None:
        try:
            snap[name] = fn()
        except (ShopifyError, KeyError, TypeError) as exc:
            snap[name] = default
            snap["errors"][name] = str(exc)[:500]

    def themes() -> list[dict[str, Any]]:
        return _edges(shop.graphql(THEMES_Q)["themes"])

    def orders() -> list[dict[str, Any]]:
        return _edges(shop.graphql(ORDERS_Q)["orders"])

    section("shop", lambda: shop.graphql(SHOP_Q)["shop"], {})
    section("products", lambda: read_products(shop), [])
    section("collections", lambda: _paged(shop, COLLECTIONS_Q, "collections"), [])
    section("pages", lambda: _paged(shop, PAGES_Q, "pages"), [])
    section("themes", themes, [])
    section("orders", orders, [])
    return snap


# ---- backup / restore ----------------------------------------------------

def backup_data(snap: dict[str, Any]) -> dict[str, Any]:
    """Only the editable content fields, so a restore cannot touch prices or status."""
    return {
        "date": snap["date"],
        "shop": (snap.get("shop") or {}).get("myshopifyDomain"),
        "products": [
            {
                "id": p["id"], "title": p["title"], "handle": p.get("handle"),
                "descriptionHtml": p.get("descriptionHtml"), "productType": p.get("productType"),
                "tags": p.get("tags"), "seo": p.get("seo"),
                "media": [{"id": m["id"], "alt": m.get("alt")} for m in p.get("media", [])],
                # prices are kept for reference only; restore never writes them
                "prices": [{"id": v["id"], "price": v.get("price"), "compareAtPrice": v.get("compareAtPrice")}
                           for v in p.get("variants", [])],
            }
            for p in snap.get("products", [])
        ],
        "collections": [
            {"id": c["id"], "title": c["title"], "descriptionHtml": c.get("descriptionHtml"), "seo": c.get("seo")}
            for c in snap.get("collections", [])
        ],
        "pages": [
            {"id": pg["id"], "title": pg["title"], "handle": pg.get("handle"), "body": pg.get("body")}
            for pg in snap.get("pages", [])
        ],
    }


def write_backup(snap: dict[str, Any], out_dir: Path) -> Path:
    """Write autopilot/backup-<date>.json. Never overwrites: the first backup of a day stays."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"backup-{snap['date']}.json"
    n = 2
    while path.exists():
        path = out_dir / f"backup-{snap['date']}-{n}.json"
        n += 1
    path.write_text(json.dumps(backup_data(snap), ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _seo_input(seo: dict[str, Any] | None) -> dict[str, Any]:
    seo = seo or {}
    return {"title": seo.get("title") or "", "description": seo.get("description") or ""}


def restore(shop: Any, backup_file: Path, confirm: Callable[[str, str], bool]) -> list[str]:
    """Write backed-up texts, SEO, alt texts and collection texts back. Returns a log."""
    data = json.loads(backup_file.read_text(encoding="utf-8"))
    current = {p["id"]: p for p in read_products(shop)}
    log: list[str] = []

    for b in data.get("products", []):
        cur = current.get(b["id"])
        if cur is None:
            log.append(f"übersprungen (nicht mehr im Shop): {b['title']}")
            continue
        fields: dict[str, Any] = {}
        for key in ("title", "descriptionHtml", "productType", "tags"):
            if b.get(key) is not None and b.get(key) != cur.get(key):
                fields[key] = b[key]
        if _seo_input(b.get("seo")) != _seo_input(cur.get("seo")):
            fields["seo"] = _seo_input(b.get("seo"))
        if fields and confirm("content", f"Zurücksetzen {b['title']}: {', '.join(fields)}"):
            res = shop.graphql(
                """
                mutation($product: ProductUpdateInput!) {
                  productUpdate(product: $product) { product { id } userErrors { field message } }
                }
                """,
                {"product": {"id": b["id"], **fields}},
            )["productUpdate"]
            log.append(f"{b['title']}: {', '.join(fields)}" + (f" FEHLER {res['userErrors']}" if res["userErrors"] else ""))

        cur_alt = {m["id"]: m.get("alt") for m in cur.get("media", [])}
        alts = [{"id": m["id"], "alt": m.get("alt") or ""} for m in b.get("media", [])
                if m["id"] in cur_alt and (cur_alt[m["id"]] or "") != (m.get("alt") or "")]
        if alts and confirm("content", f"Alt-Texte zurücksetzen bei {b['title']} ({len(alts)})"):
            res = shop.graphql(
                """
                mutation($files: [FileUpdateInput!]!) {
                  fileUpdate(files: $files) { files { id } userErrors { field message } }
                }
                """,
                {"files": alts},
            )["fileUpdate"]
            log.append(f"{b['title']}: {len(alts)} Alt-Texte" + (f" FEHLER {res['userErrors']}" if res["userErrors"] else ""))

    cur_cols = {c["id"]: c for c in snapshot_collections(shop)}
    for b in data.get("collections", []):
        cur = cur_cols.get(b["id"])
        if cur is None:
            log.append(f"übersprungen (Kollektion fehlt): {b['title']}")
            continue
        fields = {}
        if b.get("descriptionHtml") is not None and b["descriptionHtml"] != cur.get("descriptionHtml"):
            fields["descriptionHtml"] = b["descriptionHtml"]
        if _seo_input(b.get("seo")) != _seo_input(cur.get("seo")):
            fields["seo"] = _seo_input(b.get("seo"))
        if fields and confirm("content", f"Kollektion zurücksetzen {b['title']}: {', '.join(fields)}"):
            res = shop.graphql(
                """
                mutation($collection: CollectionUpdateInput!) {
                  collectionUpdate(collection: $collection) { collection { id } userErrors { field message } }
                }
                """,
                {"collection": {"id": b["id"], **fields}},
            )["collectionUpdate"]
            log.append(f"Kollektion {b['title']}: {', '.join(fields)}" + (f" FEHLER {res['userErrors']}" if res["userErrors"] else ""))
    return log


def snapshot_collections(shop: Any) -> list[dict[str, Any]]:
    return _paged(shop, COLLECTIONS_Q, "collections")


# ---- findings ------------------------------------------------------------

# Who fixes it: "auto" = the agent may do it alone (texts, SEO, alt, collections),
# "du" = owner decides (prices, publishing, photos, legal, theme, deletions).
REQUIRED_POLICIES = {
    "LEGAL_NOTICE": "Impressum",
    "PRIVACY_POLICY": "Datenschutzerklärung",
    "TERMS_OF_SERVICE": "AGB",
    "REFUND_POLICY": "Widerrufsbelehrung / Rückgabe",
    "SHIPPING_POLICY": "Versandinformationen",
    "CONTACT_INFORMATION": "Kontaktinformationen",
}
TRUST_PAGES = {
    "Über uns": ("ueber", "uber", "about", "story", "marke"),
    "FAQ": ("faq", "fragen", "hilfe"),
    "Kontakt": ("kontakt", "contact"),
}


def _f(prio: int, who: str, area: str, text: str) -> dict[str, Any]:
    return {"prio": prio, "who": who, "area": area, "text": text}


def findings(snap: dict[str, Any], today: datetime.date | None = None) -> list[dict[str, Any]]:
    today = today or datetime.date.today()
    out: list[dict[str, Any]] = []

    for name, err in snap.get("errors", {}).items():
        out.append(_f(1, "du", "Technik", f"Abschnitt '{name}' konnte nicht gelesen werden: {err}"))

    products = snap.get("products", [])
    if not products and "products" not in snap.get("errors", {}):
        out.append(_f(1, "du", "Sortiment", "Der Shop hat keine Produkte."))
    for p in products:
        name = f"„{p['title']}“"
        active = p.get("status") == "ACTIVE"
        desc = text_of(p.get("descriptionHtml"))
        images = [m for m in p.get("media", []) if m.get("mediaContentType") == "IMAGE"]
        if p.get("status") == "DRAFT":
            out.append(_f(2, "du", "Sortiment", f"{name} ist ein Entwurf und für Kunden unsichtbar – veröffentlichen?"))
        if active and not p.get("media"):
            out.append(_f(1, "du", "Bilder", f"{name} ist aktiv, hat aber kein einziges Bild/Video."))
        elif active and len(images) < 3:
            out.append(_f(2, "du", "Bilder", f"{name} hat nur {len(images)} Bild(er); für High-End mind. 3–5 (Detail, Maßstab, Verpackung)."))
        if len(desc) < 50:
            out.append(_f(1, "auto", "Texte", f"{name} hat praktisch keine Beschreibung ({len(desc)} Zeichen)."))
        elif len(desc) < 300:
            out.append(_f(2, "auto", "Texte", f"{name}: Beschreibung sehr kurz ({len(desc)} Zeichen)."))
        no_alt = [m for m in p.get("media", []) if not (m.get("alt") or "").strip()]
        if no_alt:
            out.append(_f(2, "auto", "Barrierefreiheit/SEO", f"{name}: {len(no_alt)} Medien ohne Alt-Text."))
        seo = p.get("seo") or {}
        if not (seo.get("title") or "").strip():
            out.append(_f(2, "auto", "SEO", f"{name}: kein SEO-Titel."))
        elif len(seo["title"]) > 70:
            out.append(_f(3, "auto", "SEO", f"{name}: SEO-Titel zu lang ({len(seo['title'])} > 70)."))
        if not (seo.get("description") or "").strip():
            out.append(_f(2, "auto", "SEO", f"{name}: keine SEO-Beschreibung."))
        elif len(seo["description"]) > 160:
            out.append(_f(3, "auto", "SEO", f"{name}: SEO-Beschreibung zu lang ({len(seo['description'])} > 160)."))
        if not p.get("productType"):
            out.append(_f(3, "auto", "Struktur", f"{name}: keine Produktart gesetzt."))
        if not p.get("tags"):
            out.append(_f(3, "auto", "Struktur", f"{name}: keine Tags (erschwert Filter und Smart-Kollektionen)."))
        for v in p.get("variants", []):
            vname = name if v.get("title") in (None, "Default Title") else f"{name} / {v['title']}"
            try:
                price = float(v.get("price") or 0)
                cmp_ = float(v["compareAtPrice"]) if v.get("compareAtPrice") else None
            except ValueError:
                price, cmp_ = 0.0, None
            if active and price <= 0:
                out.append(_f(1, "du", "Preise", f"{vname} hat keinen Preis (0)."))
            if cmp_ is not None and cmp_ <= price:
                out.append(_f(3, "du", "Preise", f"{vname}: Streichpreis {cmp_} ist nicht höher als der Preis {price}."))
            if active and v.get("inventoryQuantity") is not None and v["inventoryQuantity"] <= 0:
                out.append(_f(2, "du", "Lager", f"{vname} ist aktiv, aber ohne Bestand ({v['inventoryQuantity']})."))
            if not v.get("sku"):
                out.append(_f(3, "du", "Lager", f"{vname}: keine Artikelnummer (SKU)."))

    collections = snap.get("collections", [])
    if not collections and "collections" not in snap.get("errors", {}):
        out.append(_f(1, "auto", "Navigation", "Keine Kollektionen – Kunden können nicht nach Themen stöbern."))
    for c in collections:
        name = f"Kollektion „{c['title']}“"
        count = (c.get("productsCount") or {}).get("count")
        if count == 0:
            out.append(_f(2, "du", "Navigation", f"{name} ist leer – füllen oder ausblenden?"))
        if len(text_of(c.get("descriptionHtml"))) < 50:
            out.append(_f(2, "auto", "Texte", f"{name} hat keine (richtige) Beschreibung."))
        if not c.get("image"):
            out.append(_f(3, "du", "Bilder", f"{name} hat kein Titelbild."))
        elif not (c["image"].get("altText") or "").strip():
            out.append(_f(3, "auto", "Barrierefreiheit/SEO", f"{name}: Titelbild ohne Alt-Text."))
        seo = c.get("seo") or {}
        if not (seo.get("title") or "").strip() or not (seo.get("description") or "").strip():
            out.append(_f(3, "auto", "SEO", f"{name}: SEO-Titel/-Beschreibung fehlen."))

    shop = snap.get("shop") or {}
    if "shop" not in snap.get("errors", {}):
        have = {pol["type"] for pol in shop.get("shopPolicies") or [] if text_of(pol.get("body"))}
        for typ, label in REQUIRED_POLICIES.items():
            if typ not in have:
                out.append(_f(1, "du", "Recht", f"{label} fehlt oder ist leer (in DE/AT Pflicht bzw. dringend empfohlen)."))

    pages = snap.get("pages", [])
    if "pages" not in snap.get("errors", {}):
        handles = " ".join(f"{pg.get('handle', '')} {pg.get('title', '').lower()}" for pg in pages if pg.get("isPublished"))
        for label, keys in TRUST_PAGES.items():
            if not any(k in handles for k in keys):
                out.append(_f(2, "du", "Vertrauen", f"Seite „{label}“ fehlt – Text kann ich entwerfen, du gibst frei."))

    main = [t for t in snap.get("themes", []) if t.get("role") == "MAIN"]
    if snap.get("themes") and not main:
        out.append(_f(2, "du", "Design", "Kein veröffentlichtes Theme gefunden."))

    for o in snap.get("orders", []):
        try:
            created = datetime.date.fromisoformat(o["createdAt"][:10])
        except (KeyError, ValueError):
            continue
        if (o.get("displayFinancialStatus") == "PAID"
                and o.get("displayFulfillmentStatus") == "UNFULFILLED"
                and (today - created).days >= 2):
            out.append(_f(1, "du", "Bestellungen", f"Bestellung {o['name']} ist bezahlt, aber seit {(today - created).days} Tagen nicht versendet."))

    out.sort(key=lambda f: (f["prio"], f["area"] != "Technik", f["who"] != "du", f["area"]))
    return out


PRIO_LABEL = {1: "Hoch", 2: "Mittel", 3: "Niedrig"}


def report(snap: dict[str, Any], found: list[dict[str, Any]], backup_path: Path | None) -> str:
    shop = snap.get("shop") or {}
    products = snap.get("products", [])
    status: dict[str, int] = {}
    for p in products:
        status[p.get("status", "?")] = status.get(p.get("status", "?"), 0) + 1
    main = next((t["name"] for t in snap.get("themes", []) if t.get("role") == "MAIN"), "–")
    lines = [
        f"# Shop-Kontrolle {snap['date']}",
        "",
        f"**Shop:** {shop.get('name', '–')} ({shop.get('myshopifyDomain', '–')}), "
        f"Währung {shop.get('currencyCode', '–')}, Tarif {(shop.get('plan') or {}).get('publicDisplayName', '–')}",
        f"**Produkte:** {len(products)} ({', '.join(f'{k} {v}' for k, v in sorted(status.items())) or '–'}) · "
        f"**Kollektionen:** {len(snap.get('collections', []))} · **Seiten:** {len(snap.get('pages', []))} · "
        f"**Theme:** {main} · **Letzte Bestellungen:** {len(snap.get('orders', []))}",
    ]
    if backup_path:
        lines.append(f"**Sicherung der Originalwerte:** `{backup_path.as_posix()}`")
    lines += ["", "Nur gelesen – an diesem Bericht wurde im Shop nichts geändert.", ""]
    auto = [f for f in found if f["who"] == "auto"]
    mine = [f for f in found if f["who"] == "du"]
    lines += [f"## Was fehlt (nach Wichtigkeit) – {len(found)} Punkte", ""]
    for title, group in (("Entscheidest du", mine), ("Kann der Agent sicher allein erledigen", auto)):
        lines += [f"### {title} ({len(group)})", ""]
        if not group:
            lines += ["Nichts.", ""]
            continue
        for prio in (1, 2, 3):
            items = [f for f in group if f["prio"] == prio]
            if items:
                lines.append(f"**{PRIO_LABEL[prio]}**")
                lines += [f"- [{f['area']}] {f['text']}" for f in items]
                lines.append("")
    return "\n".join(lines)


def run_audit(shop: Any, out_dir: Path) -> tuple[Path, Path, list[dict[str, Any]]]:
    snap = snapshot(shop)
    backup_path = write_backup(snap, out_dir)
    found = findings(snap)
    report_path = out_dir / f"audit-{snap['date']}.md"
    report_path.write_text(report(snap, found, backup_path), encoding="utf-8")
    return report_path, backup_path, found
