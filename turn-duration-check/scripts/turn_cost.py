#!/usr/bin/env python3
"""Measure the previous turn of a Claude Code session: wall-clock time, tokens and cost.

Usage:
  python turn_cost.py TRANSCRIPT.jsonl                 report without cost; lists the price keys needed
  python turn_cost.py TRANSCRIPT.jsonl --prices -      report with cost; prices JSON on stdin (or a file path)
  add --turn N to measure another turn: 1 is the session's first, -1 (default) the previous

A turn runs from a user prompt to the last assistant response before the next prompt. The
newest prompt is the one that invoked the skill, so it is never measured itself. Tool
results, task notifications and system reminders are not prompts; reminders the app
prepends to the user's own text are stripped first, so that text still opens a turn. Subagent transcripts in
TRANSCRIPT_STEM/subagents/ count from the turn's start until the next prompt. Each response
is counted once, from its last line, because earlier lines of a streamed response can carry
a partial output count. Thinking tokens are already part of the output count.

The prices JSON holds USD per million tokens for each price key the first run lists:
  {"<model id>": {"input": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0, "output": 0},
   "us_multiplier": 0, "web_search_per_1k": 0}
A price key is the model id, plus ":fast" for fast-mode responses and ":long" for requests
whose prompt (input + cache reads + cache writes) is over 100,000 tokens. A ":long" key is
needed only where the pricing page lists a separate long-prompt price; without one the
plain key is used. us_multiplier is needed only when a response ran with inference_geo
"us", web_search_per_1k only when a response ran web searches.

Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ponytail: Haiku 5.5's long-prompt threshold (pricing page, 2026-10-28); make it a per-key
# price field if another model gets a different threshold.
LONG_PROMPT_TOKENS = 100_000
FIELDS = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")
HEADINGS = ("Input", "Cache write 5m", "Cache write 1h", "Cache read", "Output")
SYSTEM_PREFIXES = ("<task-notification>", "<system-reminder>", "<local-command-stdout>",
                   "<local-command-caveat>", "<side-sessions-event>", "<ci-monitor-event>",
                   "<bash-stdout>", "<bash-stderr>")
LEADING_REMINDERS = re.compile(r"^(?:\s*<system-reminder>.*?</system-reminder>)+", re.S)
PREVIEW_CHARS = 80


def load(path: Path) -> list[dict]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # the session is still writing its last line
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def prompt_text(entry: dict) -> str | None:
    """The text of a user's own prompt; None for tool results, injected context and app events."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str):
        return None
    # The app can prepend reminders to the user's own text in one entry (every message after a
    # fork, for example). Strip them: the entry is a prompt when the user's text remains.
    content = LEADING_REMINDERS.sub("", content)
    if not content.strip() or content.lstrip().startswith(SYSTEM_PREFIXES):
        return None
    command = re.search(r"<command-name>(.*?)</command-name>", content, re.S)
    if command:
        args = re.search(r"<command-args>(.*?)</command-args>", content, re.S)
        content = command.group(1) + (" " + args.group(1) if args else "")
    return " ".join(content.split())


def is_response(entry: dict) -> bool:
    message = entry.get("message")
    return (entry.get("type") == "assistant" and isinstance(message, dict)
            and isinstance(message.get("usage"), dict) and message.get("model") != "<synthetic>")


def parse_time(entry: dict) -> datetime:
    return datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))


def find_turns(entries: list[dict]) -> list[tuple[int, int, int]]:
    """Each answered turn before the invoking (newest) prompt, as indexes of its opening
    prompt, its last response, and the prompt after it."""
    prompts = [i for i, e in enumerate(entries) if prompt_text(e) is not None]
    turns = []
    for opener, closer in zip(prompts, prompts[1:]):
        responses = [i for i in range(opener + 1, closer) if is_response(entries[i])]
        if responses:
            turns.append((opener, responses[-1], closer))
    return turns


def last_lines(entries: list[dict]) -> list[dict]:
    """One message per response, from its last line."""
    by_id = {}
    for e in entries:
        if is_response(e):
            by_id[e["message"].get("id") or e.get("uuid")] = e["message"]
    return list(by_id.values())


def price_key(message: dict) -> str:
    usage = message["usage"]
    key = message.get("model") or "unknown"
    if usage.get("speed") == "fast":
        key += ":fast"
    prompt = sum(usage.get(f) or 0 for f in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    if prompt > LONG_PROMPT_TOKENS:
        key += ":long"
    return key


def token_counts(usage: dict) -> dict[str, int]:
    written = usage.get("cache_creation_input_tokens") or 0
    one_hour = (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0
    return {"input": usage.get("input_tokens") or 0,
            "cache_write_5m": written - one_hour,  # ponytail: a write without the TTL split counts as 5-minute
            "cache_write_1h": one_hour,
            "cache_read": usage.get("cache_read_input_tokens") or 0,
            "output": usage.get("output_tokens") or 0}


def web_searches(usage: dict) -> int:
    return (usage.get("server_tool_use") or {}).get("web_search_requests") or 0


def resolve(key: str, prices: dict | None) -> str:
    """The key that is priced: a ":long" key without a price of its own falls back to the plain key."""
    if prices is None or key in prices or not key.endswith(":long"):
        return key
    return key.removesuffix(":long")


def price(prices: dict, key: str):
    value = prices.get(key)
    if value is None:
        raise SystemExit(f"no price for {key}")
    return value


def request_cost(message: dict, prices: dict) -> float:
    usage = message["usage"]
    rates = price(prices, resolve(price_key(message), prices))
    counts = token_counts(usage)
    cost = sum(counts[f] * price(rates, f) for f in FIELDS) / 1_000_000
    if usage.get("inference_geo") == "us":
        cost *= price(prices, "us_multiplier")  # applies to token prices only
    if web_searches(usage):
        cost += web_searches(usage) * price(prices, "web_search_per_1k") / 1000
    return cost


def local(moment: datetime) -> str:
    return moment.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def duration(span: timedelta) -> str:
    seconds = max(0, round(span.total_seconds()))
    return f"{seconds // 3600}h {seconds % 3600 // 60}m {seconds % 60}s"


def report(transcript: Path, prices: dict | None = None, turn: int = -1) -> str:
    entries = load(transcript)
    turns = find_turns(entries)
    if turn == 0 or not -len(turns) <= turn <= len(turns):
        raise SystemExit(f"no turn {turn}: the session has {len(turns)} answered turns before this one")
    number = turn if turn > 0 else len(turns) + 1 + turn
    start, end, closer = turns[number - 1]
    started, ended, closed = (parse_time(entries[i]) for i in (start, end, closer))
    subagent_entries = []
    for path in sorted((transcript.parent / transcript.stem / "subagents").glob("*.jsonl")):
        subagent_entries += [e for e in load(path) if e.get("timestamp") and started <= parse_time(e) < closed]
    groups = [("Main", last_lines(entries[start + 1:end + 1])), ("Subagents", last_lines(subagent_entries))]

    rows: dict[tuple[str, str], list] = {}  # (group, label) -> [token counts..., cost]
    needed, searches = set(), 0
    for group, messages in groups:
        for message in messages:
            usage = message["usage"]
            key = price_key(message)
            needed |= {key, key.removesuffix(":long")}
            us_only = usage.get("inference_geo") == "us"
            if us_only:
                needed.add("us_multiplier")
            if web_searches(usage):
                needed.add("web_search_per_1k")
                searches += web_searches(usage)
            label = resolve(key, prices) + (" (US-only)" if us_only else "")
            row = rows.setdefault((group, label), [0] * len(FIELDS) + [0.0])
            for i, n in enumerate(token_counts(usage).values()):
                row[i] += n
            if prices is not None:
                row[-1] += request_cost(message, prices)

    with_cost = prices is not None
    header = ["Tokens", "Price key", *HEADINGS, "Total"] + (["Cost (USD)"] if with_cost else [])
    lines = [f'**Turn {number} of {len(turns)}:** "{preview(entries[start])}"',
             f"**Start:** {local(started)} · **End:** {local(ended)} · **Duration (wall clock):** {duration(ended - started)}",
             "",
             "| " + " | ".join(header) + " |",
             "|" + "---|" * 2 + "--:|" * (len(header) - 2)]
    total = [0] * len(FIELDS) + [0.0]
    for (group, label), row in rows.items():
        total = [a + b for a, b in zip(total, row)]
        lines.append(table_row([group, label], row, with_cost))
    lines.append(table_row(["**Total**", ""], total, with_cost))
    if not any(group == "Subagents" for group, _ in rows):
        lines += ["", "No subagent activity in this turn."]
    if searches:
        lines += ["", f"Web searches: {searches}"]
    if not with_cost:
        lines += ["", "Price keys needed: " + ", ".join(sorted(needed))]
    return "\n".join(lines)


def table_row(labels: list[str], row: list, with_cost: bool) -> str:
    tokens = row[:len(FIELDS)]
    cells = labels + [f"{n:,}" for n in tokens] + [f"{sum(tokens):,}"] + ([f"{row[-1]:,.4f}"] if with_cost else [])
    return "| " + " | ".join(cells) + " |"


def preview(entry: dict) -> str:
    text = prompt_text(entry) or ""
    return text if len(text) <= PREVIEW_CHARS else text[:PREVIEW_CHARS].rstrip() + "…"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # prompt previews may hold non-ASCII text
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--prices", help="prices JSON file, or - to read it from stdin")
    parser.add_argument("--turn", type=int, default=-1,
                        help="which answered turn: 1 is the session's first, -1 (default) the previous, -2 the one before")
    args = parser.parse_args(argv)
    prices = None
    if args.prices:
        prices = json.loads(sys.stdin.read() if args.prices == "-" else Path(args.prices).read_text(encoding="utf-8"))
    print(report(args.transcript, prices, args.turn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
