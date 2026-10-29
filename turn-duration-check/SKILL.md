---
name: turn-duration-check
description: "Report how long the previous turn in this Claude Code session took, how many tokens it used, and their cost at current API prices. Only run when the user invokes /turn-duration-check."
metadata:
  version: "1.1.1"
---

Report how long the previous turn in this session took, how many tokens it used, and what those tokens cost at current Claude API prices.

The helper is `python "${CLAUDE_SKILL_DIR}/scripts/turn_cost.py"` (`python3` where `python` is absent; the directory this SKILL.md was read from when the variable is not substituted). It finds the turn, counts each response once, separates subagents, splits tokens by model, and does the arithmetic. Don't redo any of that by hand.

1. Find this session's transcript at `~/.claude/projects/*/${CLAUDE_SESSION_ID}.jsonl`. If nothing matches, search under `~/.claude` for a file named `${CLAUDE_SESSION_ID}.jsonl`.
2. Run the helper on it: `python "<helper>" "<transcript>"`. It prints the report without cost and ends with `Price keys needed:`.
   Check the turn before going on. The quoted prompt must be the user's last message before this command, and the start time must match when they sent it. If either is off, the helper has missed or merged a prompt: find which message it skipped, tell the user, and don't report the wrong turn.
3. Fetch `https://platform.claude.com/docs/en/about-claude/pricing.md` and read the rates for those keys only, in USD per million tokens. Never fill in a price from memory.
   - A model id: base input, 5m cache writes, 1h cache writes, cache hits, and output, from the model pricing table.
   - `<model>:fast`: the fast-mode input and output prices. Derive the three cache rates by applying the page's prompt-caching multipliers for that model to the fast input price.
   - `<model>:long` (a prompt over 100,000 tokens): only when the page lists a separate long-prompt price for that model. Otherwise leave it out, and the helper uses the plain key.
   - `us_multiplier` and `web_search_per_1k`: from the data-residency and web-search sections.
4. Run the helper again with the prices on stdin, one entry per key:

   ```bash
   python "<helper>" "<transcript>" --prices - <<'EOF'
   {"<model id>": {"input": <rate>, "cache_write_5m": <rate>, "cache_write_1h": <rate>, "cache_read": <rate>, "output": <rate>}}
   EOF
   ```

5. Reply with the helper's output unchanged, then one line naming the pricing URL and today's date and saying this is the API-equivalent cost: a subscription plan is not billed per token.

If the page can't be fetched, or a key isn't on it, reply with the report from step 2 and say which keys could not be priced.

Don't summarize or comment on anything else in the transcript.
