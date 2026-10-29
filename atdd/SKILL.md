---
name: atdd
description: "Dave Farley-style ATDD: approved executable acceptance tests, then red, green, verify. Use only when the user invokes /atdd or explicitly asks for acceptance test-driven development."
metadata:
  version: "1.2.2"
---

# ATDD: acceptance test-driven development

Build a feature against **executable specifications**: acceptance tests written in the language of the problem domain, approved by the user before any implementation, proven **red**, driven **green** while the approved files stay **frozen**, then verified and reviewed. The method is Dave Farley's. `references/farley-atdd.md` is the digest with sources; read it once per session before the first `specify`.

## Invocation

Treat the first word after `/atdd` as the mode when it is one of `specify`, `red`, `green`, `verify`, `amend`, `status`. The rest is the target: a story reference (`#135`, an issue URL, a ticket id, a file), a feature slug, or pasted requirements.

- `/atdd #135` or `/atdd specify #135`: start at specify. After approval, red, green and verify run on without further stops unless a gate forces one.
- `/atdd red|green|verify <feature>`: resume a feature whose manifest exists under `.atdd/<feature>/`.
- `/atdd amend <feature>`: the only way to change an approved file.
- `/atdd status [feature]`: report manifests and drift. No edits.

No target and nothing in the conversation to work from: ask for the story. Never invent requirements.

Resuming in a fresh session: read `.atdd/<feature>/manifest.json` first; it holds the story, the run command, the working directory and the frozen files. Without a repository (plain chat), specify can still draft the specifications in the approval-request format; red, green and verify need a repository with a test runner, so say so and stop at the request.

## Read first

| File | When |
|---|---|
| `references/farley-atdd.md` | once per session, before the first specify |
| `references/writing-acceptance-tests.md` | every specify and amend |
| `references/frameworks.md` | every specify and red: detect the stack, run one file, run the suite |
| `references/report-template.md` | at the approval gate and for the final report |
| `references/fallbacks.md` | only when a companion skill below is unavailable |

Read the target repository's own agent docs too: `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, `docs/agents/*.md`, and nested variants. They carry the vocabulary, the exact commands and the rules of that repo, and they win over the generic defaults in this skill's references. The gates below are not defaults; they hold everywhere.

## Companion skills

Work with Matt Pocock's engineering skills when they are installed and alone when they are not. Check the available skills once at the start. Names may be namespaced (`mattpocock-skills:tdd`); match the last segment. Never modify those skills.

| Need | If available, call the Skill tool with | Otherwise |
|---|---|---|
| Settle ambiguous criteria before writing | `grilling` | `fallbacks.md`, Interview |
| Unit-level red-green loop inside green | `tdd` | `fallbacks.md`, Inner loop |
| Seam and interface vocabulary | `codebase-design`, loaded for its vocabulary before choosing the seam | the seam notes in `writing-acceptance-tests.md` |
| Final review in verify | `code-review` | `fallbacks.md`, Review |

When two available skills share a last segment, prefer the Matt Pocock one: its `code-review` is the two-axis Standards and Spec review this skill expects, and a built-in `code-review` of another shape is not a substitute. Reading `CONTEXT.md` for vocabulary is a habit, not a skill call. In the Matt Pocock main flow this skill takes the place of `implement`: run it per ticket after `to-tickets`.

## Standing rules

- **Approval gate.** No implementation starts, and no acceptance test runs against the system, until the user approves the proposed files in chat. Show the code itself, never a summary of it. Only an explicit yes counts; a question, a partial remark or silence does not.
- **Frozen files.** On approval the test cases, the domain layer and the drivers freeze together: a driver that fakes an answer changes a test's meaning as surely as an edited assertion. `scripts/atdd_lock.py` records SHA-256 hashes in `.atdd/<feature>/manifest.json`; run `check` before every acceptance run and in verify. Drift stops the work. Every change to a frozen file goes through `amend`.
- **The manifest is committed.** It is the feature's traceability: which specifications were approved, when, and the red and green evidence. Never gitignore it. Stage or commit only when the user or the repo's rules allow it; when a commit happens, the manifest belongs in it.
- **No new dependencies.** Acceptance tests use the framework the repo already runs. Gherkin only where the repo already has a Gherkin runner. Domain layer and drivers are plain modules in the existing test tree.
- **Tracker is read-only.** Fetch stories. Never comment, label, assign or close unless the user asks for it in the session.
- **Any language.** The method is language-agnostic; `frameworks.md` holds per-stack defaults and the repo's docs hold the exact commands.

## Specify

1. **Fetch the story.** `docs/agents/issue-tracker.md`, when present, says how. Otherwise `gh issue view <n> --repo <owner/repo> --comments` when the remote is GitHub and `gh` is installed. Otherwise ask the user to paste the requirements. Read every comment: criteria often move there.
2. **Extract acceptance criteria.** They may live anywhere in the story: a checklist, the "what to build" prose, a comment. Cite the sentence each specification comes from. Each becomes one or more executable specifications: an observable outcome, from an actor's point of view, with concrete example data. A criterion no public interface can observe (feel, taste, "intuitive") or that is a process step (a decision to record, a ticket to open) is listed as not acceptance-testable with a suggested manual check. A test of implementation details is not a substitute. A placeholder issue, one marked "do not start" or still awaiting triage, may be specified, since nothing changes before approval; say so in the request, and green waits until the user confirms the story is ready.
3. **Settle ambiguity before writing.** `grilling` if available, else the interview fallback. Facts about the codebase are yours to find; decisions are the user's. When the user has said in advance that nobody will answer during the run, list each question in the numbered `Q1. / Recommended:` form under Open questions and proceed on your recommendation; the approval gate still stands.
4. **Choose the seam.** The public interface the tests drive: HTTP API, CLI, a library's public function, or the UI. Prefer the highest seam that exercises the behaviour end to end without a third-party system; stub external systems at their boundary. The choice goes in the approval request with its reason.
5. **Write the files** per `writing-acceptance-tests.md`:
   - test cases that read as behaviour in the domain's words, with no protocol detail;
   - a domain layer (the DSL) that maps those words to driver calls, with defaults and unique aliases for isolation;
   - a protocol driver that speaks HTTP, CLI, UI or function calls to the real system.

   Pragmatism: one feature on one protocol gets one support module holding domain layer and driver together. Split when a second protocol or a second feature reuses the vocabulary. The invariant is the test case: it never names an endpoint, selector, table or internal function.
6. **Place the files** where the repo keeps its tests, per its conventions and `frameworks.md`.
7. **Check the harness, not the behaviour.** Confirm the files are collected or compile (`pytest --collect-only`, `tsc --noEmit`, `go vet`). Do not run them against the system yet; that is red, and red comes after approval.
8. **Present the approval request** per `report-template.md` and stop.

## Approval gate

The request shows, for every proposed file, the complete content of a new file or a unified diff of a modified file, in fenced code blocks. Alongside: the behaviour each test case specifies in one line, the seam and why, the run command and its working directory, the stubs, and the criteria judged not acceptance-testable. Then wait.

The request is shown as-is; when the repo prescribes a response format, its block goes after the request, never around it.

Feature slug: the issue or story number and a short kebab-case name, such as `135-garage-reservations`; without a number, the short name alone. `--story` records the reference the tests were approved against. Once a feature is approved, `approve` is refused unless nothing changed: the frozen set, the hashes, the run command, the working directory and the story change only through `amend`, so re-scoping to a new issue is `unlock`, then `approve` with the new reference.

On an explicit yes, lock:

```bash
python3 <skill-dir>/scripts/atdd_lock.py approve --repo <repo-root> --feature <slug> --story "<ref>" --run "<command>" --cwd <dir> --tests <paths...> --support <paths...>
```

`<skill-dir>` is the directory this SKILL.md was read from. Use `python` where `python3` is absent. `--repo` is the repository root, where `.atdd/` lives; every command accepts it before or after the subcommand, and it defaults to the current directory, so the `check`, `record` and `unlock` calls below take it too unless run from the root. `--feature` is a single name, never a path. `--cwd` is a directory inside the repository, given relative to `--repo`; nested package directories such as `frontend` or `packages/api` are fine, and anything that resolves outside the root is refused. `--support` lists the domain layer, drivers, stubs and fixtures the tests depend on, plus any empty package files that make the test tree importable; they freeze with the tests. Present an empty file as "(new, empty)" with no code block. On a change request: revise, show the new diff, wait again.

## Red

1. `check` passes.
2. `record --feature <slug> --phase red --summary "<one line naming the missing behaviour>"`: the script runs the recorded command from the recorded directory, prints the tail of the output, and stores the real exit code. It refuses a passing run, a drifted tree, an open amendment, and a red after green. Only when the script cannot run the command in this environment, run it yourself and record with `--exit-code <n> --summary "..."`; the manifest flags that evidence as manual.
3. Read the failure. Red is valid when the cause is **missing behaviour**: a failed assertion, a 404, an unknown command, a public method or symbol of the system that does not exist yet. Red is invalid when the harness is broken: the test cannot import its own support module, a fixture is misconfigured, the driver has a typo, nothing was collected. A broken harness is fixed through `amend`, because the support files are frozen too.
4. A test that passes before implementation specifies nothing: either the behaviour already exists (tell the user) or the test is tautological (amend it).
5. Report the red evidence in a few lines and continue to green, unless the user invoked `red` alone.

## Green

1. `check` before starting and before every acceptance run.
2. Work in vertical slices: one acceptance test at a time, a tracer bullet through every layer it touches. Inside a slice use `tdd` for the unit-level loop where a unit deserves its own tests, else the inner-loop fallback. The seam approved at the gate is the `tdd` seam; it needs no second confirmation. A decision approved at the gate that has no acceptance criterion (an open question's answer) gets a unit test when it has a runnable red; otherwise the report lists it as untested.
3. Only implementation changes. Not allowed: editing a frozen file, skipping or xfail-ing or `.only`-ing a test, loosening an assertion, sleeping to pass a timing problem, or a driver change that bypasses the system. If a specification looks wrong, stop and go to `amend`.
4. Run the touched existing tests often and the full suite once at the end.
5. Green is reached when the recorded command exits 0 and the rest of the suite still passes. `record --feature <slug> --phase green --summary "<one line>"` runs the command and stores the result; it is refused without red evidence for the current approval, so an amendment that changed content means red again first.

## Amend

Only for a frozen file: a wrong expectation found in green, a harness defect found in red, a criterion the user changed.

1. Stop. Say which file and why, in one short paragraph.
2. Show the proposed change as a unified diff.
3. Wait for an explicit yes.
4. `unlock --feature <slug> --reason "<why>"`, apply the change, `approve` again with the same arguments so the hashes are current. Any change to the frozen set, the hashes, the run command or the directory resets the red, green and verify evidence and keeps the old evidence on the amendment record, so run red again through `record`. If the amended specification passes at once because the behaviour already exists, tell the user; only with their explicit yes record green with `--red-waived "<their reason>"`, which `status` and the report show.

## Verify

1. `check`.
2. The repo's documented quality gate, exactly as documented: full test suite, lint, typecheck, build. When it passes: `record --feature <slug> --phase verify --exit-code 0 --summary "<suite, lint, typecheck>"`.
3. Review: `code-review` with the story as the spec and the branch point as the fixed point, else the review fallback. Approved specifications count as part of the spec. Without git history, or when the repo lacks the issue-tracker doc `code-review` asks for, use the fallback with a pristine copy or snapshot the user names as the fixed point.
4. Report per `report-template.md`: each test with its red and green status, the evidence, suite results, review findings, lock status, files changed, and the one next action for the user. If the repo prescribes its own final-response format, wrap the report in it.

## Status

`status --feature <slug>`, or `status` for all features, then `check`. Report state, tests, evidence (with manual records and red waivers), amendments and drift. No edits.

## Completion behaviour

End every mode with one clear next action: specify ends in an approval request; red continues to green; green continues to verify; verify ends in pass or fail with what remains; amend ends in a re-approval request.
