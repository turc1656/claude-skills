# claude-skills

Source for custom Claude skills that are uploaded through **Customize → Skills** so they follow your account across Claude Desktop, claude.ai, Claude Code (local and cloud sessions) and Cowork. Nothing here is installed into a repository or into `~/.claude/skills/`.

```text
claude-skills/
├── README.md            this file
├── LICENSE              MIT
├── build_zip.py         builds dist/<skill>.zip and checks the frontmatter the upload enforces
├── dist/                built ZIPs (git-ignored; published as release assets)
├── atdd/                the ATDD skill: SKILL.md, references/, scripts/, evals/
├── git-commit-message/  a Conventional Commits message for the current changes: SKILL.md
├── handover/            the handover skill: SKILL.md, references/, scripts/
├── turn-duration-check/ a turn's duration, tokens and API-equivalent cost: SKILL.md, scripts/
└── ui-polish/           focused UI polish of an existing frontend: SKILL.md, references/
```

## Get the ZIPs

Download the latest build of each skill:

- [atdd.zip](https://github.com/turc1656/claude-skills/releases/latest/download/atdd.zip)
- [git-commit-message.zip](https://github.com/turc1656/claude-skills/releases/latest/download/git-commit-message.zip)
- [handover.zip](https://github.com/turc1656/claude-skills/releases/latest/download/handover.zip)
- [turn-duration-check.zip](https://github.com/turc1656/claude-skills/releases/latest/download/turn-duration-check.zip)
- [ui-polish.zip](https://github.com/turc1656/claude-skills/releases/latest/download/ui-polish.zip)

These links always serve the newest release. Older versions are on this repository's **Releases** page, or build the ZIPs yourself as below. `dist/` is git-ignored, so the ZIPs are never committed.

## Build the upload package

```bash
python build_zip.py atdd
python build_zip.py git-commit-message
python build_zip.py handover
python build_zip.py turn-duration-check
python build_zip.py ui-polish
```

The ZIP has the skill folder at its top level (`atdd/SKILL.md`, `atdd/references/...`, `atdd/scripts/...`) and leaves out `evals/`. The script refuses to build if the frontmatter `name` differs from the folder name, the description is over 200 characters, or a field outside the Agent Skills spec is present, because each of those fails the upload. The one extra field it allows is `disable-model-invocation`, which the upload also accepts.

## Upload to Customize → Skills

Prerequisite on Free, Pro and Max plans: **Settings → Capabilities → Code execution and file creation** must be on. On Team and Enterprise plans an owner enables **Skills** and code execution under **Organization settings → Plugins & skills → Policy**.

1. Open Claude Desktop or claude.ai and go to **Customize → Skills**.
2. Click **+**, then **Create skill**, then **Upload a skill**.
3. Choose `atdd.zip` (downloaded from a release, or `dist/atdd.zip` after a build).
4. The skill appears in the list; make sure its toggle is on.

Custom skills are per user, not per organisation. Each person who wants it uploads it themselves.

## Where it is available after upload

| Surface | How it shows up |
|---|---|
| Claude Desktop and claude.ai chat | Enabled under Customize → Skills; invoke by writing `/atdd ...` or "use the atdd skill". Without a repository it can draft specifications but cannot run red or green. |
| Claude Code, terminal or desktop Code tab, signed in with the same account (v2.1.273 or later) | Synced into `~/.claude/skills/synced/` within about 10 minutes of upload, listed by `/skills` under "claude.ai sync", invoked as `/atdd` (or `/anthropic-skills:atdd` if another command already uses `atdd`). Read-only locally: edit the source here and re-upload. |
| Cloud sessions, cloud scheduled tasks, Cowork | Loaded from the account at session start. `~/.claude/skills/` is not read there. |

Sync does not run when Claude Code uses an API key or a cloud provider such as Bedrock, or when `syncClaudeAiSkills` is set to `false` in user settings.

## Update an uploaded skill

1. Edit the source under `atdd/`, bump `metadata.version` in `SKILL.md`, and run the self-test and the build:

   ```bash
   python atdd/scripts/atdd_lock.py --self-test
   python build_zip.py atdd
   ```

2. In **Customize → Skills**, open the old `atdd`, switch its toggle off, click **...** then **Delete**, and confirm.
3. Upload the new `dist/atdd.zip` as above.

## Publish a release

Run every self-test, build all five ZIPs, then attach them to a new GitHub release. Attach all five to every release, under these exact names, even when only one skill changed: the links in *Get the ZIPs* serve whichever release is latest.

```bash
python atdd/scripts/atdd_lock.py --self-test
python handover/scripts/handover.py --self-test
python turn-duration-check/scripts/test_turn_cost.py
python build_zip.py atdd
python build_zip.py git-commit-message
python build_zip.py handover
python build_zip.py turn-duration-check
python build_zip.py ui-polish
gh release create <tag> dist/*.zip --title "<tag>" --notes "<what changed>"
```

## Verify after upload

- Claude Code (local): run `/skills` and look for `atdd` under the claude.ai sync group. Then, in any repository, run `/atdd status`; it should report "no features under .atdd/" without editing anything.
- Cloud session: start one on any repository and run the same two commands.
- Full behaviour: in a throwaway repository, `/atdd specify <story file>` must end with an approval request that shows complete test code and must not create `.atdd/`.
- `/handover`: run `/skills` and look for `handover`, then in any project run `/handover verification run`. A new folder must appear under `~/.claude/handovers/<project>/` with `.handover.json` saying `complete`, and `git status` must be unchanged.
- `/git-commit-message`: run `/skills` and look for `git-commit-message`, then in a repository with staged changes run `/git-commit-message`. It must reply with one commit message in a code block and leave `git status` unchanged.
- `/turn-duration-check`: run `/skills` and look for `turn-duration-check`, then in a Claude Code session send any short prompt and run `/turn-duration-check`. It must quote that prompt and report its duration, tokens and API-equivalent cost.
- `/ui-polish`: run `/skills` and look for `ui-polish`, then in a repository with a frontend run `/ui-polish audit <one page or component>`. It must reply with an audit in the format of `references/review-template.md` and edit nothing.

## The atdd skill

`/atdd` builds a feature against executable specifications in Dave Farley's style: acceptance tests written in the language of the problem domain, approved by you before any implementation, proven red, driven green while the approved files stay frozen, then verified and reviewed. `references/farley-atdd.md` digests the method and lists its sources.

**Use.** `/atdd [mode] <target>`, or ask for acceptance test-driven development in plain words.

- `/atdd #135` or `/atdd specify <story>`: start from a story (an issue number or URL, a ticket id, a file, or pasted requirements). After you approve, red, green and verify run on without further stops unless a gate forces one.
- `/atdd red|green|verify <feature>`: resume a feature whose manifest exists under `.atdd/<feature>/`.
- `/atdd amend <feature>`: the only way to change an approved file.
- `/atdd status [feature]`: report manifests and drift. No edits.

**Phases.**

- **Specify:** fetch the story (as `docs/agents/issue-tracker.md` says, else with `gh` for a GitHub remote, else from pasted text), extract its acceptance criteria and cite where each came from, settle ambiguity, and choose the seam: the highest public interface that exercises the behaviour end to end, with third-party systems stubbed. Then write three layers: test cases in domain language, a domain layer (the DSL), and a protocol driver. Criteria no public interface can observe are listed as not acceptance-testable, with a suggested manual check. Specify ends in an approval request that shows the complete code.
- **Red:** the frozen command must fail because the behaviour is missing, not because the harness is broken.
- **Green:** implementation changes only, one acceptance test at a time. Editing a frozen file, skipping a test, loosening an assertion or letting a driver bypass the system are not allowed; a wrong specification goes through `amend`.
- **Verify:** the repo's documented quality gate, then a review against the story.

**Gates.**

- No implementation starts, and no acceptance test runs against the system, until you approve the proposed files in chat. Only an explicit yes counts.
- On approval, `scripts/atdd_lock.py` freezes the tests and their support files (domain layer, drivers, stubs, fixtures) by SHA-256 hash in `.atdd/<feature>/manifest.json`, together with the run command and its working directory. Drift stops the work, and every change to a frozen file goes through `amend` and a fresh approval.
- `record` runs the frozen command itself, stores the real exit code, and enforces the order red, green, verify. A manual record or a waived red is flagged in the manifest.
- The manifest is meant to be committed with the feature as its traceability record. The skill stages or commits only when you or the repo's rules allow it.
- No new dependencies: the tests use the framework the repo already runs, and Gherkin only where a Gherkin runner already exists.
- The issue tracker is read-only unless you ask otherwise in the session.

**Companion skills.** When Matt Pocock's engineering skills are installed, it calls `grilling` to settle ambiguous criteria, `tdd` for the unit-level loop inside green, `codebase-design` for seam vocabulary, and `code-review` for the final review. Without them it uses the compact stand-ins in `references/fallbacks.md`.

**Any language.** `references/frameworks.md` holds per-stack defaults for detecting the stack and running one file or the suite. The target repo's own `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md` and `docs/agents/*.md` win over them.

**Without a repository** (plain chat), specify can still draft the specifications in the approval-request format; red, green and verify need a repository with a test runner.

## The git-commit-message skill

`/git-commit-message` writes a Conventional Commits message for the staged changes, the unstaged ones when nothing is staged, or a diff you paste. It never stages or commits. Its `allowed-tools` pre-approves only `git status`, `git diff` and `git rev-parse`, and `disable-model-invocation: true` means it runs only when you invoke it.

## The handover skill

`/handover` writes a durable continuation package before a session runs out of context, so a fresh session can resume the work from one pasted prompt.

**Install.** Download or build `handover.zip` and upload it as above. Its frontmatter is `name`, `description` and `metadata` only, so the upload accepts it.

**Use.** `/handover [--to <dir>] [focus note]`, or ask for a handover in plain words.

- The focus note says what to emphasise, for example `/handover prioritize the uncommitted parser changes`.
- `--to <dir>` writes directly under `<dir>` (for example a project's plans folder) instead of the default root.
- Nothing is run unless the focus note asks for it, for example `/handover run the unit tests`.

**Output.** One new folder per handover, never reused or overwritten:

```text
~/.claude/handovers/<project>/<YYYY-MM-DD_HHMMSS>_<slug>/
├── .handover.json     status: in-progress until `check` passes, then complete
├── handover.md        the core briefing, read in full by the next session
├── resume-prompt.txt  the prompt to paste into the new session
├── appendix.md        optional supporting detail
└── files/             optional copies of scratchpad files
```

**Resume.** Paste `resume-prompt.txt` into a new session yourself.

- The prompt makes the new session treat the handover as a briefing. It reruns only the checks its first actions depend on, and asks before anything slow, paid or destructive.
- When a skill workflow was active, the prompt's first line is that skill's own resume command (for example `/atdd green <feature>`), so pasting it invokes the skill and resumes the existing state.
- If the skill cannot be invoked, the new session stops and asks you to run the command.

**Interrupted runs.** A compaction during a handover leaves the folder `in-progress`. The next `/handover` in that session finds it, reads what is on disk, and finishes it.

**Edited after the check.** `.handover.json` keeps saying `complete` if a file is edited later. So the resume prompt opens with `python "<helper dir>/handover.py" verify "<folder>"`. It compares every file with the fingerprints recorded by the passing check, and exits 0 only when nothing changed, was added or was removed. The writing session's `status` reports the same case as `changed-since-check`.

**What `check` enforces.**

- Required files and headings, content in every required section, and at least one numbered first action.
- The `Uncommitted work at risk:` and `Running processes:` lines.
- Every named `files/...` is a regular file copied in.
- The `verify` command in the resume prompt: its helper must exist and its target must be this very folder. The active workflow's resume command and sentences.
- No secret-shaped text in any file, hidden files and the status file included, and no file too large to scan. Every file except the top-level `.handover.json` is fingerprinted.
- No symbolic link or junction anywhere in the folder. Links are rejected before anything is read, so nothing outside the folder is read or fingerprinted.

Whether every decision, approval and constraint made it in is the skill's review step, not something a script can judge.

**Limits.**

- Cloud sessions: `~/.claude/` does not outlive the cloud machine. The skill warns and prints both files in its reply instead. Detection relies on the `CLAUDE_CODE_REMOTE` environment variable, which is not yet verified.
- The session-transcript link in a handover is a convenience only: Claude Code deletes transcripts after `cleanupPeriodDays` (default 30).
- Context-limit warnings are not part of this skill.

**Privacy.**

- The skill never reads `.env` or other secret files, and it keeps credentials and personal data out of the handover.
- `check` scans every file in the folder for key- and token-shaped text and names only the file and line, never the match.
- Handovers stay on this machine, outside every repository.

**Key decisions.**

- The name is `handover`, so it never collides with the Matt Pocock plugin's `handoff`.
- Must-keep content (decisions, rejected alternatives, pending approvals, uncommitted work, running processes, constraints) always beats the 80–200-line length guideline.
- Git detail is in proportion to the task.
- The handover itself makes no Git changes and runs no tests.

## The turn-duration-check skill

`/turn-duration-check` reports how long the previous turn of a Claude Code session took, how many tokens it used, and what those tokens would cost at current Claude API prices.

**Use.** Run `/turn-duration-check` straight after the turn you want measured. Its description tells Claude to run it only when you invoke it.

**How it works.**

- The helper `scripts/turn_cost.py` reads this session's transcript, `~/.claude/projects/*/<session id>.jsonl`. A turn runs from your prompt to the last response before your next prompt; tool results, task notifications and system reminders are not prompts.
- It counts each response once, from its last streamed line, adds the subagent transcripts that ran during the turn, and splits tokens by model into input, 5-minute and 1-hour cache writes, cache reads and output. Thinking tokens are already part of the output count.
- The first run prints the report without cost and lists the price keys it needs. The skill then fetches Anthropic's pricing page, reads only those rates (never a price from memory), and runs the helper again with them. Fast mode, prompts over 100,000 tokens, US-only inference and web searches get their own keys when the turn used them.
- Run directly, the helper also takes `--turn N` to measure another turn: 1 is the session's first, -1 (the default) the previous.

**Output.** The helper's report unchanged, then one line naming the pricing URL and today's date. The cost is the API-equivalent figure: a subscription plan is not billed per token.

**Checks and limits.**

- Before pricing, the skill checks that the quoted prompt is your last message before the command and that the start time matches. If the helper missed or merged a prompt, it says so instead of reporting the wrong turn.
- If the pricing page cannot be fetched or lacks a key, you get the report without those costs and a note naming the keys that could not be priced.
- It reads a Claude Code session transcript, so it works only in Claude Code.

## The ui-polish skill

`/ui-polish <audit|plan|implement|verify> <scope>` polishes one surface of an existing frontend without redesigning it. `audit` and `plan` make no edits, `implement` runs only after you approve a plan, and `verify` checks the result at mobile and desktop widths and runs the frontend's lint, test and build. The rubric in `references/reference.md` covers hierarchy, spacing, typography, color, depth, tables, controls, states and responsive behavior; the target repository's own design guide and agent docs win over it. `disable-model-invocation: true` means it runs only when you invoke it.

## Tests for the skill itself

- `handover/scripts/test_handover.py` holds the helper's regression tests:
  - Git snapshots: clean, dirty, no repository, detached HEAD, unborn branch, operation in progress, many paths, spaces in paths. The snapshot is also shown to leave the index unchanged.
  - No-overwrite folder reservation, and the default and `--to` roots.
  - Session-scoped `status`.
  - The completion marker, finishing an interrupted handover, `changed-since-check` after a later edit, and `verify` reporting changed, added and removed files, including a link added after the check, while the JSON still says complete.
  - Links: a symlinked scratch file, a symlinked `handover.md`, a symlinked directory and (on Windows) a junction are all rejected without the target being read. A directory named like a copied file is not accepted as one.
  - The `verify` command: required, with a helper that exists, and aimed at this folder. Another folder or a missing one fails; the same folder spelled differently passes.
  - Hidden files (for example `.handover.private.txt`, `files/.env`) are scanned for secrets and fingerprinted.
  - The template filled in mechanically passes `check` and `verify`, with and without an active workflow, and the unfilled template fails.
  - Content checks: headings with empty sections, unfilled template lines (including the template itself), the required `Uncommitted work at risk:` and `Running processes:` lines.
  - Scratch files: a named `files/...` path that was not copied in, and one that points outside `files/`.
  - The active-workflow checks: a bare skill prefix, the wrong first line, missing resume or stop-and-ask sentences, a missing state file, and a skill with no resume form.
  - The secret scan, which catches each pattern without echoing it, ignores ordinary text, and fails on a file too large to scan instead of skipping it.

  The Git repositories the tests create are temporary fixtures. The suite passes on Windows with Python 3.9.2, 3.10.11 and 3.12.8; junctions are detected from the `lstat` reparse tag, so no Python 3.12-only API is needed. Run with `python handover/scripts/handover.py --self-test` (no pytest needed) or `uv run --with pytest pytest handover/scripts/test_handover.py`.
- `atdd/scripts/test_atdd_lock.py` holds the lock script's regression tests: approve and drift, CRLF tolerance, the amendment cycle, one named test per reviewed issue (approve cannot alter the frozen set without an amendment; re-approval with changes resets evidence; record enforces red, green, verify order and the lock state), and path-boundary tests (feature-name traversal and absolute paths, symlink and junction escapes at `.atdd/` and `.atdd/<feature>`, symlinks, dangling symlinks and hard links at the manifest file itself, atomic manifest writes, working directories outside the root, nested package directories). Run them with `python atdd/scripts/atdd_lock.py --self-test` (no pytest needed) or `uv run --with pytest pytest atdd/scripts/test_atdd_lock.py`.
- `turn-duration-check/scripts/test_turn_cost.py` holds the helper's regression tests: turn boundaries (tool results, task notifications and the skill's own invocation are not prompts; `--turn` picks an earlier turn), the last line of a streamed response winning, the subagent time window, 5-minute and 1-hour cache writes, fast-mode and long-prompt price keys with the long-prompt fallback, web searches, and a missing price stopping the report. Run with `python turn-duration-check/scripts/test_turn_cost.py` (no pytest needed).
- `atdd/evals/` holds two test cases in the `claude plugin eval` layout. With Claude Code installed: `claude plugin eval atdd --allow-tools Write,Edit,Bash --scaffold` (real, billed model runs).

## License

MIT. See [LICENSE](LICENSE).
