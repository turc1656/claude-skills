---
tags: [atdd]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

/atdd specify STORY.md

Use the atdd skill. The story is in STORY.md at the root of this small Python repository (run tests with `uv run pytest`). There is nobody to answer questions during this run: where the skill would interview me, list the questions under Open questions and proceed with your recommended answers.
Input files: pyproject.toml, AGENTS.md, STORY.md, garage/__init__.py, garage/core.py, tests/__init__.py, tests/test_garage.py
