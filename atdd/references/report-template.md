# Report templates

Contents: Approval request · Re-approval request (amend) · Completion report

Use these structures exactly; the person approving reads the same shape every time.

## Approval request

Produced at the end of specify. Code is shown in full for new files and as a unified diff for modified files. Nothing is summarised in place of code.

````markdown
## ATDD approval request: <feature-slug> (<story reference>)

### Criteria and specifications
- AC1 "<criterion text>": S1 <test name>, S2 <test name>
- AC2 "<criterion text>": S3 <test name>
- AC3 "<criterion text>": not acceptance-testable because <reason>. Manual check: <what a human does>

### Seam
<interface driven> because <reason>. Stubs: <external systems replaced, or "none">.

### Run
`<exact command>` from `<working directory>`. Harness check: <collected or compiled, with the result>.

### Proposed files
#### `<path>` (new)
```<lang>
<complete file content>
```

#### `<path>` (modified)
```diff
<unified diff>
```

### Open questions
<numbered, or "none">

**Reply with an explicit approval to lock these files and run red, or say what to change.**
````

## Re-approval request (amend)

````markdown
## ATDD amendment: <feature-slug>

**File:** `<path>`
**Why:** <one short paragraph: what is wrong with the current specification or harness, and what the change preserves>

```diff
<unified diff>
```

**Reply with an explicit approval to re-lock, or say what to change.**
````

## Completion report

Produced at the end of verify. If the repository prescribes its own final-response format (for example Summary / Validation / Notes), wrap this report inside it.

````markdown
## ATDD report: <feature-slug> (<story reference>)

**Status:** <complete | blocked: reason>

### Acceptance tests
| Spec | File | Red | Green |
|---|---|---|---|
| S1 <name> | `<path>` | <date>, exit <n>, "<failure summary>" | <date>, exit 0 |

### Evidence
- Red: `<command>` from `<cwd>`, exit <n>: <summary> <(manual, if recorded by hand)>
- Green: `<command>` from `<cwd>`, exit 0 <(manual, if recorded by hand)>
- Verify: recorded, exit 0: <suite, lint, typecheck summary>
- Amendments: <none | list with reasons and what each reset>
- Red waived: <none | the user's reason>
- Approved decisions without a criterion: <unit-tested | listed as untested>

### Verification
- <package>: `<suite command>`: pass | fail (<summary>)
- <package>: `<lint command>`: pass | fail
- <package>: `<typecheck or build command>`: pass | fail | not run (<why>)

### Review
#### Standards
<findings or "none">
#### Spec
<findings or "none">

### Lock
`check`: clean | drift in <files>

### Files changed
- `<path>`: <one line>
- `.atdd/<feature-slug>/manifest.json`: approval record and evidence

### Next action
<one line, for example "Commit the change including .atdd/<feature-slug>/" or "Fix finding 2, then re-run verify">
````
