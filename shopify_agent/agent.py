"""Claude-powered Shopify agent: chat with your store from the terminal."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import anthropic

from .shopify import ShopifyClient, ShopifyError
from .tools import TOOLS, Toolbox

MODEL = os.environ.get("SHOPIFY_AGENT_MODEL", "claude-opus-5-5")
MAX_TOOL_ROUNDS = 25

SYSTEM_PROMPT = """\
You are the Shopify agent for a store that sells gold-themed products and \
publishes "Gold-Agent" videos and reels. You help the owner run the store: \
look up products and orders, improve titles and descriptions, \
and upload videos/images from the local media folder to Shopify and attach \
them to products.

How to work:
- Answer questions about store data only from tool results, never from memory.
- Look up IDs with a search or get tool before using them; never guess a gid.
- Before a change, read the current state so you can describe what changes. \
Write tools ask the owner for approval; if they decline, ask what they want instead.
- Use the graphql tool only when no dedicated tool fits.
- Texts must be factual: never invent specifications (weight, purity, \
dimensions, origin, certificates) that are not in the product data. Write in a \
calm, premium tone; no exaggerated claims, no fake scarcity.
- Prices, publishing/archiving, deletions and legal texts are the owner's \
decision: recommend them (escalate tool), never change them on your own.
- Use the escalate tool for decisions that belong to the owner.
- Reply in the language the owner writes in (often German). Keep replies short \
and concrete: what you found, what you changed, what is left.
"""


def ask_confirm(kind: str, summary: str) -> bool:
    print(f"\n\033[33m⚠ Approval needed:\033[0m\n{summary}")
    try:
        return input("Proceed? [y/N] ").strip().lower() in {"y", "yes", "j", "ja"}
    except EOFError:
        return False


class ShopifyAgent:
    def __init__(self, toolbox: Toolbox, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic()
        self.toolbox = toolbox
        # Append-only history: response.content is stored verbatim (thinking,
        # fallback and tool_use blocks included) and never edited afterwards.
        self.messages: list[dict[str, Any]] = []

    def _call(self) -> Any:
        return self.client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=self.messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            cache_control={"type": "ephemeral"},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    def send(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._call()
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue
            if response.stop_reason in ("refusal", "max_tokens"):
                # Every tool_use needs a tool_result, otherwise the next request fails (HTTP 400).
                self._close_open_tool_uses(response)
                if response.stop_reason == "refusal":
                    return "[The model declined this request.]"
                return _text(response) + "\n[Reply was cut off at max_tokens.]"

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                return _text(response)

            results = []
            for block in tool_uses:
                print(f"\033[2m→ {block.name}({_short(block.input)})\033[0m", file=sys.stderr)
                output, is_error = self.toolbox.run(block.name, dict(block.input))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output[:50_000],
                        "is_error": is_error,
                    }
                )
            # All results of one turn go back in a single user message.
            self.messages.append({"role": "user", "content": results})

        return "[Stopped: too many tool rounds in one turn.]"

    def _close_open_tool_uses(self, response: Any) -> None:
        open_ids = [b.id for b in response.content if b.type == "tool_use"]
        if open_ids:
            self.messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": i, "is_error": True,
                 "content": "Not executed: the reply was cut off or declined."}
                for i in open_ids
            ]})


def _text(response: Any) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def _short(args: Any, n: int = 120) -> str:
    s = str(args)
    return s if len(s) <= n else s[: n - 1] + "…"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chat with your Shopify store via Claude.")
    parser.add_argument("prompt", nargs="*", help="One-shot request; omit for interactive chat.")
    parser.add_argument("--media-dir", default=os.environ.get("MEDIA_DIR", "social"),
                        help="Folder with videos/images to upload (default: social/).")
    parser.add_argument("--yes", action="store_true",
                        help="Approve text and media changes without asking (prices, status and raw mutations still ask).")
    parser.add_argument("--autopilot", action="store_true",
                        help="Unattended run: safe changes only, everything else is escalated.")
    parser.add_argument("--out-dir", default="autopilot", help="Autopilot reports and state (default: autopilot/).")
    parser.add_argument("--audit", action="store_true",
                        help="Read-only check: back up all texts and write a prioritised report. Changes nothing.")
    parser.add_argument("--restore", metavar="BACKUP_JSON",
                        help="Write texts, SEO, alt texts and collection texts back from a backup file.")
    args = parser.parse_args(argv)

    if args.autopilot:
        from .autopilot import run
        return run(Path(args.media_dir), Path(args.out_dir))

    try:
        shop = ShopifyClient()
    except ShopifyError as exc:
        print(exc, file=sys.stderr)
        return 2

    # --yes covers only the reversible kinds; prices, status and raw mutations always ask.
    confirm = (lambda k, s: k in {"content", "media"} or ask_confirm(k, s)) if args.yes else ask_confirm

    if args.audit:
        from .audit import run_audit
        report_path, backup_path, found = run_audit(shop, Path(args.out_dir))
        print(report_path.read_text(encoding="utf-8"))
        print(f"\nBericht: {report_path}\nSicherung: {backup_path}", file=sys.stderr)
        return 0
    if args.restore:
        from .audit import restore
        for line in restore(shop, Path(args.restore), confirm) or ["Nichts zurückzusetzen."]:
            print(line)
        return 0
    agent = ShopifyAgent(Toolbox(shop, Path(args.media_dir), confirm, backup_dir=Path(args.out_dir),
                                 change_log=Path(args.out_dir)))

    if args.prompt:
        print(agent.send(" ".join(args.prompt)))
        return 0

    print("Shopify Agent — type your request, or 'exit' to quit.")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.lower() in {"exit", "quit", "q"}:
            return 0
        if not line:
            continue
        try:
            print("\n" + agent.send(line))
        except anthropic.RateLimitError:
            print("Rate limited by the Claude API — wait a moment and try again.")
        except anthropic.AuthenticationError:
            print("Claude API authentication failed — check ANTHROPIC_API_KEY.")
            return 2
        except anthropic.APIStatusError as exc:
            print(f"Claude API error {exc.status_code}: {exc.message}")
        except anthropic.APIConnectionError:
            print("Could not reach the Claude API.")


if __name__ == "__main__":
    sys.exit(main())
