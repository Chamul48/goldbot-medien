"""Autopilot: one unattended run that looks after the store.

Safe changes (texts, tags, media uploads) are made directly. Anything risky
(prices, status changes, raw mutations) is never executed; it becomes an
escalation in the report so the owner decides. The run writes
autopilot/reports/<date>.md and, if the owner is needed, autopilot/ESCALATIONS.md.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

from .agent import ShopifyAgent
from .shopify import ShopifyClient, ShopifyError
from .tools import Toolbox

ALLOWED_ALONE = {"content", "media"}
MAX_CONTENT_EDITS = 10

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
4. Prices, status changes (publish/archive) and deletions are never yours to \
decide: escalate them with your recommendation.

Finish with a short German report: what you changed, what you escalated, and \
anything that blocked you.
"""


def autopilot_policy(toolbox_ref: list[Toolbox]):
    def confirm(kind: str, summary: str) -> bool:
        if kind in ALLOWED_ALONE:
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

    ref: list[Toolbox] = []
    toolbox = Toolbox(shop, media_dir, autopilot_policy(ref), state_file=out_dir / "state.json")
    ref.append(toolbox)
    agent = ShopifyAgent(toolbox)

    summary = agent.send(AUTOPILOT_TASK.format(date=date))

    report = [f"# Autopilot {date}", "", summary or "(no summary)", ""]
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
