import json
from pathlib import Path

import pytest

from goldbot import ideas, llm, profile, report, trends
from goldbot.config import load_config

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("GOLDBOT_OFFLINE", "1")


@pytest.fixture
def cfg():
    return load_config(Path(__file__).parent.parent / "config.example.yaml")


def test_parse_google_trends_rss():
    items = trends.parse_feed((FIX / "google_trends.xml").read_text(), "Google Trends AT")
    assert [i.title for i in items] == ["Goldpreis", "Fußball Ergebnis", "KI Video Generator"]
    assert items[0].traffic == 20000


def test_parse_reddit_atom_and_detect_leads(cfg):
    items = trends.parse_feed((FIX / "reddit.xml").read_text(), "Reddit r/forhire")
    assert items[0].url == "https://www.reddit.com/r/forhire/1"
    assert "short form edits" in items[0].summary
    scored = trends.score(items, cfg["trends"]["keywords"])
    top = scored[0]
    assert top.kind == "auftrag" and "tiktok" in top.matched
    # "[For Hire]" ist ein Anbieter, kein Auftrag
    assert next(i for i in scored if "Logo" in i.title).kind == "trend"


def test_score_prefers_niche_over_raw_traffic(cfg):
    items = trends.parse_feed((FIX / "google_trends.xml").read_text(), "Google Trends AT")
    scored = trends.score(items, cfg["trends"]["keywords"])
    assert scored[-1].title == "Fußball Ergebnis"


def test_parse_hackernews():
    payload = {"hits": [{"title": "AI video tools", "objectID": "42", "points": 120, "url": None}]}
    items = trends.parse_hackernews(payload, "HN")
    assert items[0].url.endswith("id=42") and items[0].traffic == 120


def test_bad_feed_returns_empty():
    assert trends.parse_feed("<not xml", "x") == []


def test_collect_survives_failing_sources(cfg):
    class FakeResp:
        def __init__(self, text): self.text = text
        def json(self): return json.loads(self.text)

    class FakeFetcher:
        def get(self, url):
            if "trends.google" in url:
                return FakeResp((FIX / "google_trends.xml").read_text())
            if "reddit" in url:
                return FakeResp((FIX / "reddit.xml").read_text())
            return None

    items, errors = trends.scan(cfg, FakeFetcher())
    assert items and errors
    assert all(e.startswith("Hacker News") for e in errors)


def test_template_profile_respects_fiverr_limits(cfg):
    pack, source, _ = profile.build_profile(cfg)
    assert source == "vorlage"
    assert len(pack["one_liner"]) <= profile.LIMITS["one_liner"]
    assert profile.LIMITS["about_min"] <= len(pack["about"]) <= profile.LIMITS["about_max"]
    for gig in pack["gigs"]:
        assert len(gig["title"]) <= 80 and gig["title"].startswith("I will")
        assert len(gig["tags"]) <= 5 and all(len(t) <= 20 for t in gig["tags"])
        assert len(gig["description"]) <= 1200
        assert [p["name"] for p in gig["packages"]] == ["Basic", "Standard", "Premium"]


def test_enforce_limits_truncates():
    pack = {"one_liner": "x " * 100, "about": "word " * 200, "skills": [], "profile_photo_tips": [],
            "gigs": [{"title": "I will " + "edit " * 40, "tags": ["A/B!", "a b", "x" * 40, "1", "2", "3"],
                      "description": "d " * 1000}]}
    pack, notes = profile.enforce_limits(pack)
    assert len(pack["about"]) <= 600 and len(pack["one_liner"]) <= 60
    assert len(pack["gigs"][0]["title"]) <= 80
    assert pack["gigs"][0]["tags"][0] == "a b" and len(pack["gigs"][0]["tags"]) == 5
    assert notes


def test_ideas_and_report(cfg, tmp_path):
    items = trends.score(
        trends.parse_feed((FIX / "reddit.xml").read_text(), "Reddit r/forhire")
        + trends.parse_feed((FIX / "google_trends.xml").read_text(), "Google Trends AT"),
        cfg["trends"]["keywords"],
    )
    result, source = ideas.build_ideas(cfg, items)
    assert source == "vorlage" and 1 <= len(result["ideas"]) <= 8
    assert result["ideas"][0]["title"].startswith("Auftrag prüfen")

    folder = report.write(tmp_path, profile=profile.build_profile(cfg), trends=(items, ["HN"]),
                          ideas=(result, source))
    text = (folder / "bericht.md").read_text()
    assert "Vertriebsideen" in text and "Mögliche Aufträge" in text and "Gig 1" in text
    assert json.loads((folder / "daten.json").read_text())["profile"]["gigs"]


def test_llm_offline():
    assert llm.available() is False
    assert llm.ask_json("s", "p", {"type": "object"}) is None


def test_fetcher_retries_on_429():
    class R:
        def __init__(self, code, headers=None): self.status_code, self.headers = code, headers or {}

    class S:
        headers = {}
        def __init__(self): self.calls = 0
        def get(self, url, timeout):
            self.calls += 1
            return R(429, {"Retry-After": "7"}) if self.calls == 1 else R(200)

    sess, slept = S(), []
    f = trends.Fetcher(delay=0, session=sess)
    f.sleep = slept.append
    assert f.get("https://www.reddit.com/r/x/new/.rss").status_code == 200
    assert sess.calls == 2 and slept == [7.0]


def test_fetcher_gives_up_after_retries():
    class S:
        headers = {}
        def get(self, url, timeout):
            return type("R", (), {"status_code": 429, "headers": {}})()

    f = trends.Fetcher(delay=0, session=S())
    f.sleep = lambda s: None
    assert f.get("https://www.reddit.com/x") is None


def test_hn_video_tag_is_not_a_topic_match():
    items = trends.parse_hackernews({"hits": [{"title": "Future of AI [video]", "objectID": "1"}]}, "HN")
    assert items[0].title == "Future of AI"
    assert trends.score(items, ["video"])[0].matched == []
