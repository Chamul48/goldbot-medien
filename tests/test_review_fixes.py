"""Fixes from the 2026-11-03 review: history repair, --yes limits, backup, change log, retries."""

import json
from types import SimpleNamespace as NS

import requests

from shopify_agent import agent as agent_mod
from shopify_agent import audit
from shopify_agent.agent import ShopifyAgent
from shopify_agent.shopify import ShopifyClient, ShopifyError
from shopify_agent.tools import Toolbox
from test_agent import FakeClient, FakeShop, tool_use


def test_cut_off_tool_use_gets_a_tool_result(tmp_path):
    tb = Toolbox(FakeShop(), tmp_path, confirm=lambda k, s: True)
    client = FakeClient([
        NS(stop_reason="max_tokens", content=[tool_use("t1", "get_shop_info", {})]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="ok")]),
    ])
    a = ShopifyAgent(tb, client=client)
    assert "cut off" in a.send("hi")
    last = a.messages[-1]
    assert last["role"] == "user" and last["content"][0]["tool_use_id"] == "t1"
    assert a.send("weiter") == "ok"  # history is valid again
    # the API needs a tool_result before the next user text
    assert a.messages[2]["content"][0]["type"] == "tool_result"


def test_yes_flag_still_asks_for_prices(monkeypatch):
    asked = []
    monkeypatch.setattr(agent_mod, "ask_confirm", lambda k, s: asked.append(k) or False)
    captured = {}

    class Dummy:
        def __init__(self, toolbox, client=None):
            captured["confirm"] = toolbox.confirm

        def send(self, text):
            return ""

    monkeypatch.setattr(agent_mod, "ShopifyAgent", Dummy)
    monkeypatch.setattr(agent_mod, "ShopifyClient", lambda: FakeShop())
    agent_mod.main(["--yes", "hallo"])
    c = captured["confirm"]
    assert c("content", "x") and c("media", "x")
    assert not c("price", "x") and not c("status", "x") and not c("graphql", "x")
    assert asked == ["price", "status", "graphql"]
    assert "adjust prices" not in agent_mod.SYSTEM_PROMPT


def test_chat_backs_up_before_first_write_and_logs_change(tmp_path):
    from test_audit import AuditShop
    shop = AuditShop()
    tb = Toolbox(shop, tmp_path / "media", confirm=lambda k, s: True,
                 backup_dir=tmp_path / "out", change_log=tmp_path / "out")
    args = {"product_id": "gid://shopify/Product/1", "title": "Neu",
            "description_html": None, "tags": None, "status": None}
    out, err = tb.run("update_product", args)
    assert not err
    out, err = tb.run("update_product", args)
    backups = list((tmp_path / "out").glob("backup-*.json"))
    assert len(backups) == 1  # once per session
    log = next((tmp_path / "out").glob("aenderungen-*.md")).read_text(encoding="utf-8")
    assert log.count("gid://shopify/Product/1") == 2 and "update_product" in log
    assert len(tb.changes) == 2
    data = json.loads(backups[0].read_text(encoding="utf-8"))
    assert data["products"][0]["title"] == "Goldbarren 1 oz"  # original, before the change


def test_no_write_without_backup(tmp_path):
    tb = Toolbox(FakeShop(), tmp_path, confirm=lambda k, s: True, backup_dir=tmp_path)
    out, err = tb.run("update_product", {"product_id": "gid://shopify/Product/1", "title": "Neu",
                                         "description_html": None, "tags": None, "status": None})
    assert err and "backup" in out


def test_declined_write_is_not_logged(tmp_path):
    tb = Toolbox(FakeShop(), tmp_path, confirm=lambda k, s: False, change_log=tmp_path)
    tb.run("update_product", {"product_id": "gid://shopify/Product/1", "title": "Neu",
                              "description_html": None, "tags": None, "status": None})
    assert not tb.changes and not list(tmp_path.glob("aenderungen-*.md"))


def test_product_query_stays_below_cost_limit():
    # products(first:n) * (1 + media(first) + variants(first)) + connection overhead
    import re
    media = int(re.search(r"media\(first: (\d+)\)", audit.PRODUCTS_Q).group(1))
    variants = int(re.search(r"variants\(first: (\d+)\)", audit.PRODUCTS_Q).group(1))
    cost = 2 + audit.PRODUCT_PAGE * (1 + (2 + media) + (2 + variants))
    assert cost < 1000


class Resp:
    def __init__(self, status, body, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.text = json.dumps(body)

    def json(self):
        return self._body


def _client(responses):
    c = ShopifyClient.__new__(ShopifyClient)
    c.endpoint, c.timeout, c.sleep = "https://x/graphql.json", 1, lambda s: None
    it = iter(responses)

    def post(*a, **kw):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    c.session = NS(post=post)
    return c


def test_graphql_retries_throttle_5xx_and_network():
    c = _client([
        requests.ConnectionError("weg"),
        Resp(503, {}),
        Resp(200, {"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]}),
        Resp(200, {"data": {"ok": 1}}),
    ])
    assert c.graphql("{ shop { name } }") == {"ok": 1}


def test_graphql_gives_up_with_shopify_error():
    c = _client([requests.ConnectionError("weg")] * 5)
    try:
        c.graphql("{ x }")
    except ShopifyError as exc:
        assert "Network" in str(exc)
    else:
        raise AssertionError("no error")


def test_autopilot_writes_report_even_if_agent_crashes(tmp_path, monkeypatch):
    from shopify_agent import autopilot

    monkeypatch.setattr(autopilot, "ShopifyClient", lambda: FakeShop())
    monkeypatch.setattr(autopilot.audit, "run_audit",
                        lambda shop, out: (out / "a.md", out / "b.json", []))

    class Boom:
        def __init__(self, tb):
            pass

        def send(self, text):
            raise RuntimeError("API weg")

    monkeypatch.setattr(autopilot, "ShopifyAgent", Boom)
    assert autopilot.run(tmp_path / "social", tmp_path) == 1
    report = next((tmp_path / "reports").glob("*.md")).read_text(encoding="utf-8")
    assert "abgebrochen" in report and (tmp_path / "ESCALATIONS.md").exists()
