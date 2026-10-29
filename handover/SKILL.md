---
name: handover
description: "Handover: write a durable continuation package so a fresh session can resume this work. Use only when the user invokes /handover or explicitly asks for a handover or handoff."
metadata:
  version: "1.0.1"
---

# Handover

A **handover** is a folder on disk from which a fresh session, given one pasted prompt and nothing of this conversation, continues the work. It is a **briefing**, not a transcript: what to do next, what was decided and why, what waits on the user, and how to confirm the briefing still matches reality. It is usually written late, under context pressure, and a compaction can land mid-run, so the steps put the most valuable file on disk first, and **the disk wins** over any memory or summary of what was written.

## Invocation

`/handover [--to <dir>] [focus note]`

- The text after the command is the **focus note**: what to emphasise, or what the next session will be used for.
- `--to <dir>` puts the folder directly under `<dir>` (for example a project's plans folder) instead of `~/.claude/handovers/<project>/`. Pass it to `status` and `reserve` alike.
- Checks run only when the focus note asks for one (`/handover run the unit tests`).

The helper is `python "${CLAUDE_SKILL_DIR}/scripts/handover.py"` (`python3` where `python` is absent; the directory this SKILL.md was read from when the variable is not substituted). This session's id is `${CLAUDE_SESSION_ID}`. When the id is not substituted, this is not a Claude Code session: write `handover.md` and `resume-prompt.txt` straight into the reply instead.

## Steps

1. **Look for an unfinished handover.** `status --session ${CLAUDE_SESSION_ID}`. An `in-progress` or `changed-since-check` line means this session already has one that is not complete: go to *Resuming* with that folder. Done when every listed handover is `complete`, or none is listed.
2. **Reserve.** `reserve --session ${CLAUDE_SESSION_ID} --slug "<three to five words naming the task>"`. It prints the new folder and marks it `in-progress`. Done when you hold the path.
3. **Snapshot.** `snapshot --session ${CLAUDE_SESSION_ID}`. It prints the header facts and the Git block for the Workspace section, read-only. When it reports a cloud session, the folder will not outlive this machine: warn the user and also print both files in the reply at step 9.
4. **Write `handover.md`** in one Write, following `references/template.md` (read it now) and the content rules below. Done when every **must-keep** item from this session is in it.
5. **Write `resume-prompt.txt`** from the same template. Its `<helper dir>` is the absolute folder of the helper you ran (`${CLAUDE_SKILL_DIR}/scripts`), so the receiving session can run `verify`: `.handover.json` alone can still say `complete` after a file was edited, and only `verify` compares the files with their passing check.
6. **Optional:** `appendix.md` for supporting detail on substantial work (full history, the user's instructions in order, result tables, hypotheses with their evidence), linked from the core; and `files/` for scratchpad files the next session needs, since the scratchpad is deleted with the session. Name each copied file as `files/<name>`.
7. **Review** the core as the receiving session will read it, against this session's record: every decision and its reason, every rejected alternative, every pending approval, every constraint, the work state, uncommitted work and running processes. Each one is in `handover.md` (or the appendix it links), or stated as `none`. Done when nothing from that list is missing; `check` cannot judge this, only headings and shape.
8. **Check.** `check <folder>`. It fails on missing files or headings, an empty section, no numbered first action, a missing `Uncommitted work at risk:` or `Running processes:` line, a `files/...` name that is not a regular file copied in, a `verify` command that is missing, names a helper that does not exist, or targets any folder but this one, an active-workflow prompt that would not resume the workflow, a secret-shaped string, any file it could not scan, and any symbolic link or junction in the folder (copy real files in instead). Fix each problem and run it again. Done when it prints `PASS`; only then is the handover `complete`. Any later edit makes `status` report `changed-since-check` until `check` passes again.
9. **Reply** with the folder path, the status, the line counts, one line on what it covers, what is not verified, and the resume prompt in a fenced block ready to paste. The user pastes it into a new session themselves.

## Resuming an unfinished handover

After a compaction, or when step 1 finds one:

- List the folder and Read every file in it; the disk wins over the compaction summary.
- Continue from the first missing step and write only the missing files.
- Read a file before editing it; extend or correct it, keeping all of its content and every file.
- Keep working in that folder; a second folder only when the user asks for one.
- Finish with steps 7 and 8, so `complete` always follows a review and a passing check.

## Content rules

- **Must-keep**: decisions with their reasons; rejected alternatives with their reasons; pending approvals and open decisions; uncommitted work; running processes; important constraints and standing rules. These stay in the core whatever its length.
- **Inclusion test** for everything else: keep a fact when, without it, the next session would act wrongly, reopen a settled question, or redo work. Supporting detail goes to the appendix; the rest stays out.
- **Length**: 80–200 lines is a guideline, never a reason to cut a must-keep item. Move detail to the appendix instead.
- **Link, don't copy**: anything already in a spec, plan, issue, commit, doc or state file gets its path or URL and one line on why it matters.
- **Checks, not dumps**: for anything the next session can recheck (Git, tests, file contents), give the command, the last result with its time, a tag, and a cost label: `cheap`, `slow`, `paid` or `destructive`.
- **Tags** go on claims about state (files, Git, tests, external systems): `[verified]` with how, `[inferred]`, `[reported]` by the user, `[unknown]`. Facts known only from a compaction summary are `[unknown]` until rechecked; recover exact wording from the session transcript when it matters.
- **Git in proportion**: the snapshot block is the default. Write a full Git section only when the task itself is about Git state or uncommitted work is at risk.
- **Active workflow**: only when a skill drove the work. Point to the skill's own state file. Take the resume command from that skill's own instructions (its mode and state identifier, such as `/atdd green <feature>`), because a skill reads the text after its name as arguments, and a bare name plus free text can start a new workflow. A skill with no resume form gets `none`.
- **Hypotheses**: each with its evidence for and against; rank only on evidence and say what the ranking rests on.
- **The user's words**: quote their exact phrasing for goals and constraints.

## Guardrails

- The project stays as it was: queries only, no Git changes, no source edits, no model calls, and checks only on request.
- Secret files (`.env` and the like) stay unread; credentials and personal data stay out of every file. The secret scan in `check` is a backstop.
- Starting, clearing, compacting or archiving sessions stays with the user.
