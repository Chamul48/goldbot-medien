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
    # "[For Hire]" ist ein Anbieter (Konkurrenz), kein Auftrag
    assert next(i for i in scored if "Logo" in i.title).kind == "konkurrenz"


def test_score_prefers_niche_over_raw_traffic(cfg):
    items = trends.parse_feed((FIX / "google_trends.xml").read_text(), "Google Trends AT")
    scored = trends.score(items, cfg["trends"]["keywords"])
    assert scored[-1].title == "Fußball Ergebnis"


def test_parse_hackernews():
    payload = {"hits": [{"title": "AI video tools", "objectID": "42", "points": 120, "url": None}]}
    items = trends.parse_hackernews(payload, "HN")
    assert items[0].url.endswith("id=42") and items[0].traffic == 120


def test_bad_feed_counts_as_error():
    with pytest.raises(ValueError):
        trends.parse_feed("<html>Sperrseite", "x")


def test_collect_survives_failing_sources(cfg):
    class FakeResp:
        def __init__(self, text): self.text, self.content = text, text.encode("utf-8")
        def json(self): return json.loads(self.text)

    class FakeFetcher:
        def get(self, url):
            if "trends.google" in url:
                return FakeResp((FIX / "google_trends.xml").read_text())
            if "reddit" in url:
                return FakeResp((FIX / "reddit.xml").read_text())
            return None

    fetched = []
    class Recording(FakeFetcher):
        def get(self, url):
            fetched.append(url)
            return super().get(url)

    items, errors = trends.scan(cfg, Recording())
    assert items and errors
    assert all(e.startswith("Hacker News") for e in errors)
    reddit = [u for u in fetched if "reddit" in u]
    assert len(reddit) == 1 and "forhire+HireAnEditor" in reddit[0]


def test_template_profile_respects_fiverr_limits(cfg):
    cfg["profile"]["pack_file"] = None
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
    assert not any("Bookkeeper" in i["title"] for i in result["ideas"])

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


def test_for_hire_posts_are_competitors_not_trends(cfg):
    item = trends.TrendItem(source="Reddit r/forhire", title="[For Hire] UGC video packs | From $97")
    scored = trends.score([item], cfg["trends"]["keywords"])[0]
    assert scored.kind == "konkurrenz" and scored.price == "$97"
    result, _ = ideas.build_ideas(cfg, [scored])
    assert not any("UGC video packs" in i["title"] for i in result["ideas"])


def test_trend_ideas_only_from_google_trends(cfg):
    hn = trends.TrendItem(source="Hacker News 'ai video'", title="AI video model released")
    gt = trends.TrendItem(source="Google Trends AT", title="Goldpreis", traffic=20000)
    result, _ = ideas.build_ideas(cfg, trends.score([hn, gt], cfg["trends"]["keywords"]))
    titles = [i["title"] for i in result["ideas"]]
    assert any("Goldpreis" in t for t in titles) and not any("AI video model" in t for t in titles)


def test_keyword_matches_german_compounds_but_not_short_substrings():
    items = [trends.TrendItem(source="G", title="Goldpreis steigt"), trends.TrendItem(source="G", title="Air Max")]
    a, b = trends.score(items, ["gold", "ai"])
    assert a.matched == ["gold"] and b.matched == []


def test_template_gigs_have_distinct_packages_and_faq(cfg):
    pack = profile.template_profile(cfg["profile"])
    gigs = pack["gigs"]
    assert len({str(g["packages"]) for g in gigs}) == 3
    assert len({str(g["faq"]) for g in gigs}) == 3
    reels, faceless, automation = gigs
    assert faceless["packages"][0]["price_usd"] > reels["packages"][0]["price_usd"]
    assert not any("video up to 30s" in i for p in automation["packages"] for i in p["includes"])
    for g in gigs:
        prices = [p["price_usd"] for p in g["packages"]]
        assert prices == sorted(prices) and prices[0] >= 5


def test_research_pack_is_used_without_api(cfg):
    pack, source, notes = profile.build_profile(cfg)
    assert source == "recherche" and not notes
    for g in pack["gigs"]:
        assert len(g["title"]) <= 80 and len(g["tags"]) == 5 and len(g["description"]) <= 1200
    assert pack["profile_photo_tips"] and len(pack["gigs"]) == 3


def test_missing_pack_falls_back_to_template(cfg):
    cfg["profile"]["pack_file"] = "docs/gibt-es-nicht.json"
    assert profile.build_profile(cfg)[1] == "vorlage"


# --------------------------------------------------------------------------- #
# Lokale KI (Ollama) – mit nachgebautem Server, ohne echtes Netzwerk
# --------------------------------------------------------------------------- #

class _FakeResp:
    def __init__(self, payload, code=200):
        self._payload, self.status_code = payload, code
    def json(self):
        return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            raise llm.requests.HTTPError(str(self.status_code))


@pytest.fixture
def fake_ollama(monkeypatch):
    monkeypatch.delenv("GOLDBOT_OFFLINE", raising=False)
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    llm._OLLAMA_CACHE.clear()
    state = {"models": ["qwen3:14b"], "answer": {"ideas": [], "weekly_focus": "x"}, "posted": []}
    monkeypatch.setattr(llm.requests, "get", lambda url, timeout: _FakeResp({"models": [{"name": m} for m in state["models"]]}))
    def post(url, json, timeout):
        state["posted"].append(json)
        return _FakeResp({"message": {"content": __import__("json").dumps(state["answer"])}})
    monkeypatch.setattr(llm.requests, "post", post)
    yield state
    llm._OLLAMA_CACHE.clear()


def test_auto_uses_ollama_without_key(fake_ollama):
    cfg = {"provider": "auto", "ollama_model": "qwen3:14b"}
    assert llm.provider(cfg) == "ollama"
    data = llm.ask_json("s", "p", {"type": "object", "required": ["ideas"]}, cfg)
    assert data["weekly_focus"] == "x"
    sent = fake_ollama["posted"][0]
    assert sent["format"]["type"] == "object" and sent["stream"] is False and sent["model"] == "qwen3:14b"


def test_missing_model_means_no_ai(fake_ollama):
    fake_ollama["models"] = []
    assert llm.provider({"ollama_model": "qwen3:14b"}) is None


def test_incomplete_answer_is_rejected(fake_ollama):
    fake_ollama["answer"] = {"weekly_focus": "x"}
    assert llm.ask_json("s", "p", {"type": "object", "required": ["ideas"]}, {}) is None


def test_provider_off(fake_ollama):
    assert llm.provider({"provider": "aus"}) is None


def test_ideas_from_ollama_end_to_end(fake_ollama, cfg):
    fake_ollama["answer"] = {"weekly_focus": "Fokus", "ideas": [{
        "title": "KI-Idee", "why_now": "w", "action_steps": ["a"], "channel": "Fiverr",
        "effort": "niedrig", "revenue_potential": "hoch"}]}
    result, source = ideas.build_ideas(cfg, [])
    assert result["ideas"][0]["title"] == "KI-Idee" and "Ollama" in source


def test_cut_drops_dangling_words():
    assert profile._cut("Professional video creator and AI automation expert for creators", 55) == \
        "Professional video creator and AI automation expert"


def test_local_ai_does_not_replace_research_pack(fake_ollama, cfg):
    pack, source, _ = profile.build_profile(cfg)
    assert source == "recherche" and not fake_ollama["posted"]


def test_local_ai_writes_profile_when_preferred(fake_ollama, cfg):
    cfg["profile"]["prefer_pack"] = False
    fake_ollama["answer"] = profile.template_profile(cfg["profile"])
    pack, source, _ = profile.build_profile(cfg)
    assert "Ollama" in source and fake_ollama["posted"]


def test_ideas_prompt_lists_only_matching_signals_with_links():
    items = [trends.TrendItem(source="Reddit", title="[Hiring] reels editor", url="https://x/1", matched=["reels"], kind="auftrag"),
             trends.TrendItem(source="HN", title="Unrelated", url="https://x/2")]
    text = ideas._prompt({}, items)
    assert "https://x/1" in text and "Unrelated" not in text and "viele Anfragen" in text


def test_real_leads_always_first_with_ai(fake_ollama, cfg):
    lead = trends.TrendItem(source="Reddit r/forhire", title="[Hiring] Video editor for reels",
                            url="https://reddit.com/lead1")
    scored = trends.score([lead], cfg["trends"]["keywords"])
    fake_ollama["answer"] = {"weekly_focus": "f", "ideas": [{
        "title": f"KI-Idee {n}", "why_now": "w", "action_steps": ["a"], "channel": "c",
        "effort": "niedrig", "revenue_potential": "hoch"} for n in range(8)]}
    result, _ = ideas.build_ideas(cfg, scored)
    assert result["ideas"][0]["title"].startswith("Auftrag prüfen") and len(result["ideas"]) == 8


# --------------------------------------------------------------------------- #
# Auftrags-Wächter
# --------------------------------------------------------------------------- #

from datetime import datetime as _dt

from goldbot import leads, notify


def _lead(n, title="[Hiring] Video editor for TikTok reels"):
    return trends.TrendItem(source="Reddit r/forhire", title=title, url=f"https://reddit.com/p/{n}")


@pytest.fixture
def lead_cfg(cfg, tmp_path, monkeypatch):
    cfg["output_dir"] = str(tmp_path / "reports")
    cfg["leads"] = {"state_file": str(tmp_path / "state.json")}
    sent = []
    monkeypatch.setattr(notify, "send", lambda c, t, b, d="", open_path=None: sent.append((t, b)) or ["test"])
    cfg["_sent"] = sent
    return cfg


def test_phrase_without_tag_is_a_lead(cfg):
    item = trends.score([trends.TrendItem(source="Reddit r/HireAnEditor",
                                          title="Looking for a video editor for YouTube Shorts")],
                        cfg["trends"]["keywords"])[0]
    assert item.kind == "auftrag"


def test_for_hire_still_competitor_even_with_phrase(cfg):
    item = trends.score([trends.TrendItem(source="Reddit", title="[For Hire] Need a video editor? I edit reels")],
                        cfg["trends"]["keywords"])[0]
    assert item.kind == "konkurrenz"


def test_leads_reported_only_once(lead_cfg):
    items = trends.score([_lead(1), _lead(2)], lead_cfg["trends"]["keywords"])
    first = leads.check(lead_cfg, items, now=_dt(2026, 11, 3, 8, 0))
    second = leads.check(lead_cfg, items, now=_dt(2026, 11, 3, 9, 0))
    assert len(first) == 2 and second == []
    assert len(lead_cfg["_sent"]) == 1 and "2 neue Aufträge" in lead_cfg["_sent"][0][0]
    md = (Path(lead_cfg["output_dir"]) / "auftraege" / "2026-11-03.md").read_text()
    assert md.count("**Antwort-Entwurf:**") == 2 and "[PORTFOLIO-LINK]" in md


def test_unmatched_or_competitor_posts_are_not_leads(lead_cfg):
    items = trends.score([_lead(1, "[Hiring] Bookkeeper"), _lead(2, "[For Hire] reels editor")],
                         lead_cfg["trends"]["keywords"])
    assert leads.check(lead_cfg, items, now=_dt(2026, 11, 3)) == []


def test_old_state_entries_are_pruned(tmp_path):
    path = tmp_path / "s.json"
    leads.save_state(path, {"old": "2026-09-01T00:00:00", "new": "2026-11-02T00:00:00"}, _dt(2026, 11, 3))
    assert set(leads.load_state(path)) == {"new"}


def test_ai_reply_drafts_used_when_valid(fake_ollama, lead_cfg):
    items = trends.score([_lead(7)], lead_cfg["trends"]["keywords"])
    fake_ollama["answer"] = {"replies": [{"url": "https://reddit.com/p/7",
                                          "reply": "Hi! I'd cut your reels with tight hooks. Samples: [PORTFOLIO-LINK]. Deadline?"}]}
    drafts = leads.draft_replies(lead_cfg, items)
    assert drafts["https://reddit.com/p/7"].startswith("Hi! I'd cut")


def test_lead_check_only_fetches_reddit(lead_cfg):
    fetched = []
    class F:
        def get(self, url):
            fetched.append(url)
            return None
    leads.check(lead_cfg, fetcher=F(), now=_dt(2026, 11, 3))
    assert fetched and all("reddit.com" in u for u in fetched)


def test_notify_without_channels_is_quiet(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "linux")
    assert notify.send({"notify": {"windows": True, "telegram_chat_id": ""}}, "t", "b") == []


def test_single_lead_title(lead_cfg):
    leads.check(lead_cfg, trends.score([_lead(9)], lead_cfg["trends"]["keywords"]), now=_dt(2026, 11, 3))
    assert lead_cfg["_sent"][0][0] == "Goldbot: 1 neuer Auftrag"


def test_gig_description_keeps_line_breaks(cfg):
    pack, _, _ = profile.build_profile(cfg)
    desc = pack["gigs"][0]["description"]
    assert "\n- " in desc and "\n\n" in desc and len(desc) <= 1200


def test_multiline_cut_respects_limit():
    text = "Intro line\n\n" + "\n".join(f"- point number {i} with some words" for i in range(80))
    out = profile._cut(text, 300, multiline=True)
    assert len(out) <= 300 and out.startswith("Intro line\n\n- point")


# Echte Titel aus r/HireAnEditor, r/VideoEditingRequests, r/slavelabour (03.11.2026)
JOB_CASES = [
    ("HireAnEditor", "Need a video editor for a features/trailer video for an app im making", True),
    ("HireAnEditor", "LOOKING FOR UGC CREATORS", True),
    ("VideoEditingRequests", "_HIRING - AI VIDEO CREATOR (WFH) - NORMAL AI TOOLS - 60K/MONTH_", True),
    ("HireAnEditor", "[HIRING] LONG FORM VIDEOGAME EDITOR WITH GOOD COMEDY TIMING $50 BUDGET", True),
    ("HireAnEditor", "Need someone to edit my videos", True),
    ("forhire", "[Hiring] Video Editor to Record and Create a 20-40 Second Windows Software Showcase", True),
    ("HireAnEditor", "Hey I am a video editor searching for clients", False),
    ("HireAnEditor", "For hire", False),
    ("HireAnEditor", "Editor de vídeo disponível", False),
    ("HireAnEditor", "Creo videos (cortos, reels, etc)", False),
    ("HireAnEditor", "[FOR HIRE] Freelance Video Editor | Shorts, TikTok & Reels", False),
    ("VideoEditingRequests", "[HOBBY] LOOKING FOR ADOBE PREMIERE PRO EDITORS FOR SHORT FILM.", False),
    ("NewTubers", "Need feedback on my youtube video", False),
    ("NewTubers", "Looking for advice on growing my TikTok", False),
    ("VideoEditing", "Need help, my Premiere export of shorts is laggy", False),
    ("HireAnEditor", "Video editor available - need a YouTube editor? DM me", False),
    ("NewTubers", "Looking for a video editor for my channel", False),
    ("slavelabour", "[Offer] Reliable, affordable VA / data entry / chat support, $3-4 an hour", False),
    # Review 2026-11-03: Kunden, die "DM me" / "I'm a creator" schreiben, sind Aufträge
    ("HireAnEditor", "[Hiring] Reels editor, DM me with your portfolio", True),
    ("HireAnEditor", "[HIRING] I'm a fitness creator, need a shorts editor", True),
    ("HireAnEditor", "I'm a content creator looking for a reels editor", True),
    ("HireAnEditor", "Need video editor ASAP, DM me", True),
    # Themenwörter im Titel sind keine Frage, ein Betrag schlägt "revenue share"
    ("HireAnEditor", "[Hiring] Video editor for a cooking tips channel", True),
    ("HireAnEditor", "[Hiring] Editor for How to videos on YouTube", True),
    ("HireAnEditor", "[Hiring] Shorts editor, $500/month + revenue share", True),
    ("HireAnEditor", "Hiring video editor - not for free, $30 per video", True),
    # Aufträge ohne Tag
    ("HireAnEditor", "Hiring: YouTube video editor", True),
    ("HireAnEditor", "Video editor needed for weekly YouTube videos", True),
    ("HireAnEditor", "Editor wanted for gaming channel", True),
    ("HireAnEditor", "Looking for someone to edit my YouTube videos", True),
    ("HireAnEditor", "Need help editing my videos", True),
    # Jobsuchende sind keine Aufträge
    ("HireAnEditor", "Looking for a job as a video editor", False),
    ("HireAnEditor", "Need work - video editor with 3 years experience", False),
    ("HireAnEditor", "Need a video editor? I'm your guy", False),
    ("HireAnEditor", "Looking for creators who need an editor", False),
    ("HireAnEditor", "[Hiring] Unpaid editor for my channel", False),
    ("HireAnEditor", "[HIRING] How do I find a good editor?", False),
]


@pytest.mark.parametrize("sub,title,is_job", JOB_CASES)
def test_job_detection_on_real_titles(cfg, sub, title, is_job):
    item = trends.TrendItem(source="Reddit r/forhire+HireAnEditor", title=title, category=sub)
    assert (trends.score([item], cfg["trends"]["keywords"])[0].kind == "auftrag") == is_job


def test_subreddit_is_parsed_from_atom_category():
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Need a video editor</title>'
           '<category term="HireAnEditor" label="r/HireAnEditor"/><link href="https://r/1"/></entry></feed>')
    assert trends.parse_feed(xml, "Reddit")[0].category == "HireAnEditor"


def test_lead_needs_video_connection(lead_cfg):
    items = trends.score([_lead(1, "[Hiring] AI chatbot developer"), _lead(2, "[Hiring] AI video editor")],
                         lead_cfg["trends"]["keywords"])
    new = leads.check(lead_cfg, items, now=_dt(2026, 11, 3))
    assert [i.title for i in new] == ["[Hiring] AI video editor"]


def test_single_instance_lock(tmp_path):
    from goldbot.lock import AlreadyRunning, single_instance
    with single_instance(tmp_path / "x.lock"):
        with pytest.raises(AlreadyRunning):
            # zweite Sperre über einen anderen Prozess simulieren
            import subprocess, sys
            code = ("import sys; sys.path.insert(0, %r); from goldbot.lock import single_instance, AlreadyRunning\n"
                    "try:\n single_instance(%r).__enter__()\nexcept AlreadyRunning:\n sys.exit(3)\n")
            rc = subprocess.run([sys.executable, "-c", code % (str(Path(__file__).parent.parent), str(tmp_path / "x.lock"))]).returncode
            if rc == 3:
                raise AlreadyRunning("x")
    with single_instance(tmp_path / "x.lock"):  # nach Freigabe wieder nutzbar
        pass


def test_lead_check_failure_keeps_report(cfg, tmp_path, monkeypatch):
    from goldbot import __main__ as cli
    cfg["output_dir"] = str(tmp_path)
    monkeypatch.setattr(cli.trends_mod, "scan", lambda c: ([], []))
    def boom(*a, **k):
        raise OSError("Datei gesperrt")
    monkeypatch.setattr(cli.leads_mod, "check", boom)
    cli.run(cfg, "trends")
    assert list(tmp_path.glob("*/bericht.md"))



@pytest.mark.parametrize("reply", [
    "I specialize in AI-assisted editing for viral Shorts. See [PORTFOLIO-LINK]. Deadline?",
    "I create high-quality Reels for various industries. Portfolio: [PORTFOLIO-LINK]. Timeline?",
    "I work with creators on UGC content. [PORTFOLIO-LINK]. What do you need?",
    "I can help! Samples: https://example.com Deadline?",
])
def test_ai_drafts_with_claims_fall_back_to_template(fake_ollama, lead_cfg, reply):
    items = trends.score([_lead(5)], lead_cfg["trends"]["keywords"])
    fake_ollama["answer"] = {"replies": [{"url": "https://reddit.com/p/5", "reply": reply}]}
    draft = leads.draft_replies(lead_cfg, items)["https://reddit.com/p/5"]
    assert draft == leads.template_reply(items[0], lead_cfg)


def test_reddit_source_shows_real_subreddit(cfg):
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>[Hiring] reels editor</title>'
           '<category term="HireAnEditor"/><link href="https://r/1"/></entry></feed>')
    class R:
        text = xml
        content = xml.encode("utf-8")
    class F:
        def get(self, url):
            return R() if "reddit" in url else None
    items, _ = trends.scan(cfg, F(), only=("reddit",))
    assert items[0].source == "Reddit r/HireAnEditor" and items[0].kind == "auftrag"



def test_missing_placeholder_is_added_not_rejected(fake_ollama, lead_cfg):
    items = trends.score([_lead(6)], lead_cfg["trends"]["keywords"])
    fake_ollama["answer"] = {"replies": [{"url": "https://reddit.com/p/6", "reply":
        "I'd cut fast-paced promotional reels for your studio. What's the expected length of each reel?"}]}
    draft = leads.draft_replies(lead_cfg, items)["https://reddit.com/p/6"]
    assert draft == ("I'd cut fast-paced promotional reels for your studio. Samples: [PORTFOLIO-LINK]. "
                     "What's the expected length of each reel?")


def test_insert_helper_page(cfg, tmp_path):
    from goldbot import helper
    pack, _, _ = profile.build_profile(cfg)
    page = helper.write(tmp_path / "e.html", pack, pack.get("languages"))
    text = page.read_text()
    assert text.count("data-copy=") >= 3 + 3 * 5  # Profil + je Gig Titel/Kategorie/Tags/Beschreibung/FAQ
    import html as _hh
    assert _hh.escape(pack["one_liner"]) in text and "seller_onboarding" in text
    import html as _h, json as _j, re as _re
    first = _re.search(r'data-copy="([^"]*)"', text).group(1)
    assert _j.loads(_h.unescape(first)) == pack["one_liner"]


# --------------------------------------------------------------------------- #
# Muster-Videos
# --------------------------------------------------------------------------- #

from goldbot import demo as demo_mod


def test_demo_word_times_follow_voice_and_numbers():
    marks = [(0.0, 0.4, "Gold"), (0.4, 0.9, "passt"), (0.9, 2.0, "zweiundzwanzig"), (2.0, 2.6, "Meter")]
    words = demo_mod.word_times("Gold passt 22 Meter", marks, 2.6)
    assert [w[2] for w in words] == ["Gold", "passt", "22", "Meter"]
    starts = [w[0] for w in words]
    assert starts == sorted(starts) and starts[0] == 0.0 and words[-1][1] == 2.6


def test_demo_ass_has_karaoke_hook_cta_and_footer():
    d = next(x for x in demo_mod.DEMOS if x["name"] == "finanzen_de")
    scenes, start = [], 0.0
    for i, (kind, text) in enumerate([("hook", d["hook"])] + [("line", t) for t in d["lines"]] + [("cta", d["cta"])]):
        scenes.append({"kind": kind, "text": text, "index": i, "start": start, "dur": 3.0,
                       "words": demo_mod.word_times(text, None, 2.5)})
        start += 3.0
    ass = demo_mod.build_ass(d, scenes, "DejaVu Sans", start)
    assert "50/30/20-Regel" in ass and "Rücklagen." in ass and d["footer"] in ass
    assert ass.count("Style: Cap,") == 1 and "\\1c&H0073BF1D" in ass  # Akzent 0x1dbf73 als BGR
    assert d["cta"] in ass and "1/3" not in ass and d["chip"] not in ass  # wenig Text
    assert ass.count(",Cap,,") >= 12  # höchstens 2 Wörter auf einmal
    foot = next(l for l in ass.splitlines() if ",Foot," in l)
    assert foot.startswith("Dialogue: 1,0:00:12.00")  # Hinweis erst in der letzten Szene


def test_pixabay_prefers_vertical_full_hd():
    vids = {"large": {"url": "l", "width": 2160, "height": 3840, "size": 9},
            "medium": {"url": "m", "width": 1080, "height": 1920, "size": 5},
            "small": {"url": "s", "width": 720, "height": 1280, "size": 2}}
    assert demo_mod._pick_size(vids)["url"] == "m"
    assert demo_mod._pick_size({"large": {"url": "q", "width": 3840, "height": 2160}})["url"] == "q"


def test_pixabay_key_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nPIXABAY_API_KEY=abc123\n", encoding="utf-8")
    assert demo_mod.pixabay_key({"muster": {"pixabay_env": str(env)}}) == "abc123"


def test_footage_cache_and_no_key_offline(tmp_path):
    f = demo_mod.Footage(tmp_path, None)
    assert f.search("gold") == [] and f.pick("gold", 3, set()) is None


def test_demo_contents_are_marked_as_demo():
    for d in demo_mod.DEMOS:
        assert ("Beispiel" in d["footer"] or "Sample" in d["footer"]) and \
            ("beratung" in d["footer"].lower() or "advice" in d["footer"])


@pytest.mark.skipif(not demo_mod.find_ffmpeg() or not demo_mod.find_font(), reason="ffmpeg/Schrift fehlt")
def test_demo_render_real_video(tmp_path, monkeypatch):
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    monkeypatch.setattr(demo_mod, "pixabay_key", lambda cfg=None: None)  # offline: Farbverlauf
    out = demo_mod.render_all(tmp_path, ["krypto_de"], voice=False)
    assert out and out[0].stat().st_size > 50_000
    assert abs(demo_mod.duration(out[0], demo_mod.find_ffmpeg()) - 5 * 2.6) < 8


def test_file_log_written(tmp_path):
    import logging as _l
    from goldbot import __main__ as cli
    root = _l.getLogger()
    before = list(root.handlers)
    try:
        cli.setup_file_log(tmp_path / "goldbot.log")
        _l.getLogger("goldbot").warning("Testmeldung äöü")
        for h in root.handlers:
            h.flush()
        assert "Testmeldung äöü" in (tmp_path / "goldbot.log").read_text(encoding="utf-8")
    finally:
        for h in root.handlers[len(before):]:
            h.close()
        root.handlers[:] = before


def test_windows_scripts_use_crlf():
    root = Path(__file__).parent.parent / "windows"
    for f in list(root.glob("*.bat")) + list(root.glob("*.ps1")):
        data = f.read_bytes()
        assert b"\n" in data and data.count(b"\r\n") == data.count(b"\n"), f"{f.name} braucht CRLF"


# --------------------------------------------------------------------------- #
# Review 2026-11-03
# --------------------------------------------------------------------------- #

def test_empty_config_key_keeps_default(tmp_path):
    user = tmp_path / "config.yaml"
    user.write_text("trends:\n  keywords:\n  #  - gold\nllm:\n", encoding="utf-8")
    c = load_config(user)
    assert c["trends"]["keywords"] and c["llm"]["provider"]


def test_broken_config_is_logged(tmp_path, monkeypatch):
    from goldbot import __main__ as cli, config as config_mod
    bad = tmp_path / "config.yaml"
    bad.write_text("profile:\n\tusername: x\n", encoding="utf-8")
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    assert cli.main(["-c", str(bad), "trends"]) == 1
    assert "kein gültiges YAML" in (tmp_path / "reports" / "goldbot.log").read_text(encoding="utf-8")


def test_ansi_config_is_read(tmp_path):
    user = tmp_path / "config.yaml"
    user.write_bytes("profile:\n  country: Österreich\n".encode("cp1252"))
    assert load_config(user)["profile"]["country"] == "Österreich"


def test_reddit_posts_with_same_title_are_kept():
    a = trends.TrendItem(source="Reddit r/HireAnEditor", title="[Hiring] Video Editor", url="u1")
    b = trends.TrendItem(source="Reddit r/HireAnEditor", title="[Hiring] Video editor", url="u2")
    assert len(trends.dedupe([a, b])) == 2


def test_feed_bytes_use_xml_encoding():
    xml = ('<?xml version="1.0" encoding="utf-8"?><rss><channel><item><title>Goldpreis Österreich</title>'
           '</item></channel></rss>').encode("utf-8")
    assert trends.parse_feed(xml, "x")[0].title == "Goldpreis Österreich"


def test_atom_alternate_link_wins():
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>x</title>'
           '<link rel="replies" href="https://a/comments"/><link rel="alternate" href="https://a/post"/></entry></feed>')
    assert trends.parse_feed(xml, "x")[0].url == "https://a/post"


def test_fetcher_retries_network_errors_and_5xx():
    import requests as rq

    class R:
        def __init__(self, code): self.status_code, self.headers = code, {}

    class S:
        headers = {}
        calls = 0
        def get(self, url, timeout):
            S.calls += 1
            if S.calls == 1:
                raise rq.ConnectionError("weg")
            return R(503) if S.calls == 2 else R(200)

    f = trends.Fetcher(delay=0, session=S())
    f.sleep = lambda s: None
    assert f.get("https://x").status_code == 200 and S.calls == 3


def test_empty_feed_counts_as_failed_source(cfg):
    class R:
        content = b"<rss><channel></channel></rss>"
    class F:
        def get(self, url): return R()
    _, errors = trends.collect(cfg, F(), only=("reddit",))
    assert errors and errors[0].startswith("Reddit")


def test_claim_check_catches_more_invented_experience(cfg):
    from goldbot import leads as leads_mod
    for bad in ["With 5 years editing shorts I can help", "I'm an expert in reels",
                "Ich habe bereits viele Reels geschnitten", "See mywork.com", "Call me +43 660 1234567"]:
        assert leads_mod.CLAIM_RE.search(bad), bad
    assert not leads_mod.CLAIM_RE.search(leads_mod.template_reply(_lead(1), cfg))


def test_state_write_is_atomic_and_corrupt_file_is_kept(tmp_path):
    from datetime import datetime
    from goldbot import leads as leads_mod
    path = tmp_path / ".gesehen.json"
    leads_mod.save_state(path, {"u": "2026-11-03T10:00:00"}, datetime(2026, 11, 3))
    assert leads_mod.load_state(path) == {"u": "2026-11-03T10:00:00"}
    assert not (tmp_path / ".gesehen.json.tmp").exists()
    path.write_text('{"u": "2026', encoding="utf-8")
    assert leads_mod.load_state(path) == {}
    assert (tmp_path / ".gesehen.json.defekt").exists()


def test_lead_ideas_need_video_connection():
    items = [trends.TrendItem(source="Reddit r/forhire", title="[Hiring] AI chatbot developer", url="a",
                              kind="auftrag", matched=["ai"]),
             trends.TrendItem(source="Reddit r/forhire", title="[Hiring] AI video editor", url="b",
                              kind="auftrag", matched=["ai"])]
    assert [i["url"] for i in ideas.lead_ideas(items)] == ["b"]


def test_package_descriptions_fit_fiverr(cfg):
    cfg["llm"]["provider"] = "aus"
    pack, _, _ = profile.build_profile(cfg)
    for gig in pack["gigs"]:
        for p in gig["packages"]:
            assert 0 < len(p["description"]) <= profile.LIMITS["package_desc"]


def test_helper_title_without_i_will_and_single_tags(cfg):
    from goldbot import helper
    cfg["llm"]["provider"] = "aus"
    pack, _, _ = profile.build_profile(cfg)
    page = helper.build_page(pack)
    assert "Tag 5" in page and "Paket" in page
    title = pack["gigs"][0]["title"]
    assert title.startswith("I will") and f"<pre>{title[7:]}</pre>" in page


def test_degraded_full_run_is_retried_soon(cfg, tmp_path, monkeypatch):
    from goldbot import __main__ as cli
    cfg["output_dir"] = str(tmp_path)
    monkeypatch.setattr(cli.trends_mod, "scan", lambda c: ([], ["Reddit"]))
    monkeypatch.setattr(cli.leads_mod, "check", lambda c, items=None: [])
    assert cli.run(cfg, "trends") is False


def test_pixabay_relevance_needs_all_query_words():
    flowers = {"tags": "flowers, yellow, gold, nature"}
    bars = {"tags": "gold bars, bullion, wealth"}
    assert demo_mod.relevance(flowers, "gold bars")[0] is False
    ok, bonus = demo_mod.relevance(bars, "gold bars")
    assert ok and bonus == 3
    assert demo_mod.relevance({"tags": "gold bar, finance"}, "gold bars")[0]
    assert demo_mod.relevance({"tags": "fingerprint, green screen, scan"}, "fingerprint")[0] is False


def test_helper_next_button_progress_and_videos(cfg, tmp_path):
    from goldbot import helper
    cfg["llm"]["provider"] = "aus"
    pack, _, _ = profile.build_profile(cfg)
    (tmp_path / "gold_de.mp4").write_bytes(b"x")
    page = helper.build_page(pack, None, tmp_path)
    assert 'id="next"' in page and "localStorage" in page and 'data-key="Einzeiler"' in page
    assert "gold_de.mp4" in page and "finance_en.mp4" not in page  # nur vorhandene Videos
    assert 'f.dataset.key=i+"·"+f.dataset.key' in page  # Gig-Felder gleichen Namens getrennt abhaken


def test_cover_headline_short_and_without_i_will():
    rows = demo_mod.cover_headline("I will create faceless gold and finance shorts in german or english")
    assert rows[0].startswith("Create") and len(rows) <= 2 and all(len(r) <= 32 for r in rows)


@pytest.mark.skipif(not demo_mod.find_ffmpeg() or not demo_mod.find_font(), reason="ffmpeg/Schrift fehlt")
def test_gig_cover_is_fiverr_size(tmp_path):
    import subprocess as sp
    ff = demo_mod.find_ffmpeg()
    v = tmp_path / "gold_de.mp4"
    sp.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:d=16", "-pix_fmt", "yuv420p", str(v)], check=True)
    out = demo_mod.render_covers(tmp_path, [{"title": "I will edit short form reels in german or english"}],
                                 [["gold_de", "gold_en"]])
    assert out and out[0].name == "gig1_titelbild.jpg"
    probe = sp.run([demo_mod._ffprobe(ff), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                    str(out[0])], capture_output=True, text=True).stdout.strip()
    assert probe == "1280,769"


def test_old_leads_are_skipped():
    from datetime import datetime, timezone
    from goldbot import leads as leads_mod
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    fresh = trends.TrendItem(source="Reddit r/forhire", title="[Hiring] Video editor", url="a",
                             kind="auftrag", matched=["video"], published="2026-11-03T08:00:00+00:00")
    old = trends.TrendItem(source="Reddit r/forhire", title="[Hiring] Video editor", url="b",
                           kind="auftrag", matched=["video"], published="2026-10-28T08:00:00+00:00")
    rss = trends.TrendItem(source="Reddit r/forhire", title="[Hiring] Reels editor", url="c",
                           kind="auftrag", matched=["video"], published="Tue, 03 Nov 2026 10:00:00 +0000")
    assert [i.url for i in leads_mod.find_new([fresh, old, rss], {}, now=now)] == ["a", "c"]


def test_toast_opens_leads_file(monkeypatch, tmp_path):
    import sys as _sys
    seen = {}
    monkeypatch.setattr(_sys, "platform", "win32")
    monkeypatch.setattr(notify.subprocess, "run", lambda *a, **k: seen.update(k["env"]))
    assert notify.windows_toast("t", "b", tmp_path / "x.md")
    assert seen["GOLDBOT_TOAST_LAUNCH"].startswith("file://") and "launch" in notify._TOAST_SCRIPT


def test_dotenv_loads_without_overriding(tmp_path, monkeypatch):
    from goldbot.config import load_dotenv
    import os
    env = tmp_path / ".env"
    env.write_text("# x\nGOLDBOT_TEST_A=1\nGOLDBOT_TEST_B=neu\nGOLDBOT_TEST_C=\n", encoding="utf-8")
    monkeypatch.setenv("GOLDBOT_TEST_B", "alt")
    monkeypatch.delenv("GOLDBOT_TEST_A", raising=False)
    assert load_dotenv(env) == ["GOLDBOT_TEST_A"]
    assert os.environ["GOLDBOT_TEST_A"] == "1" and os.environ["GOLDBOT_TEST_B"] == "alt"
    monkeypatch.delenv("GOLDBOT_TEST_A")


def test_env_example_has_no_values():
    from goldbot.config import ROOT
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert all(l.endswith("=") for l in lines if l and not l.startswith("#"))



# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #

def test_simulation_learns_reddit_rate_without_backlog():
    from goldbot import simulation
    state = {"a": "2026-11-03T07:00:00", "b": "2026-11-03T07:00:00",
             "c": "2026-11-03T13:00:00", "d": "2026-11-03T19:00:00"}
    rate, count, hours = simulation.learn_reddit_rate(state)
    assert count == 2 and hours == 12 and rate == 4.0
    assert simulation.learn_reddit_rate({"a": "2026-11-03T07:00:00"})[0] is None


def test_simulation_observed_numbers_shift_beta():
    from goldbot import simulation
    p = {k: (list(v) if isinstance(v, list) else v) for k, v in simulation.DEFAULTS.items()}
    before = simulation.beta_mean(p["klickrate"])
    notes = simulation.apply_observed(p, {"tage": 14, "gigs": 3, "impressionen": 4200, "klicks": 210})
    assert simulation.beta_mean(p["klickrate"]) > before  # 5 % beobachtet > 1,5 % Annahme
    assert p["impressionen_pro_tag"] == 100 / p["start_schub"]
    assert notes


def test_simulation_report_runs(tmp_path):
    from goldbot import simulation
    cfg = {"output_dir": str(tmp_path), "leads": {"state_file": str(tmp_path / "s.json")},
           "simulation": {"laeufe": 100}}
    path, data = simulation.write(cfg)
    text = path.read_text(encoding="utf-8")
    assert "Auf einen Blick" in text and "Was wäre, wenn" in text
    base = data["base"]
    assert base["n"] == 100 and 0 <= base["mind_ein_auftrag"] <= 1
    assert base["p"]["netto"][0] <= base["p"]["netto"][1] <= base["p"]["netto"][2]
    # ohne Reddit-Antworten gibt es keine Reddit-Aufträge
    _, data0 = simulation.report(cfg, {"antworten_pro_tag": 0})
    assert data0["base"]["mittel"]["reddit"] == 0
