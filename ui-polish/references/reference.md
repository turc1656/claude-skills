# Operational UI rubric

Use this file as the working design rubric while auditing or changing the frontend. When the target repository has its own design principles or style guide, it holds the detailed rationale and wins over this file.

## Product identity

Before judging anything, establish what the product is and how it should feel: who uses it, how often, and for what. Take this from the repository's docs and the current UI, not from taste. A tool used repeatedly every day should feel composed, credible, and useful under that use.

Preserve the established palette and brand unless the user approves a rebrand. The target is a refined version of the same product, not a generic dashboard or a trend-driven restyle.

## Decision order

For every design decision, evaluate in this order:

1. Does it make the primary user task clearer or faster?
2. Does it improve hierarchy or reduce ambiguity?
3. Does it preserve useful information density?
4. Does it improve consistency and reuse?
5. Does it remain accessible and responsive?
6. Only then: does it add visual distinction or delight?

Decoration that fails the first five questions should not be added.

## Feature-first design

Audit real workflows rather than redesigning the application shell in isolation. List the product's actual workflows first, for example:

- Find and compare items.
- Read and navigate a detail page or document.
- Evaluate the key attributes of an item.
- Manage a saved list or collection.
- Recognize changes and alerts.
- Understand access and locked content.

Do not imply functionality the product does not support.

## Hierarchy

- Determine primary, secondary, and tertiary content for the scope.
- Reduce competition before making the primary element louder.
- Use weight and contrast before large size changes.
- Keep labels subordinate to values unless users scan for the label.
- Keep application headings compact.
- Use one dominant action per local context.
- Make active navigation obvious; make inactive navigation quieter.

Red flags:

- Every item uses bright text.
- Several buttons have equal visual weight.
- Page title, filters, metrics, and content all compete.
- Supporting copy is tiny rather than simply muted.
- Icons attract more attention than their labels.

## Spacing and grouping

- Use a constrained spacing scale.
- Space within a group must be tighter than space around the group.
- Begin with enough breathing room, then deliberately compress information-dense surfaces.
- Do not force controls or text to fill wide screens.
- Keep forms and prose at appropriate max-widths.
- Give sidebars and controls stable content-driven widths.

Red flags:

- Equal gaps between labels/controls and separate control groups.
- Full-width paragraphs on wide screens.
- Tables padded like marketing cards.
- Unrelated items appear grouped because spacing is ambiguous.
- Arbitrary values differ by one or two pixels without semantic meaning.

## Typography

- Use the project's intended sans-serif consistently.
- Keep a small application type scale.
- Use regular/medium and semibold/bold as the main weights.
- Avoid lightweight small text.
- Keep long-form prose within a readable measure.
- Tighten line height as text size increases.
- Left-align explanatory content longer than a few lines.
- Align mixed-size text on a baseline.
- Use increased tracking only for short uppercase metadata.
- Use tabular figures for comparable numeric values.

Red flags:

- Browser fallback font overrides the loaded project font.
- Many near-identical font sizes.
- Excessive uppercase metadata.
- Very long prose lines.
- Oversized page headings inside application screens.
- Monospace used broadly for aesthetic reasons rather than data alignment.

## Color

Use role-based colors:

- page
- sidebar
- surface
- raised surface
- hover/selected surface
- strong/normal/muted/disabled text
- subtle/strong border
- brand accent
- positive/neutral/caution/negative/info/locked

Rules:

- Use semantic scales, not many scattered alpha variations.
- Avoid pure black and pure white for ordinary surfaces and text.
- Choose supporting text colors for their actual background.
- Do not use color as the only state cue.
- Reserve the brand accent for important interactions and selected states.
- Prefer tinted semantic surfaces with readable text over visually dominant saturated blocks.

Red flags:

- Every link and icon uses the brand accent.
- Positive and negative values differ only by red/green.
- Selected and hover states are barely perceptible.
- Muted text looks disabled.
- New arbitrary hex values appear throughout components.

## Depth, borders, and radii

Use the lightest effective separator:

1. spacing
2. background difference
3. subtle shadow
4. border

- Standard panels should not all look like floating modal cards.
- Use stronger elevation for popovers and modals.
- Keep light direction internally consistent.
- Use small-to-moderate radii on application surfaces.
- Full pills are for badges and pill controls.
- Do not stack strong border, shadow, gradient, and glow on one component.

## Tables and numeric data

Tables should support fast comparison:

- Keep headers compact and sticky when valuable.
- Right-align numbers.
- Use tabular figures.
- Standardize currency, signs, precision, percentages, and dates.
- Emphasize the column that identifies each row.
- De-emphasize secondary names, timestamps, and freshness details appropriately.
- Make sort direction and interactive rows clear without color alone.
- Preserve useful density.
- Keep minimum column widths; use horizontal scrolling rather than unreadable compression.
- Consider combining related values only when independent sorting is unnecessary.
- Distinguish locked, unavailable, loading, empty, error, and stale states.

Locked rows should demonstrate available value without looking broken. Avoid repeating an upgrade message in many cells if a coherent row-level disclosure is clearer.

## Controls and actions

- Primary action: solid, high contrast, limited use.
- Secondary action: clear but quieter surface or outline.
- Tertiary action: text/icon treatment.
- Destructive action: dominant only in its confirmation context.
- Keep heights, radii, type, focus, and disabled states consistent.
- Connect labels to controls spatially and semantically.
- Selected tabs and filters must remain obvious without color.
- Provide a reset path for filter-generated empty states.

## App shell

- Keep main content more prominent than the sidebar.
- Keep brand and navigation clear but compact.
- Use a clear active-navigation pattern.
- De-emphasize legal/support content.
- Prevent mobile navigation from becoming an equal-weight list of crowded links.
- Preserve orientation as users move between pages.

## Panels and dashboard metrics

- Use panels for meaningful groups, not every element.
- Avoid nested card-on-card layouts.
- Let related items share a surface and use spacing or subtle dividers.
- Metric values dominate labels.
- Every metric must answer a real product question.
- Do not repeat identical cards when a different composition creates stronger hierarchy.

## Long-form content

- Reading and section navigation are the priority.
- Keep prose narrower than data tables.
- Style markdown headings according to the interface, not raw HTML defaults.
- Maintain predictable heading and paragraph rhythm.
- Keep table of contents navigation useful but secondary.
- Treat tables, lists, quotes, and metadata as one editorial system.

## States

Design these separately:

- loading
- empty
- no filter matches
- error
- unavailable data
- locked access
- stale data
- disabled action
- successful update

Each state should explain what happened and, when possible, what the user can do next. Hide controls that are meaningless in a true empty state.

## Responsive verification

At minimum inspect approximately:

- 390px mobile
- 768px intermediate
- 1280px desktop
- 1440px wide desktop

Check:

- navigation
- page headers and actions
- filter wrapping/overflow
- table behavior
- long names
- long error text
- large and negative values
- empty and locked states
- long-form prose and table of contents

Do not make mobile look clean by removing essential context without an approved alternative.

## Restrained visual distinction

Good opportunities:

- active-navigation accent
- refined status and trend indicators
- subtle summary emphasis
- carefully framed empty states
- consistent numerical typography
- quiet marketing background decoration
- selective accent borders

Avoid:

- glass panels everywhere
- neon glow
- constant gradients
- ornamental charts
- motion that implies urgency
- huge rounded cards
- multiple competing accents
- unreadably low-contrast text

## Acceptance test

A design change is successful when:

- The primary task is clearer.
- The interface still feels like the same product.
- Important information is easier to scan.
- Secondary content is quieter but readable.
- Density remains appropriate for the task.
- Tokens and primitives become more consistent.
- All supported states remain intentional.
- Accessibility and responsive behavior do not regress.
- No functionality or data meaning changes unintentionally.
