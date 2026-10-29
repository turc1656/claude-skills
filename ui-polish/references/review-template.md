# Required UI-polish output templates

## Audit output

### Scope and evidence

- Scope reviewed:
- Routes/components inspected:
- Rendered widths/states inspected:
- Anything not available for verification:

### Current strengths to preserve

List the aspects that already support the product's identity or workflows.

### Findings

For each finding use:

#### `[P0|P1|P2|P3] Concise finding title`

- **Surface:**
- **Evidence:**
- **Consequence:**
- **Recommended direction:**
- **Category:** usability/accessibility, consistency/maintainability, or subjective polish

### Cross-cutting system issues

List repeated typography, spacing, color, radius, border, elevation, or component issues. Do not propose a system migration when the problem is isolated.

### Explicit non-changes

State what should remain unchanged and why.

### Recommended first slice

Define one small, complete, reviewable implementation slice with expected benefit and likely files.

---

## Plan output

### Goal

- Primary user task:
- Desired improvement:
- Product personality to preserve:

### Preserved behavior

List routes, data behavior, interactions, and states that will not change.

### Proposed visual direction

Describe the recommended direction in product terms. When a subjective choice is necessary, include at most one alternative and explain the difference.

### Files and components

| File/component | Planned change | Why it belongs in scope |
|---|---|---|

### Design-system changes

- Tokens to add/change:
- Shared primitives to add/change:
- Existing one-off values to remove:
- Why each change is reusable:

### Implementation sequence

1. Foundation or primitive work.
2. Main surface changes.
3. State and responsive changes.
4. Cleanup and verification.

### State coverage

- Populated:
- Loading:
- Empty/no matches:
- Error:
- Locked/unavailable:
- Long content/large values:

### Responsive and accessibility checks

List concrete widths, keyboard interactions, focus, contrast, semantics, and table behavior to verify.

### Tests and commands

- The frontend's documented lint, test and build commands (for example `npm run lint`, `npm test`, `npm run build`)
- Rendered pages and widths to inspect

### Risks and non-goals

- Risks/trade-offs:
- Explicit non-goals:
- Rollback or containment strategy:

### Approval gate

End with: `Approve this plan before implementation.`

---

## Implementation completion output

### Implemented

Summarize the completed design changes by user-visible outcome, not just by file.

### Preserved

Confirm the important functionality and information architecture that remained unchanged.

### Files changed

| File | Purpose |
|---|---|

### Checks run

| Check | Result |
|---|---|

### Visual verification completed

List actual widths and states inspected. State clearly what was not inspected.

### Deviations from plan

Explain any approved or necessary deviations and their consequences.

### Next action

Recommend `/ui-polish verify <scope>`.

---

## Verification output

### Verification status

`PASS`, `PASS WITH FOLLOW-UPS`, or `FAIL`.

### Visual and interaction results

| Area/state | Width | Result | Notes |
|---|---:|---|---|

### Accessibility results

- Keyboard:
- Focus:
- Contrast:
- Semantics:
- Non-color state cues:
- Reduced motion/touch targets where applicable:

### Engineering checks

| Command | Result | Relevant output |
|---|---|---|

### Regressions or remaining issues

List severity, surface, and recommended correction. Do not hide unavailable verification.

### Final assessment

State whether the approved design goal was achieved and whether the result remains consistent with the product's identity.
