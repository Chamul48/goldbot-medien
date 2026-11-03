"""Bringt einen Commit aus GitHub sicher auf den PC, ohne lokale Änderungen zu überschreiben.

Aufruf (im Projektordner auf dem PC):
    python pc_sync.py <commit>             Commit einspielen
    python pc_sync.py --init <commit>      einmalig: festhalten, dass der Ordner gerade auf <commit> steht

Regeln:
- Eine Datei wird nur überschrieben, wenn sie seit dem letzten Abgleich lokal NICHT geändert wurde
  (Vergleich mit den Prüfsummen in .sync_manifest.json).
- Lokal geänderte oder unbekannte Dateien werden übersprungen und gemeldet – nichts geht verloren.
- .env, .venv, autopilot/state.json und Sicherungen/Berichte auf dem PC werden nie angefasst.
Nur Standardbibliothek, läuft mit jedem Python ab 3.9.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "Chamul48/goldbot-medien"
HIER = Path(__file__).resolve().parent
MANIFEST = HIER / ".sync_manifest.json"
NIE_GENAU = {".env", ".env.vorher", "autopilot/state.json", "autopilot/ESCALATIONS.md", ".sync_manifest.json"}
NIE_PRAEFIX = (".venv/", "autopilot/backup-", "autopilot/reports/")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def geschuetzt(rel: str) -> bool:
    return rel in NIE_GENAU or rel.startswith(NIE_PRAEFIX)


def commit_dateien(commit: str) -> dict[str, bytes]:
    url = f"https://codeload.github.com/{REPO}/zip/{commit}"
    with urllib.request.urlopen(url, timeout=60) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    root = z.namelist()[0]
    return {n[len(root):]: z.read(n) for n in z.namelist() if not n.endswith("/") and n[len(root):]}


def plan(neu: dict[str, bytes], lokal: dict[str, bytes | None], manifest: dict[str, str]) -> dict[str, list[str]]:
    """Entscheidet je Datei: schreiben, gleich, oder überspringen (lokal geändert)."""
    out: dict[str, list[str]] = {"schreiben": [], "gleich": [], "lokal_geaendert": [], "geschuetzt": []}
    for rel, data in sorted(neu.items()):
        if geschuetzt(rel):
            out["geschuetzt"].append(rel)
            continue
        cur = lokal.get(rel)
        if cur is None:
            out["schreiben"].append(rel)
        elif sha(cur) == sha(data):
            out["gleich"].append(rel)
        elif manifest.get(rel) == sha(cur):
            out["schreiben"].append(rel)  # lokal unverändert seit letztem Abgleich
        else:
            out["lokal_geaendert"].append(rel)
    return out


def main(argv: list[str]) -> int:
    init = "--init" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    commit = args[0]
    neu = commit_dateien(commit)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"files": {}}
    if init:
        manifest = {"commit": commit, "files": {rel: sha(d) for rel, d in neu.items() if not geschuetzt(rel)}}
        MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"Ausgangsstand festgehalten: {commit} ({len(manifest['files'])} Dateien).")
        return 0

    lokal = {rel: ((HIER / rel).read_bytes() if (HIER / rel).is_file() else None) for rel in neu}
    p = plan(neu, lokal, manifest["files"])
    for rel in p["schreiben"]:
        ziel = HIER / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(neu[rel])
    for rel in p["schreiben"] + p["gleich"]:
        manifest["files"][rel] = sha(neu[rel])
    manifest["commit"] = commit
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    print(f"Commit {commit[:10]}: {len(p['schreiben'])} aktualisiert, {len(p['gleich'])} schon aktuell.")
    if p["lokal_geaendert"]:
        print("NICHT überschrieben, weil auf dem PC geändert (bitte prüfen und ggf. ins Repo übernehmen):")
        for rel in p["lokal_geaendert"]:
            print("  -", rel)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
