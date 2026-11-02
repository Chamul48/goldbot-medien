"""Autopilot: one unattended run that looks after the store.

Before anything changes, the run reads the whole shop and stores the original
values in autopilot/backup-<date>.json (see audit.py), so every text, SEO and
alt-text change can be undone with `--restore`. Safe changes (texts, tags, SEO,
alt texts, collections, media uploads) are made directly. Anything risky
(prices, status changes, raw mutations) is never executed; it becomes an
escalation in the report so the owner decides. The run writes
autopilot/reports/<date>.md and, if the owner is needed, autopilot/ESCALATIONS.md.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

from . import audit
from .agent import ShopifyAgent
from .shopify import ShopifyClient, ShopifyError
from .tools import Toolbox

ALLOWED_ALONE = {"content", "media"}
MAX_CONTENT_EDITS = 10
MAX_FINDINGS_IN_TASK = 40

AUTOPILOT_TASK = f"""\
Autopilot run, {{date}}. The owner is not watching; work on your own and \
hand anything that needs a human to the escalate tool.

1. Media: call list_local_media. Each folder in social/ is one post (usually \
video.mp4 + cover.jpg). Upload every file with already_uploaded=false. If one \
product clearly matches the post, attach it; otherwise upload without a \
product and escalate the question which product it belongs to.
2. Catalog: search active and draft products. For at most {MAX_CONTENT_EDITS} \
products with a missing or very thin description, write a good German product \
description (HTML, factual, no invented specs such as weight or purity you \
did not see in the data) and sensible tags. If facts are missing, escalate \
instead of guessing.
3. Orders: list recent orders. Do not change orders. Escalate paid orders \
that are still unfulfilled after 2 days, and anything unusual.
4. Polish (only items from the audit list below, at most {MAX_CONTENT_EDITS} \
products per run, highest priority first): missing SEO titles/descriptions \
(update_product, update_collection), alt texts that describe what is visible \
(set_media_alt), collection descriptions (update_collection). If there are no collections at all, \
propose at most 3 smart collections by tag with create_collection (they stay \
unpublished). Read each product with get_product before you write.
5. Prices, status changes (publish/archive), legal texts (Impressum, AGB, \
Widerruf, Datenschutz), theme changes and deletions are never yours to decide: \
escalate them with your recommendation.

Audit findings the owner allowed you to fix alone:
{{findings}}

Finish with a short German report: what you changed, what you escalated, and \
anything that blocked you.
"""


def autopilot_policy(toolbox_ref: list[Toolbox], allowed: set[str] = ALLOWED_ALONE):
    def confirm(kind: str, summary: str) -> bool:
        if kind in allowed:
            return True
        toolbox_ref[0].escalations.append(
            {"topic": f"Needs approval ({kind})", "details": summary}
        )
        return False

    return confirm


def run(media_dir: Path, out_dir: Path) -> int:
    date = datetime.date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        shop = ShopifyClient()
    except ShopifyError as exc:
        print(exc, file=sys.stderr)
        return 2

    # Back up first; without a complete backup, texts are not touched.
    report_path, backup_path, found = audit.run_audit(shop, out_dir)
    snap_errors = [f for f in found if f["area"] == "Technik"]
    allowed = ALLOWED_ALONE if not snap_errors else {"media"}

    ref: list[Toolbox] = []
    toolbox = Toolbox(shop, media_dir, autopilot_policy(ref, allowed), state_file=out_dir / "state.json")
    ref.append(toolbox)
    if snap_errors:
        toolbox.escalations.append({
            "topic": "Shop konnte nicht vollständig gelesen werden",
            "details": "Ohne vollständige Sicherung ändert der Autopilot keine Texte.\n"
                       + "\n".join(f["text"] for f in snap_errors),
        })
    agent = ShopifyAgent(toolbox)

    todo = [f for f in found if f["who"] == "auto"][:MAX_FINDINGS_IN_TASK]
    todo_text = "\n".join(f"- P{f['prio']} [{f['area']}] {f['text']}" for f in todo) or "- (none)"
    summary = agent.send(AUTOPILOT_TASK.format(date=date, findings=todo_text))

    report = [f"# Autopilot {date}", "", summary or "(no summary)", "",
              f"Sicherung: `{backup_path.as_posix()}` · Kontrolle: `{report_path.as_posix()}`", ""]
    if toolbox.escalations:
        report += ["## Needs you", ""]
        for e in toolbox.escalations:
            report += [f"### {e['topic']}", "", e["details"], ""]
    reports = out_dir / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"{date}.md").write_text("\n".join(report))

    esc_file = out_dir / "ESCALATIONS.md"
    if toolbox.escalations:
        esc_file.write_text("\n".join(report))
    elif esc_file.exists():
        esc_file.unlink()

    print("\n".join(report))
    print(json.dumps({"escalations": len(toolbox.escalations)}), file=sys.stderr)
    return 0
