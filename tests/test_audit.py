"""Audit, backup, restore and the new content tools, against a fake shop."""

import copy
import datetime
import json


from shopify_agent import audit
from shopify_agent.tools import Toolbox

PRODUCT = {
    "id": "gid://shopify/Product/1", "title": "Goldbarren 1 oz", "handle": "goldbarren", "status": "ACTIVE",
    "vendor": "Goldbot", "productType": "", "tags": [], "descriptionHtml": "<p>Gold.</p>",
    "onlineStoreUrl": None, "seo": {"title": None, "description": None},
    "media": {"edges": [{"node": {"id": "gid://shopify/MediaImage/5", "alt": "", "mediaContentType": "IMAGE"}}]},
    "variants": {"edges": [{"node": {"id": "gid://shopify/ProductVariant/9", "title": "Default Title", "sku": "",
                                     "price": "100.00", "compareAtPrice": "90.00", "inventoryQuantity": 0}}]},
}
DRAFT = {**copy.deepcopy(PRODUCT), "id": "gid://shopify/Product/2", "title": "Entwurf", "status": "DRAFT",
         "descriptionHtml": "<p>" + "Schöner Text. " * 40 + "</p>",
         "seo": {"title": "Entwurf | Goldbot", "description": "Kurz."}}


class AuditShop:
    """Pages products 1 per page to exercise pagination; records mutations."""

    def __init__(self, products=None, collections=None, fail=()):
        self.products = copy.deepcopy(products if products is not None else [PRODUCT, DRAFT])
        self.collections = copy.deepcopy(collections or [])
        self.fail = set(fail)
        self.mutations = []

    def _page(self, items, key, variables):
        i = int(variables.get("after") or 0)
        nxt = i + 1 < len(items)
        return {key: {"pageInfo": {"hasNextPage": nxt, "endCursor": str(i + 1)},
                      "edges": [{"node": copy.deepcopy(n)} for n in items[i:i + 1]]}}

    def graphql(self, query, variables=None):
        variables = variables or {}
        from shopify_agent.shopify import ShopifyError
        for f in self.fail:
            if f in query:
                raise ShopifyError(f"Field '{f}' doesn't exist")
        if query.lstrip().startswith("mutation"):
            self.mutations.append((query, variables))
            if "productUpdate" in query:
                p = variables["product"]
                for prod in self.products:
                    if prod["id"] == p["id"]:
                        prod.update({k: v for k, v in p.items() if k != "id"})
                return {"productUpdate": {"product": {"id": p["id"], "title": "x", "status": "ACTIVE", "tags": []},
                                          "userErrors": []}}
            if "fileUpdate" in query:
                return {"fileUpdate": {"files": variables["files"], "userErrors": []}}
            if "collectionUpdate" in query:
                return {"collectionUpdate": {"collection": {"id": variables["collection"]["id"], "title": "c"}, "userErrors": []}}
            if "collectionCreate" in query:
                return {"collectionCreate": {"collection": {"id": "gid://shopify/Collection/77", "title": "n", "handle": "n"},
                                             "userErrors": []}}
            raise AssertionError(query)
        if "shopPolicies" in query:
            return {"shop": {"name": "Goldbot", "myshopifyDomain": "goldbot.myshopify.com", "primaryDomain": {"url": "x"},
                             "currencyCode": "EUR", "contactEmail": "a@b", "plan": {"publicDisplayName": "Basic"},
                             "shopPolicies": [{"type": "PRIVACY_POLICY", "title": "Datenschutz", "body": "<p>Text</p>", "url": "u"},
                                              {"type": "LEGAL_NOTICE", "title": "Impressum", "body": "", "url": "u"}]}}
        if "products(" in query:
            return self._page(self.products, "products", variables)
        if "collections(" in query:
            return self._page(self.collections, "collections", variables)
        if "pages(" in query:
            return self._page([{"id": "gid://shopify/Page/1", "title": "Kontakt", "handle": "kontakt",
                                "isPublished": True, "body": "x"}], "pages", variables)
        if "themes(" in query:
            return {"themes": {"edges": [{"node": {"id": "t", "name": "Dawn", "role": "MAIN"}}]}}
        if "orders(" in query:
            old = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
            return {"orders": {"edges": [{"node": {"id": "o", "name": "#1001", "createdAt": old + "T10:00:00Z",
                                                   "displayFinancialStatus": "PAID", "displayFulfillmentStatus": "UNFULFILLED",
                                                   "totalPriceSet": {"shopMoney": {"amount": "1", "currencyCode": "EUR"}}}}]}}
        if "product(id" in query:
            return {"product": {"seo": {"title": "Alt Titel", "description": "Alte Beschreibung"}}}
        if "collection(id" in query:
            return {"collection": {"seo": {"title": "K", "description": "KB"}}}
        raise AssertionError(query)


def test_snapshot_reads_all_pages_and_sections():
    snap = audit.snapshot(AuditShop())
    assert [p["title"] for p in snap["products"]] == ["Goldbarren 1 oz", "Entwurf"]
    assert snap["products"][0]["media"][0]["id"] == "gid://shopify/MediaImage/5"
    assert snap["themes"][0]["role"] == "MAIN" and snap["orders"] and not snap["errors"]
    assert not AuditShop().mutations


def test_failing_section_is_reported_not_raised():
    snap = audit.snapshot(AuditShop(fail={"pages("}))
    assert "pages" in snap["errors"] and snap["products"]
    found = audit.findings(snap)
    assert found[0]["area"] == "Technik" and found[0]["prio"] == 1


def test_findings_cover_high_end_basics():
    texts = [f"{f['prio']}|{f['who']}|{f['text']}" for f in audit.findings(audit.snapshot(AuditShop()))]
    joined = "\n".join(texts)
    assert "1|auto|„Goldbarren 1 oz“ hat praktisch keine Beschreibung" in joined
    assert "Medien ohne Alt-Text" in joined and "kein SEO-Titel" in joined
    assert "nur 1 Bild" in joined
    assert "Streichpreis 90.0 ist nicht höher" in joined
    assert "ohne Bestand" in joined
    assert "ist ein Entwurf" in joined
    assert "1|auto|Keine Kollektionen" in joined
    assert "1|du|Impressum fehlt" in joined          # empty body counts as missing
    assert "Datenschutz" not in joined               # present with text
    assert "AGB fehlt" in joined
    assert "„Über uns“ fehlt" in joined and "„Kontakt“ fehlt" not in joined
    assert "#1001 ist bezahlt, aber seit 5 Tagen nicht versendet" in joined
    # sorted by priority
    prios = [int(t.split("|")[0]) for t in texts]
    assert prios == sorted(prios)


def test_backup_keeps_originals_and_never_overwrites(tmp_path):
    snap = audit.snapshot(AuditShop())
    first = audit.write_backup(snap, tmp_path)
    second = audit.write_backup(snap, tmp_path)
    assert first.name == f"backup-{snap['date']}.json" and second.name == f"backup-{snap['date']}-2.json"
    data = json.loads(first.read_text(encoding="utf-8"))
    p = data["products"][0]
    assert p["descriptionHtml"] == "<p>Gold.</p>" and p["media"] == [{"id": "gid://shopify/MediaImage/5", "alt": ""}]
    assert p["prices"][0]["price"] == "100.00"


def test_run_audit_writes_report_without_changing_shop(tmp_path):
    shop = AuditShop()
    report_path, backup_path, found = audit.run_audit(shop, tmp_path)
    text = report_path.read_text(encoding="utf-8")
    assert "Goldbot (goldbot.myshopify.com)" in text and "Theme:** Dawn" in text
    assert "### Entscheidest du" in text and "### Kann der Agent sicher allein erledigen" in text
    assert backup_path.exists() and not shop.mutations


def test_restore_writes_back_only_changed_content(tmp_path):
    shop = AuditShop(collections=[{"id": "gid://shopify/Collection/3", "title": "Barren", "handle": "barren",
                                   "descriptionHtml": "", "sortOrder": "MANUAL", "seo": {"title": None, "description": None},
                                   "image": None, "productsCount": {"count": 2}}])
    backup = audit.write_backup(audit.snapshot(shop), tmp_path)
    # the agent improves product 1 and the collection
    shop.products[0]["descriptionHtml"] = "<p>Neu und lang.</p>"
    shop.products[0]["seo"] = {"title": "Neu", "description": "Neu"}
    shop.products[0]["media"]["edges"][0]["node"]["alt"] = "Goldbarren von vorne"
    shop.collections[0]["descriptionHtml"] = "<p>Neu</p>"
    approvals = []
    log = audit.restore(shop, backup, lambda k, s: approvals.append(k) or True)
    assert set(approvals) == {"content"} and len(log) == 3
    prod = [v for q, v in shop.mutations if "productUpdate" in q][0]["product"]
    assert prod == {"id": "gid://shopify/Product/1", "descriptionHtml": "<p>Gold.</p>",
                    "seo": {"title": "", "description": ""}}
    files = [v for q, v in shop.mutations if "fileUpdate" in q][0]["files"]
    assert files == [{"id": "gid://shopify/MediaImage/5", "alt": ""}]
    col = [v for q, v in shop.mutations if "collectionUpdate" in q][0]["collection"]
    assert col == {"id": "gid://shopify/Collection/3", "descriptionHtml": ""}
    assert not any("price" in json.dumps(v).lower() for _, v in shop.mutations)


def test_restore_declined_changes_nothing(tmp_path):
    shop = AuditShop()
    backup = audit.write_backup(audit.snapshot(shop), tmp_path)
    shop.products[0]["descriptionHtml"] = "<p>Neu</p>"
    audit.restore(shop, backup, lambda k, s: False)
    assert not shop.mutations


def tb_for(shop, tmp_path, approve=True):
    approvals = []
    return Toolbox(shop, tmp_path, lambda k, s: approvals.append(k) or approve), approvals


def test_update_product_seo_keeps_other_field(tmp_path):
    shop = AuditShop()
    tb, approvals = tb_for(shop, tmp_path)
    out, err = tb.run("update_product", {"product_id": "gid://shopify/Product/1", "title": None,
                                         "description_html": None, "tags": None, "status": None,
                                         "product_type": None, "seo_title": "Goldbarren 1 oz kaufen",
                                         "seo_description": None})
    assert not err and approvals == ["content"]
    sent = shop.mutations[0][1]["product"]
    assert sent["seo"] == {"title": "Goldbarren 1 oz kaufen", "description": "Alte Beschreibung"}


def test_seo_length_is_enforced(tmp_path):
    shop = AuditShop()
    tb, approvals = tb_for(shop, tmp_path)
    out, err = tb.run("update_collection", {"collection_id": "gid://shopify/Collection/3", "description_html": None,
                                            "seo_title": "x" * 71, "seo_description": "y"})
    assert err and "70" in out and not approvals and not shop.mutations


def test_set_media_alt_and_rejects_empty(tmp_path):
    shop = AuditShop()
    tb, approvals = tb_for(shop, tmp_path)
    out, err = tb.run("set_media_alt", {"items": [{"media_id": "gid://shopify/MediaImage/5", "alt": " "}]})
    assert err and not shop.mutations
    out, err = tb.run("set_media_alt", {"items": [{"media_id": "gid://shopify/MediaImage/5", "alt": "Goldbarren, Vorderseite"}]})
    assert not err and approvals == ["content"]
    assert shop.mutations[0][1]["files"] == [{"id": "gid://shopify/MediaImage/5", "alt": "Goldbarren, Vorderseite"}]


def test_create_collection_smart_rule_and_validation(tmp_path):
    shop = AuditShop()
    tb, _ = tb_for(shop, tmp_path)
    out, err = tb.run("create_collection", {"title": "Barren", "description_html": "<p>x</p>",
                                            "product_ids": None, "tag_rule": None})
    assert err and not shop.mutations
    out, err = tb.run("create_collection", {"title": "Barren", "description_html": "<p>x</p>",
                                            "product_ids": None, "tag_rule": "barren"})
    assert not err
    sent = shop.mutations[0][1]["collection"]
    assert "ruleSet" not in sent and "collectionCreate(collection:" in shop.mutations[0][0]
    src = sent["sources"][0]["source"]
    assert src["targetType"] == "PRODUCTS"
    assert src["inclusion"]["conditions"] == [
        {"productTag": {"matchType": "ANY", "relation": "TAGGED_WITH", "values": ["barren"]}}]
    out, err = tb.run("create_collection", {"title": "Auswahl", "description_html": "<p>x</p>",
                                            "product_ids": ["gid://shopify/Product/1"], "tag_rule": None})
    assert not err
    assert shop.mutations[1][1]["collection"]["sources"][0]["source"]["inclusion"] == {
        "selections": [{"productId": "gid://shopify/Product/1"}]}


def test_list_collections(tmp_path):
    shop = AuditShop(collections=[{"id": "c1", "title": "A"}, {"id": "c2", "title": "B"}])
    tb, _ = tb_for(shop, tmp_path)
    out, err = tb.run("list_collections", {})
    assert not err and '"c2"' in out


def test_autopilot_backs_up_first_and_blocks_texts_without_full_backup(tmp_path, monkeypatch):
    import shopify_agent.autopilot as ap
    from types import SimpleNamespace as NS
    from shopify_agent.agent import ShopifyAgent
    from test_agent import FakeClient, tool_use

    upd = {"product_id": "gid://shopify/Product/1", "title": None, "description_html": "<p>Neu</p>",
           "tags": None, "status": None, "product_type": None, "seo_title": None, "seo_description": None}
    for fail, expect_change in ((set(), True), ({"pages("}, False)):
        shop = AuditShop(fail=fail)
        client = FakeClient([
            NS(stop_reason="tool_use", content=[tool_use("t1", "update_product", upd)]),
            NS(stop_reason="end_turn", content=[NS(type="text", text="Fertig.")]),
        ])
        monkeypatch.setattr(ap, "ShopifyClient", lambda: shop)
        monkeypatch.setattr(ap, "ShopifyAgent", lambda tb: ShopifyAgent(tb, client=client))
        out = tmp_path / ("ok" if expect_change else "fail")
        assert ap.run(tmp_path / "media", out) == 0
        assert list(out.glob("backup-*.json")) and list(out.glob("audit-*.md"))
        assert bool(shop.mutations) is expect_change
        task = client.requests[0]["messages"][0]["content"]
        assert "Audit findings" in task and "Medien ohne Alt-Text" in task
        if not expect_change:
            assert "nicht vollständig gelesen" in (out / "ESCALATIONS.md").read_text()


def test_cli_audit_and_restore(tmp_path, monkeypatch, capsys):
    import shopify_agent.agent as ag

    shop = AuditShop()
    monkeypatch.setattr(ag, "ShopifyClient", lambda: shop)
    assert ag.main(["--audit", "--out-dir", str(tmp_path)]) == 0
    assert "Shop-Kontrolle" in capsys.readouterr().out and not shop.mutations
    backup = next(tmp_path.glob("backup-*.json"))
    shop.products[0]["title"] = "Geändert"
    assert ag.main(["--restore", str(backup), "--yes"]) == 0
    assert shop.products[0]["title"] == "Goldbarren 1 oz"
