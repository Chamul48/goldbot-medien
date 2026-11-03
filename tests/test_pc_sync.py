"""pc_sync must never overwrite files changed on the PC since the last sync."""

from pc_sync import geschuetzt, plan, sha


def test_unchanged_local_file_is_updated_changed_one_is_kept():
    neu = {"a.py": b"neu", "b.py": b"neu", "c.py": b"gleich", "d.py": b"neu"}
    lokal = {"a.py": b"alt", "b.py": b"lokal verbessert", "c.py": b"gleich", "d.py": None}
    manifest = {"a.py": sha(b"alt"), "b.py": sha(b"alt")}
    p = plan(neu, lokal, manifest)
    assert p["schreiben"] == ["a.py", "d.py"]
    assert p["lokal_geaendert"] == ["b.py"]
    assert p["gleich"] == ["c.py"]


def test_unknown_differing_file_is_not_overwritten():
    p = plan({"x.py": b"neu"}, {"x.py": b"unbekannt"}, {})
    assert p["lokal_geaendert"] == ["x.py"] and not p["schreiben"]


def test_secrets_and_pc_data_are_protected():
    for rel in (".env", "autopilot/state.json", "autopilot/backup-2026-11-03.json", "autopilot/reports/x.md"):
        assert geschuetzt(rel)
    assert not geschuetzt(".env.example") and not geschuetzt("autopilot/README.md")
    p = plan({".env": b"x", "autopilot/state.json": b"{}"}, {".env": None, "autopilot/state.json": None}, {})
    assert p["geschuetzt"] == [".env", "autopilot/state.json"] and not p["schreiben"]
