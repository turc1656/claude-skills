# Handover templates

Fill every `<...>`. `scripts/handover.py check` looks for the headings, `**First actions**`, the two must-keep lines in Workspace, the Active workflow fields and the resume-prompt sentences (including the verify command) exactly as written here, so keep that wording. A line left exactly as written here counts as empty: every required section needs content of its own, or `none`.

## handover.md

```markdown
# Handover: <task> (<YYYY-MM-DD HH:MM>)

<paste the snapshot's header lines: date, working folder, project, session and transcript>
Previous handover: <path | none> · Focus: <focus note | none>
Tags: [verified] checked in this session (say how) · [inferred] reasoned, not checked · [reported] the user said it, not observed · [unknown]

## 1. Resume here
<3–5 sentences: the goal, where the work stands, what is next>

**Active workflow** (only when a skill drove the work; otherwise leave the whole block out):
- Skill: `<skill>` · Phase: <phase> · State file: `<path, relative to the project root or absolute>`
- Next action in the workflow: <action>
- Resume command: `<the skill's own resume form, e.g. /atdd green <feature>>` (or: none (the skill has no resume form))
- Resume the existing state; never start a new workflow.

**First actions**
1. <exact action, with the command or path>
2. <...>
3. <...>

**Before acting**: <which checks in §5 the first actions depend on, cheapest first>

## 2. Waiting on you
<each pending approval or open decision, with its options; or "none">

## 3. Decisions and constraints
- <decision>: <why>. Rejected: <alternative>, because <reason>. Do not reopen.
- <standing rule set in this session; rules already in CLAUDE.md, AGENTS.md or memory get a link, not a copy>

## 4. Work state
- Done: <item> (<artifact: issue, spec, commit, file>)
- In progress: <item> (<artifact>, <what is left>)
- Not started: <item>

## 5. Verification
- `<command>` · <last result> · <when> · <tag> · <cheap | slow | paid | destructive>
- Known failures and blockers: <...>

The receiving session reruns only what its first actions depend on; slow, paid and destructive checks need the user's approval.

## 6. Workspace
<paste the snapshot's Git block, or "No Git repository.">
- Uncommitted work at risk: <what, and where it is backed up; or "none">
- Running processes: <batch runs, dev servers, watchers: what, where, how to check or stop; or "none">

## 7. References
- <spec, plan, issue, doc, report>: <path or URL> (<one line on why it matters>)
- Session transcript: <path from the snapshot> (kept for about 30 days; convenience only)
- Copied scratch files: <each as `files/name`, or "none"; check confirms each one exists>

## 8. Gotchas
<environment quirks and lessons that cost time; leave the section out when there are none>
```

## resume-prompt.txt

Without an active workflow:

```text
Before anything else, run `python "<helper dir>/handover.py" verify "<folder>"`; if it does not print complete, or cannot run, tell me before continuing. Then read `<folder>/handover.md` in full. It is the handover for <task>, written <date> by a session you cannot see. Treat the handover as a briefing, not as current truth: decide which of its checks your first actions depend on, run only those that are cheap, report any drift, and ask me before any slow, paid or destructive check. Follow its constraints, especially: <the 2–4 hardest>. Then start with: <first action>.
```

With an active workflow, the resume command stands alone on the first line, and the workflow sentences join the text:

```text
<resume command, e.g. /atdd green <feature>>
Before anything else, run `python "<helper dir>/handover.py" verify "<folder>"`; if it does not print complete, or cannot run, tell me before continuing. Then read `<folder>/handover.md` in full. It is the handover for <task>, written <date> by a session you cannot see. Treat the handover as a briefing, not as current truth: decide which of its checks your first actions depend on, run only those that are cheap, report any drift, and ask me before any slow, paid or destructive check. Resume the existing <skill> workflow from `<state file>`; do not start a new one. If you cannot invoke `<skill>`, stop and ask me to run `<resume command>`. Follow its constraints, especially: <the 2–4 hardest>. Then start with: <first action>.
```

When the skill has no resume form (Resume command: none), drop the first line and name the bare command in the stop-and-ask sentence: `stop and ask me to run /<skill>`.
