"""Regression tests for turn_cost.py.

Run with pytest (`pytest test_turn_cost.py`) or without it (`python test_turn_cost.py`).
Plain asserts and the standard library only. Each test builds a throwaway transcript.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_cost  # noqa: E402

PRICES = {
    "claude-opus-5-5": {"input": 4, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2, "output": 20},
    "claude-opus-5-5:fast": {"input": 8, "cache_write_5m": 10, "cache_write_1h": 16, "cache_read": 0.4, "output": 40},
    "claude-haiku-5-5": {"input": 0.1, "cache_write_5m": 0.125, "cache_write_1h": 0.2, "cache_read": 0.01, "output": 0.5},
    "claude-haiku-5-5:long": {"input": 0.5, "cache_write_5m": 0.625, "cache_write_1h": 1, "cache_read": 0.05, "output": 2.5},
    "web_search_per_1k": 10,
}


def user(time: str, content, **extra) -> dict:
    return {"type": "user", "timestamp": f"2026-10-28T{time}Z", "message": {"role": "user", "content": content}, **extra}


def assistant(time: str, message_id: str, model: str, **usage) -> dict:
    return {"type": "assistant", "timestamp": f"2026-10-28T{time}Z",
            "message": {"id": message_id, "model": model, "usage": usage}}


def write_session(folder: Path) -> Path:
    transcript = folder / "session.jsonl"
    main = [
        user("09:50:00", "an earlier turn"),
        assistant("09:50:10", "m0", "claude-opus-5-5", input_tokens=999, output_tokens=999),
        user("10:00:00", "Fix   the parser"),
        # m1: the first line of a streamed response carries a partial output count; the last line wins.
        # Its prompt is over 100K tokens, and with no opus ":long" price it falls back to the plain key.
        assistant("10:00:05", "m1", "claude-opus-5-5", input_tokens=10, output_tokens=5),
        assistant("10:00:06", "m1", "claude-opus-5-5", input_tokens=10, output_tokens=100,
                  cache_creation_input_tokens=1000, cache_creation={"ephemeral_1h_input_tokens": 1000},
                  cache_read_input_tokens=120_000),
        user("10:00:07", [{"type": "tool_result", "content": "ok"}]),
        assistant("10:01:00", "m2", "claude-haiku-5-5", input_tokens=2, cache_read_input_tokens=150_000, output_tokens=50),
        user("10:02:00", "<task-notification>agent finished</task-notification>"),
        assistant("10:03:00", "m3", "claude-opus-5-5", input_tokens=100, output_tokens=1000, speed="fast",
                  cache_creation_input_tokens=200, cache_creation={"ephemeral_5m_input_tokens": 200},
                  server_tool_use={"web_search_requests": 2}),
        assistant("10:03:01", "s1", "<synthetic>", input_tokens=0, output_tokens=0),
        user("10:05:00", "<command-message>turn-duration-check</command-message>\n"
                         "<command-name>/turn-duration-check</command-name>"),
        user("10:05:00", [{"type": "text", "text": "Base directory for this skill: ..."}], isMeta=True),
        assistant("10:05:10", "m4", "claude-opus-5-5", input_tokens=5000, output_tokens=5000),
    ]
    subagents = folder / "session" / "subagents"
    subagents.mkdir(parents=True)
    agent = [
        assistant("09:59:00", "a0", "claude-haiku-5-5", input_tokens=777, output_tokens=777),
        assistant("10:01:30", "a1", "claude-haiku-5-5", input_tokens=1000, output_tokens=500),
        assistant("10:06:00", "a2", "claude-haiku-5-5", input_tokens=777, output_tokens=777),
    ]
    transcript.write_text("\n".join(map(json.dumps, main)) + "\n", encoding="utf-8")
    (subagents / "agent-a.jsonl").write_text("\n".join(map(json.dumps, agent)) + "\n", encoding="utf-8")
    return transcript


def test_report_with_prices() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        text = turn_cost.report(write_session(Path(tmp)), PRICES)
    assert '**Turn 2 of 2:** "Fix the parser"' in text, text
    assert "**Duration (wall clock):** 0h 3m 0s" in text, text
    assert "| Main | claude-opus-5-5 | 10 | 0 | 1,000 | 120,000 | 100 | 121,110 | 0.0340 |" in text, text
    assert "| Main | claude-haiku-5-5:long | 2 | 0 | 0 | 150,000 | 50 | 150,052 | 0.0076 |" in text, text
    assert "| Main | claude-opus-5-5:fast | 100 | 200 | 0 | 0 | 1,000 | 1,300 | 0.0628 |" in text, text
    assert "| Subagents | claude-haiku-5-5 | 1,000 | 0 | 0 | 0 | 500 | 1,500 |" in text, text
    # 0.03404 + 0.007626 + (0.0428 + 2 searches at $10/1k) + 0.00035
    assert "| **Total** |  | 1,112 | 200 | 1,000 | 270,000 | 1,650 | 273,962 | 0.1048 |" in text, text
    assert "Web searches: 2" in text and "Price keys needed" not in text, text


def test_report_without_prices_lists_keys() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        text = turn_cost.report(write_session(Path(tmp)))
    assert "Cost (USD)" not in text, text
    assert text.endswith("Price keys needed: claude-haiku-5-5, claude-haiku-5-5:long, claude-opus-5-5, "
                         "claude-opus-5-5:fast, claude-opus-5-5:long, web_search_per_1k"), text


def test_earlier_turn() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        transcript = write_session(Path(tmp))
        text = turn_cost.report(transcript, turn=1)
        try:
            turn_cost.report(transcript, turn=3)
        except SystemExit as stop:
            assert str(stop) == "no turn 3: the session has 2 answered turns before this one", stop
        else:
            raise AssertionError("a turn that does not exist must stop the report")
    assert '**Turn 1 of 2:** "an earlier turn"' in text and "0h 0m 10s" in text, text
    assert "| Main | claude-opus-5-5 | 999 | 0 | 0 | 0 | 999 | 1,998 |" in text, text
    assert "| Subagents | claude-haiku-5-5 | 777 | 0 | 0 | 0 | 777 | 1,554 |" in text, text


def test_prepended_reminder_still_opens_a_turn() -> None:
    """After a fork the app prepends reminders to the user's message in the same entry. That
    message must still open a turn; on 2026-10-28 it was skipped and two turns merged."""
    reminder = {"type": "text", "text": "<system-reminder>\nThe user forked this conversation.\n</system-reminder>"}
    entries = [
        user("09:00:00", "review A-D"),
        assistant("09:10:00", "r1", "claude-opus-5-5", input_tokens=1, output_tokens=10),
        user("09:30:00", [reminder, {"type": "text", "text": "discuss B-D"}]),
        assistant("09:40:00", "r2", "claude-opus-5-5", input_tokens=2, output_tokens=20),
        user("09:41:00", "<system-reminder>a reminder on its own</system-reminder>"),
        assistant("09:42:00", "r3", "claude-opus-5-5", input_tokens=3, output_tokens=30),
        user("09:50:00", "<command-name>/turn-duration-check</command-name>"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "session.jsonl"
        transcript.write_text("\n".join(map(json.dumps, entries)) + "\n", encoding="utf-8")
        text = turn_cost.report(transcript)
    assert '**Turn 2 of 2:** "discuss B-D"' in text, text
    assert "**Duration (wall clock):** 0h 12m 0s" in text, text  # r3 belongs to the same turn
    assert "| Main | claude-opus-5-5 | 5 | 0 | 0 | 0 | 50 | 55 |" in text, text


def test_missing_price_stops() -> None:
    prices = {k: v for k, v in PRICES.items() if k != "claude-haiku-5-5"}
    with tempfile.TemporaryDirectory() as tmp:
        try:
            turn_cost.report(write_session(Path(tmp)), prices)
        except SystemExit as stop:
            assert str(stop) == "no price for claude-haiku-5-5", stop
        else:
            raise AssertionError("a missing price must stop the report")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"self-test OK ({len(tests)} checks)")
