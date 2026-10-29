# Fallbacks when companion skills are unavailable

Each section is a compact stand-in for one Matt Pocock skill. Use a section only when the named skill is absent from the available skills; when it is present, call the Skill tool with it instead.

## Interview (stands in for `grilling`)

Interview the user until no acceptance criterion rests on a silent assumption.

- Work in rounds. Each round asks every question that can be answered now, numbered, each with your recommended answer. A question that depends on an open question waits for the next round.
- Facts are yours to find: read the code, run the tool, check the docs before asking. Decisions are the user's: put each one to them and wait.
- Ask only what changes a specification: an actor, a rule, a boundary value, a failure path, an observable outcome. Skip a question whose answer would change no test.
- Done when every criterion has concrete example data and an observable outcome, and nothing is assumed silently. Say so in one line, then continue to writing.

Format:

```
Q1. <title>: <question, with choices if any>
    Recommended: <answer>

Q2. ...
```

## Inner loop (stands in for `tdd`)

Use inside green when a unit deserves its own tests on the way to an acceptance test passing.

- **Red before green.** Write the failing unit test first at a pre-agreed seam (a public interface of a module), then the least code that passes it.
- **One slice at a time**: one test, one minimal implementation, repeat. Each test responds to what the previous cycle taught; never write all the tests first.
- **Tests verify behaviour through public interfaces.** No mocking of internal collaborators, no private methods, no call-count assertions, no verifying through a side channel. Mock only at system boundaries: external APIs, the clock, randomness, sometimes the file system.
- **No tautologies.** Expected values are independent literals from the spec, not recomputed by the test.
- **Refactor only on green**, in small steps, keeping unit and acceptance tests passing. Refactoring never touches frozen files.

## Review (stands in for `code-review`)

Two axes, reported separately, never merged into one ranking.

- **Standards**: does the diff follow the repo's documented coding standards (`AGENTS.md`, `CONTRIBUTING.md`, `CODING_STANDARDS.md`, nested rules)? On top, flag judgement-call smells: mysterious names, duplicated logic, speculative generality, data clumps, feature envy, long message chains, one change scattered across many files. A documented repo standard overrides the smell list. Skip what tooling enforces.
- **Spec**: does the diff implement the story and the approved specifications? Report requirements missing or partial, behaviour nobody asked for, and requirements that look implemented but wrong. Quote the story line or the test name for each finding.

Run the two axes as parallel subagents when an agent-spawning tool exists, each given the diff command (`git diff <fixed-point>...HEAD`), the commit list and the relevant sources; otherwise run them one after the other yourself. The fixed point is the branch point of the feature (`git merge-base main HEAD`, or what the user names). Present `## Standards` and `## Spec`, each under 400 words, then one line: findings per axis and the worst within each.
