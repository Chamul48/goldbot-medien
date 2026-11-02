"""Offline tests: Shopify and Claude are replaced by fakes."""

from pathlib import Path
from types import SimpleNamespace as NS

from shopify_agent.agent import ShopifyAgent
from shopify_agent.tools import TOOLS, Toolbox


class FakeShop:
    def __init__(self):
        self.calls = []

    def graphql(self, query, variables=None):
        self.calls.append((query, variables))
        if "products(" in query:
            return {"products": {"edges": [{"node": {
                "id": "gid://shopify/Product/1", "title": "Goldbarren",
                "variants": {"edges": [{"node": {"id": "gid://shopify/ProductVariant/9", "price": "10.00"}}]},
            }}]}}
        if "productUpdate" in query:
            p = variables["product"]
            return {"productUpdate": {"product": {"id": p["id"], "title": p.get("title")}, "userErrors": []}}
        return {"ok": True}


class FakeClient:
    def __init__(self, responses):
        self.requests = []
        it = iter(responses)

        def create(**kw):
            self.requests.append(kw)
            return next(it)

        self.beta = NS(messages=NS(create=create))


def tool_use(id_, name, inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def make(tmp_path, approve=True):
    shop = FakeShop()
    approvals = []
    tb = Toolbox(shop, tmp_path, confirm=lambda k, s: approvals.append((k, s)) or approve)
    return shop, tb, approvals


def test_tool_schemas_are_strict():
    for t in TOOLS:
        assert t["strict"] is True
        assert t["input_schema"]["additionalProperties"] is False


def test_search_then_update_with_approval(tmp_path):
    shop, tb, approvals = make(tmp_path)
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use("t1", "search_products", {"query": "title:*gold*", "limit": 5})]),
        NS(stop_reason="tool_use", content=[tool_use("t2", "update_product", {
            "product_id": "gid://shopify/Product/1", "title": "Goldbarren 1oz",
            "description_html": None, "tags": None, "status": None})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="Fertig.")]),
    ])
    agent = ShopifyAgent(tb, client=client)
    assert agent.send("Benenne den Goldbarren um") == "Fertig."
    assert len(approvals) == 1
    update = [v for q, v in shop.calls if "productUpdate" in q][0]
    assert update["product"] == {"id": "gid://shopify/Product/1", "title": "Goldbarren 1oz"}
    # History is append-only and alternates roles.
    assert [m["role"] for m in agent.messages] == ["user", "assistant"] * 3
    # Each request enables the server-side fallback.
    assert client.requests[0]["fallbacks"] == "default"


def test_declined_change_is_not_sent(tmp_path):
    shop, tb, _ = make(tmp_path, approve=False)
    out, is_error = tb.run("update_product", {
        "product_id": "gid://shopify/Product/1", "title": "X",
        "description_html": None, "tags": None, "status": None})
    assert is_error and "Not approved" in out
    assert not shop.calls


def test_upload_rejects_paths_outside_media_dir(tmp_path):
    _, tb, approvals = make(tmp_path)
    out, is_error = tb.run("upload_media", {"path": "../secret.mp4", "alt": "x", "product_id": None})
    assert is_error and not approvals


def test_graphql_mutation_needs_approval_query_does_not(tmp_path):
    _, tb, approvals = make(tmp_path)
    tb.run("graphql", {"query": "{ shop { name } }", "variables_json": "{}"})
    assert not approvals
    tb.run("graphql", {"query": "mutation{ x }", "variables_json": "{}"})
    assert len(approvals) == 1


def test_list_local_media(tmp_path):
    (tmp_path / "reel").mkdir()
    (tmp_path / "reel" / "video.mp4").write_bytes(b"123")
    (tmp_path / "notes.txt").write_text("x")
    _, tb, _ = make(tmp_path)
    out, _ = tb.run("list_local_media", {})
    assert "reel/video.mp4" in out and "notes.txt" not in out


def test_refusal_stops_without_running_tools(tmp_path):
    shop, tb, _ = make(tmp_path)
    client = FakeClient([NS(stop_reason="refusal", content=[tool_use("t1", "get_shop_info", {})])])
    assert "declined" in ShopifyAgent(tb, client=client).send("hi")
    assert not shop.calls


def test_autopilot_policy_allows_content_escalates_price(tmp_path):
    from shopify_agent.autopilot import autopilot_policy

    ref = []
    tb = Toolbox(FakeShop(), tmp_path, autopilot_policy(ref))
    ref.append(tb)
    out, err = tb.run("update_product", {"product_id": "gid://shopify/Product/1", "title": "Neu",
                                         "description_html": None, "tags": None, "status": None})
    assert not err
    out, err = tb.run("update_variant_prices", {"product_id": "gid://shopify/Product/1", "variants": [
        {"variant_id": "gid://shopify/ProductVariant/9", "price": "1.00", "compare_at_price": None}]})
    assert err and tb.escalations[0]["topic"] == "Needs approval (price)"
    out, err = tb.run("update_product", {"product_id": "gid://shopify/Product/1", "title": None,
                                         "description_html": None, "tags": None, "status": "ARCHIVED"})
    assert err and len(tb.escalations) == 2


def test_upload_is_not_repeated(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"1")
    state = tmp_path / "state.json"
    state.write_text('{"uploaded": {"v.mp4": {"file_id": "gid://shopify/Video/1", "product_id": null, "date": "2026-11-01"}}}')
    tb = Toolbox(FakeShop(), tmp_path, lambda k, s: True, state_file=state)
    out, err = tb.run("upload_media", {"path": "v.mp4", "alt": "x", "product_id": None})
    assert err and "already uploaded" in out
    assert '"already_uploaded": true' in tb.run("list_local_media", {})[0]


def test_autopilot_run_writes_report_and_escalations(tmp_path, monkeypatch):
    import shopify_agent.autopilot as ap

    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use("t1", "escalate", {"topic": "Preis prüfen", "details": "Zu billig"})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="Bericht: 1 Eskalation.")]),
    ])
    monkeypatch.setattr(ap, "ShopifyClient", FakeShop)
    monkeypatch.setattr(ap, "ShopifyAgent", lambda tb: ShopifyAgent(tb, client=client))
    assert ap.run(tmp_path / "media", tmp_path / "out") == 0
    esc = (tmp_path / "out" / "ESCALATIONS.md").read_text()
    assert "Preis prüfen" in esc and "Bericht" in esc
    assert list((tmp_path / "out" / "reports").glob("*.md"))
