# UI audit and verification checklist

Use only the sections relevant to the requested scope, but do not skip state, responsive, or accessibility review.

## Severity

- `P0`: blocks a core task, creates a serious accessibility failure, or causes loss/misinterpretation of important data.
- `P1`: materially harms usability, hierarchy, responsive behavior, or product credibility.
- `P2`: noticeable inconsistency or polish issue with moderate impact.
- `P3`: optional enhancement or subjective refinement.

## Product and task

- What is the primary task on this surface?
- What information must users notice first, second, and third?
- Is anything visually prominent without helping the task?
- Is any implemented capability hidden or visually understated?
- Does the surface match the product's intended personality?
- Is any decorative element implying urgency, certainty, or functionality that does not exist?

## Hierarchy

- Is there one clear page identity?
- Is there one dominant action per local context?
- Are secondary and tertiary actions quieter?
- Do labels support rather than compete with values?
- Are headings appropriately compact for an application screen?
- Are icons balanced with adjacent text?
- Can the interface's hierarchy be understood in grayscale?

## Typography

- Is the intended project font actually applied?
- Are too many near-identical font sizes or weights in use?
- Is supporting text readable rather than merely tiny?
- Are long lines constrained?
- Are headings using appropriate line height?
- Are mixed-size values and units aligned on a baseline?
- Are uppercase labels short and tracked deliberately?
- Are comparable numbers tabular and consistently formatted?

## Spacing and layout

- Is spacing inside groups tighter than spacing between groups?
- Are any unrelated items visually grouped by equal spacing?
- Is content stretched to fill width without benefit?
- Are form controls, reports, and prose constrained to useful widths?
- Is data density appropriate for the task?
- Are panel paddings and section gaps consistent?
- Does the main content remain more prominent than the sidebar?
- Are nested panels or dividers creating unnecessary visual noise?

## Color, surfaces, and depth

- Does each color have a semantic or brand role?
- Are there repeated arbitrary alpha/color variations that should become tokens?
- Is the brand accent overused?
- Is muted text readable on its actual surface?
- Are semantic states understandable without color?
- Are borders necessary, or would spacing/background contrast work better?
- Are shadows proportional to elevation?
- Are radii consistent with the product's personality?
- Are focus, selected, hover, disabled, and pressed states sufficiently distinct?

## Navigation and shell

- Is the active destination obvious?
- Are inactive items de-emphasized without becoming hard to find?
- Does the sidebar remain stable and uncluttered?
- Does support/disclaimer content compete with navigation?
- Is mobile navigation usable, orienting, and keyboard accessible?
- Does branding remain compact enough for a workspace?

## Page headers

- Are title, eyebrow, description, and action all necessary?
- Is the title proportionate to an application page?
- Is the description concise and width-constrained?
- Is the action the actual primary action?
- Is a border being used where spacing would be enough?
- Does the header wrap gracefully on narrow screens?

## Tables

- Is the most important identity column visually dominant?
- Are numbers right-aligned and tabular?
- Are signs, decimals, currency, percentages, and dates consistent?
- Are sortability and sort direction clear?
- Are sticky headers readable against scrolling content?
- Is row height dense but usable?
- Are supporting details quieter than primary values?
- Do hover and keyboard focus clarify interactivity?
- Are minimum widths deliberate?
- Is horizontal scrolling discoverable and usable?
- Are locked, unavailable, empty, loading, error, and stale states distinct?
- Is upgrade messaging coherent rather than repeated in many cells?
- Do long names and large values avoid clipping or destructive wrapping?

## Forms, tabs, and filters

- Are labels connected to controls?
- Are related controls grouped?
- Are active tabs/filters clear without color?
- Are controls consistent in height, radius, and typography?
- Are focus indicators visible?
- Is there a clear reset path?
- Is the no-results state specific to the active filters?
- Do controls wrap or scroll intentionally at mobile widths?

## Buttons and links

- Is the primary action unique?
- Are secondary and tertiary actions appropriately quiet?
- Are destructive actions proportionate to their current context?
- Are link-dense surfaces avoiding constant brand-color noise?
- Do icon-only actions have accessible names and usable hit areas?
- Are disabled controls distinguishable from muted content?

## Badges, ratings, and movement

- Does each badge communicate a useful category?
- Are badge dimensions and typography consistent?
- Is the text label always present?
- Are positive/negative values indicated by sign or icon as well as color?
- Are neutral and unavailable states explicit?
- Are many rating colors necessary, or can contrast and text reduce noise?

## Dashboard metrics and alerts

- Does each metric answer a real question?
- Does the value dominate the label?
- Is detail useful rather than filler?
- Are identical cards weakening hierarchy?
- Do alerts explain what changed and when?
- Is severity conveyed without color alone?
- Is tone informational rather than alarmist?

## Reports and long-form content

- Is prose within a readable measure?
- Is the table of contents helpful but secondary?
- Are markdown headings visually proportionate?
- Are paragraphs, lists, quotes, tables, and code/data blocks consistent?
- Does active-section navigation remain visible and accessible?
- Are wide tables handled separately from prose width?
- Are long reports usable on mobile?

## States

Check separately where supported:

- initial loading
- incremental loading
- populated
- true empty
- no filter matches
- API error
- unavailable value
- locked access
- stale content
- disabled action
- successful update

For each state:

- Is the state named clearly?
- Is the cause understandable?
- Is the next action available when one exists?
- Is still-usable context preserved?
- Is the layout stable enough to avoid excessive movement?

## Accessibility

- Semantic headings and landmarks remain correct.
- Form controls have labels or accessible names.
- Keyboard order follows visual order.
- Focus is clearly visible.
- Interactive elements are not implemented as noninteractive containers.
- Contrast is sufficient for text, controls, and state indicators.
- Color is never the only cue.
- Table headers and sorting state are announced appropriately.
- Motion is nonessential and reduced-motion aware.
- Mobile touch targets are comfortably usable.

## Responsive widths

Inspect at approximately:

- 390px
- 768px
- 1280px
- 1440px

At each width check:

- shell/navigation
- page-header wrapping
- primary-action placement
- section rhythm
- filter behavior
- table overflow
- long names and messages
- large/negative values
- empty/error/locked states
- focus visibility

## Engineering and regression checks

- Shared primitives are reused where appropriate.
- New abstractions have at least two justified uses or a clear semantic role.
- Visual tokens are centralized rather than scattered.
- Existing types, API behavior, auth, and entitlements are unchanged unless approved.
- No unsupported data or functionality was added.
- No unrelated pages were restyled accidentally.
- The frontend's documented lint, test and build commands pass (for example `npm run lint`, `npm test`, `npm run build`).
