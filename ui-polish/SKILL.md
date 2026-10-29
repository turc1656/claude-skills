---
name: ui-polish
description: "Audit, plan, implement and verify focused UI polish in an existing frontend while keeping its layout, behavior and identity. Not for backend work or wholesale redesigns."
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# UI polish workflow

Use the mode and scope supplied with the skill invocation.

Examples:

- `/ui-polish audit dashboard`
- `/ui-polish plan data table`
- `/ui-polish implement shared UI primitives`
- `/ui-polish verify settings page`

## Read first

Before working, read:

1. `references/reference.md` for the operational design rubric.
2. `references/audit-checklist.md` for the relevant surface.
3. `references/review-template.md` for the required output structure.
4. The target repository's own design principles or style guide, when one exists, for broader rationale or component guidance.
5. The repository-root `AGENTS.md` or `CLAUDE.md` and any more-specific `AGENTS.md`, `AGENTS.override.md` or `CLAUDE.md` files that apply, including those in the frontend's own folder. They carry the frontend's rules and exact commands, and they win over the generic defaults in this skill's references.

## Interpret the request

Treat the first word after `/ui-polish` as the mode when it is one of:

- `audit`
- `plan`
- `implement`
- `verify`

Treat the remaining text as the scope.

When no mode is supplied, default to `audit`. When no scope is supplied, ask for one rather than auditing the entire frontend without boundaries.

## Standing constraints

Apply these throughout the task:

- Preserve existing routes, business behavior, API contracts, auth, access control, entitlements, and data semantics unless the user explicitly approves a functional change.
- Preserve the existing overall layout and information architecture. Improve clarity and polish rather than replacing the product's identity.
- Do not invent features, data, charts, claims, or interactions.
- Do not use a broad visual trend as the design direction. Avoid glassmorphism, neon glow, excessive gradients, huge rounded cards, ornamental analytics, and unnecessary animation.
- Keep application surfaces calm and information-focused. Marketing pages may be more expressive but must remain consistent with the product.
- Prefer shared tokens and primitives when several surfaces need the same correction. Do not create abstractions for a one-off variation without evidence of reuse.
- Make no edits during `audit` or `plan` mode.
- Do not enter `implement` mode without an approved plan for the requested scope. If approval is not evident in the conversation, present or update the plan and stop before editing.
- Do not modify unrelated files merely because they are visually inconsistent. Record them as follow-up findings.

## Inspect the current state

For every mode:

1. Locate the relevant route, components, shared primitives, styles, and tests.
2. Identify the actual data states supported by the code.
3. Inspect the running application when possible instead of judging only from class names.
4. Review representative widths:
   - narrow mobile around 390px
   - tablet/intermediate around 768px
   - desktop around 1280px
   - wide desktop around 1440px or the product's actual max width
5. Inspect populated, loading, empty, error, unavailable, and locked states when available.
6. Identify the primary user task and current attention hierarchy.

If the app cannot be run, say exactly what could not be verified and base conclusions on code only.

## Audit mode

Do not edit files.

Produce the audit section from `references/review-template.md`. Findings must be concrete and connected to the current UI. For each finding include:

- Surface or component.
- Evidence from code or rendered behavior.
- User or product consequence.
- Severity: `P0`, `P1`, `P2`, or `P3`.
- Recommended direction, not implementation detail unless necessary.

Separate:

- Objective usability/accessibility problems.
- Consistency and maintainability problems.
- Subjective polish opportunities requiring user approval.
- Elements that should remain unchanged.

Conclude with a recommended first implementation slice that is small enough to review.

## Plan mode

Do not edit files.

Use the approved audit or independently inspect the requested scope. Produce the plan section from `references/review-template.md`.

The plan must include:

1. Design goal and primary user task.
2. Current behavior that will be preserved.
3. Exact components/files likely to change.
4. Token or primitive changes, including why they are shared.
5. Page/component changes in implementation order.
6. Responsive and state coverage.
7. Accessibility checks.
8. Test and visual-verification steps.
9. Risks, trade-offs, and explicit non-goals.
10. A checkpoint for user approval before implementation.

Offer at most two meaningful visual directions when a subjective choice is required. Recommend one and explain the difference in product terms.

## Implement mode

Only proceed after the user approved the relevant plan.

### Before editing

- Check the working tree and note unrelated changes; do not overwrite them.
- Re-read the approved plan and identify the smallest complete slice.
- Confirm whether token or primitive changes must land before page-specific changes.

### During editing

- Keep data and interaction logic unchanged unless the approved plan includes a functional correction.
- Use semantic HTML and preserve accessible names.
- Reuse existing components where they remain appropriate.
- Consolidate repeated visual decisions into the smallest sensible token or primitive layer.
- Maintain consistent number formatting, numeric alignment, table density, and state treatment.
- Avoid arbitrary one-off values (such as arbitrary Tailwind values) unless defining a deliberate central token not supported by the existing scale.
- Keep changes scoped. Do not opportunistically restyle unrelated pages.
- Run formatting or lint checks often enough to catch invalid class names, type errors, and markup issues early.

### Implementation checkpoints

After each coherent slice:

1. Inspect the running page.
2. Compare against the approved goal, not merely against the code diff.
3. Check mobile and desktop behavior.
4. Correct regressions before moving to the next slice.

When a rendered result contradicts the plan, stop and explain the trade-off rather than silently changing the design direction.

## Verify mode

Do not introduce new design changes except fixes required to satisfy the approved plan or correct regressions.

Use the verification section from `references/review-template.md`.

Verify:

- Primary visual hierarchy.
- Consistency with the product's established personality.
- Desktop and mobile layouts.
- Keyboard focus and interaction states.
- Text and control contrast.
- Loading, empty, error, locked, unavailable, and populated states.
- Table scanning, sorting cues, numerical alignment, and overflow.
- Long content and large-number behavior.
- No invented data or lost functionality.

Run the frontend's documented lint, test and build commands from its directory, for example:

```text
npm run lint
npm test
npm run build
```

Report the exact result of each command. Do not claim a visual state was checked when it was not available.

## Completion behavior

End each mode with one clear next action:

- Audit: the recommended implementation slice.
- Plan: an explicit approval request.
- Implement: the verification command to run next.
- Verify: pass/fail status and remaining issues.
