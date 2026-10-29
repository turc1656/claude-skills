---
name: git-commit-message
description: Generate detailed, meaningful Git commit messages using Conventional Commits, based on supplied diffs or current repository changes.
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git rev-parse *)
metadata:
  version: "1.0.0"
---

# Git Commit Message Generator

Generate a detailed, meaningful Git commit message based on the
changes supplied by the user or detected in the current repository.

Follow all conventions below. The goal is to produce a professional,
informative commit message that clearly documents what changed and
why, providing enough detail for future developers to understand
the commit without having to examine the entire diff.

## 1. Determine the Changes

### When the user supplies a diff

If the user provides a Git diff or description of changes, use that
information as the primary source.

Do not automatically substitute unrelated repository changes for
the supplied content.

### When no diff is supplied

Automatically inspect the current Git repository:

1. Verify that the working directory is a Git repository using
   `git rev-parse --is-inside-work-tree`.
2. Run `git status --short` to identify modified, staged, and
   untracked files.
3. First inspect staged changes using `git diff --cached`.
4. If staged changes exist, generate the message using ONLY the
   staged changes. Do not include unstaged modifications.
5. If no changes are staged, inspect unstaged tracked changes
   using `git diff`.
6. If only untracked files exist, inspect their contents using
   read-only tools when available. Clearly indicate that the
   files are untracked and the proposed message is provisional.
7. If no changes are found, inform the user rather than
   inventing a commit message.

For large diffs, inspect the relevant changes and their context
rather than relying solely on filenames or diff statistics.

If the available information is incomplete, avoid making
unsupported claims.

### Safety requirements

- NEVER execute `git commit`.
- NEVER execute `git add` or stage files.
- NEVER modify, create, delete, or reset repository files.
- NEVER modify Git history or repository configuration.
- Use read-only commands exclusively.
- Generate the commit message for the user to review and copy.

## 2. Conventional Commit Structure

Follow the Conventional Commits format:

<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

### Header (Required)

Rules:

- Maximum length: 50 characters, including type and scope.
- Format: `<type>: <description>` or
  `<type>(scope): <description>`.
- Type must always be lowercase.
- Description must begin with a lowercase letter.
- Use imperative mood.
- Do not end with a period.
- Be concise but descriptive.
- Describe the primary purpose of the commit.

The description should complete the sentence:

"If applied, this commit will..."

Examples:

Correct:
- `feat: add user authentication`
- `fix(auth): handle expired tokens`
- `refactor(api): simplify response handling`

Incorrect:
- `feat: Added user authentication`
- `Fix: Handle expired tokens`
- `feat: add user authentication.`
- `feat: Add User Authentication`

### Common Commit Types

| Type | Meaning |
|------|---------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation changes |
| style | Code formatting without logic changes |
| refactor | Code restructuring without feature or bug changes |
| test | Adding or updating tests |
| chore | Maintenance tasks or build changes |
| perf | Performance improvements |
| ci | CI/CD configuration changes |
| revert | Reverting previous commits |

Select the type that best represents the primary purpose.

Do not use `feat` simply because many files were changed.

### Optional Scope

Use a scope when it meaningfully identifies the affected
component, module, or subsystem.

Examples:

- `feat(auth): add OAuth login`
- `fix(database): handle connection timeouts`
- `refactor(parser): simplify token handling`

Scopes should be concise, lowercase, and consistent with
the project's terminology when possible.

Do not force a scope when none is appropriate.

## 3. Commit Body

The body is technically optional under Conventional Commits,
but this skill should generally produce a detailed body for
meaningful code changes.

### Formatting

- Separate the header from the body with one blank line.
- Wrap body text at approximately 72 characters.
- Use bullets for distinct changes when appropriate.
- Use paragraphs to explain broader motivations or impacts.
- Use descriptive sections for larger or multifaceted changes.
- Maintain consistent formatting throughout the message.

### Content

Explain:

1. WHAT changed.
2. WHY the change was necessary or beneficial.
3. WHAT important behavior, capability, or limitation changed.
4. WHICH major components were affected, when relevant.

Prioritize what and why over low-level implementation details.

However, include meaningful technical details when they improve
the commit's usefulness, particularly for complex changes.

Do not simply repeat the filenames or restate every line
of the diff.

### Detail Level

Favor comprehensive, informative commit messages over
minimal summaries.

For substantial changes:

- Describe the major modifications individually.
- Include important new functionality or behavior.
- Identify significant refactoring or architectural changes.
- Describe relevant validation, error handling, or safeguards.
- Mention meaningful test additions or updates.
- Explain compatibility considerations when applicable.
- Summarize the overall benefit or motivation.

For simple changes, remain appropriately concise.

Do not artificially inflate minor commits with unnecessary
sections, repetitive bullets, or obvious implementation details.

The amount of detail should reflect the complexity and
significance of the changes.

### Accuracy

- Never invent functionality that is not supported by the diff.
- Never claim tests passed unless execution results confirm it.
- Never invent performance improvements or numerical results.
- Never assume a bug was fixed beyond what the changes establish.
- Never invent issue numbers, requirements, or motivations.
- Distinguish verified results from intended behavior.
- Describe actual changes rather than speculative benefits.

## 4. Commit Footer

Include optional footers when appropriate.

### Issue References

Examples:

Fixes #123
Closes #456
Refs #789

Only reference issues when their identifiers and relationships
are known.

### Breaking Changes

When a change introduces a confirmed breaking change, include:

BREAKING CHANGE: description of the incompatible behavior

Explain the compatibility impact and any necessary migration
or adaptation.

Do not label a change as breaking without sufficient evidence.

### Co-Authors

When explicitly supplied or established:

Co-authored-by: Name <email>

Never invent contributor names or email addresses.

## 5. Multi-File and Complex Changes

When changes span multiple files or subsystems:

1. Identify the primary objective of the overall change.
2. Group related modifications logically.
3. Use the header to summarize the overall purpose.
4. Use the body to describe the significant components.
5. Explain how related changes contribute to the objective.
6. Include noteworthy tests, safeguards, and compatibility
   considerations.

Avoid generating an unrelated list of file modifications.

The commit message should tell a coherent story about
the change.

If the changes appear unrelated, still produce a message
accurately describing the changes, but briefly mention
that separate commits might improve the history.

Do not split commits or modify staging automatically.

## 6. Output Requirements

Output ONLY the completed Git commit message.

- Present it in a single copyable text code block.
- Do not include introductory commentary.
- Do not include an explanation of the selected commit type.
- Do not include alternative messages unless requested.
- Do not include Git commands for staging or committing.
- Do not include unsupported claims.
- Ensure the header satisfies the 50-character limit.
- Ensure the body follows the 72-character wrapping guideline.

The examples below demonstrate the preferred style,
level of detail, and structure.

IMPORTANT: Explicit formatting rules take precedence over
examples if any inconsistency exists.

---

# Examples

## Example 1: Search Result Filtering

feat(search): exclude archived records

- Extend filter expression building to support multiple conditions.
- Add a mandatory filter to exclude records whose `archived_at`
  is set.
- Refactor the single `created_after` filter into a list-based
  approach.
- Combine multiple filter expressions using AND logic.

This ensures search results include only active records,
improving result quality and preventing archived items from
appearing in downstream views.

---

## Example 2: Comprehensive Feature Enhancement

feat(reports): add sales trend visualization

Enhance the sales reporting module with interactive analysis,
order detail retrieval, and additional cache safeguards.

Key Changes:

Data Visualization & Analysis:
- Add Plotly as a dependency in `pyproject.toml` and `uv.lock`.
- Implement `build_trend_html()` to generate interactive
  HTML charts comparing current and prior-period sales.
- Add dropdown navigation and previous/next controls.
- Add `orders_to_dataframe()` to convert `OrderSummary`
  objects into pandas DataFrames.
- Include statistical analysis of order values, regional
  distributions, and date ranges.

Order Data Access:
- Add an `order_id` field to the `OrderSummary`
  dataclass for detail lookups.
- Implement `get_line_items_by_ids()` and
  `extract_line_items_from_summaries()` to retrieve
  line items for selected orders.
- Update `query_orders()` to include order IDs in output fields.

Date Filtering:
- Add a `since` parameter to `query_orders()` for date
  filtering.
- Implement date-based filtering through SQL `WHERE` clauses.

Safety Features:
- Add a `purge_report_cache()` helper with deletion safeguards.
- Require an explicit manual override before enabling
  destructive cache operations.

Testing & Demo:
- Extend the main test script with DataFrame conversion
  and statistical analysis.
- Add interactive chart generation for the top
  10 products.
- Include a date-filtering example.

These changes expand the reporting module's analytical
capabilities while preserving compatibility with existing
query workflows.

---

## Example 3: New Session Store

feat(cache): implement session store with Redis

Introduce a reusable session store backed by Redis for
persisting user sessions across application instances.

Key Changes:

Store Interface:
- Add `src/session_store.py` as a reusable session module.
- Define a `Session` dataclass containing user IDs,
  creation and expiry times, and optional metadata.
- Include optional fields for roles and preferences.

SessionStore Implementation:
- Load connection settings from environment variables
  using `python-dotenv`.
- Support `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, and
  `SESSION_TTL`.
- Implement connection pooling and key namespacing.
- Add configurable `get()` and `save()` methods supporting
  custom serializers and expiry times.
- Add `get_store_stats()` to retrieve key counts
  and memory usage.

Testing & Demonstration:
- Add a `__main__` test harness for exercising the
  store interface.
- Print store statistics during test execution.
- Create and expire a sample session for
  demonstration.
- Display retrieved sessions and their remaining lifetime.

Reliability & Maintainability:
- Handle invalid inputs, connection failures, and
  serialization errors.
- Include comprehensive docstrings and type annotations.
- Design the interface for future extension.

This establishes a reusable foundation for session
persistence across application instances, supporting
horizontal scaling and later authentication work.

---

## Example 4: Database Schema and Import Updates

feat(db): add delivery status fields

Extend the orders table schema and the order import
pipeline to record delivery progress across every stage.

Key Changes:

Table Schema:
- Add `shipped_at`, `out_for_delivery_at`, `delivered_at`,
  and `returned_at` fields for tracking each stage of an
  order's delivery.
- Add `create_orders_table()` to initialize
  tables using the updated schema.

Data Import:
- Update `OrderImporter.load_batch()` to require a
  carrier tracking number before recording delivery stages.
- Parse carrier timestamps defensively, skipping malformed
  values and recording NULL where appropriate.
- Insert delivery-stage values alongside existing
  order data in bulk.

Persistence:
- Disable the legacy CSV export path for
  imported orders.
- Rely on database transactions for import durability.

Initialization:
- Update the main entry point to create the revised
  table schema before importing orders.

These changes let the order pipeline retain delivery
progress for every stage, providing the data needed for
delivery-time reporting and customer notifications.

---

# Final Validation Checklist

Before returning the message, verify:

1. The header uses a valid Conventional Commit type.
2. The entire header is 50 characters or fewer.
3. The description begins with a lowercase letter.
4. The description uses imperative mood.
5. The header does not end with a period.
6. The scope is appropriate, if included.
7. The body is separated from the header by a blank line.
8. The body is wrapped at approximately 72 characters.
9. The message explains what changed and why.
10. The level of detail matches the complexity of the diff.
11. Important changes are not omitted.
12. No unsupported claims or invented issue references appear.
13. Breaking changes are documented when established.
14. Only the intended changes are described.
15. No repository modifications or commits were performed.

Return the completed message without additional commentary.