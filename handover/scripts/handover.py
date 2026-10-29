#!/usr/bin/env python3
"""Handover helper: reserves a handover folder, snapshots the workspace, validates the result.

A handover lives in its own folder:
  ~/.claude/handovers/<project>/<YYYY-MM-DD_HHMMSS>_<slug>/   by default
  <dir>/<YYYY-MM-DD_HHMMSS>_<slug>/                           with --to <dir>
holding .handover.json (the status), handover.md (the core document),
resume-prompt.txt, and optionally appendix.md and files/. `reserve` writes the
status as in-progress; only a passing `check` sets it to complete, and `status`
reports a complete handover whose files changed after its check as
changed-since-check.

`check` fails on: missing files or headings; an empty required section or no numbered
first action; a Workspace without its "Uncommitted work at risk:" and "Running
processes:" lines; a `files/...` path that is not a regular file copied in; a resume
prompt whose verify command is missing, names a helper that does not exist, or targets
any folder but this one; an active workflow whose prompt would not resume it;
a secret-shaped string; any file it could not scan; any symbolic link or junction in the
folder (rejected before anything is read, so nothing outside the folder is read or hashed).

Commands (--cwd DIR is the working folder; default: the current directory):
  status   --session ID [--to DIR]             this session's handovers, unfinished first
  reserve  --session ID [--to DIR] [--slug S]  create a new folder, never reusing one
  snapshot [--session ID]                      header facts and the Git block, as Markdown
  check    FOLDER                              exit 0 and mark complete, or exit 1 and list problems
  verify   FOLDER                              exit 0 only while every file matches its passing
                                               check; the receiving session runs this first,
                                               because .handover.json alone can be stale
  --self-test                                  run the regression tests in test_handover.py

Read-only on the project: Git is only queried, with optional locks off, so even
`git status` leaves the index alone. Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".claude" / "handovers"
STATUS_FILE = ".handover.json"
CORE_FILE = "handover.md"
PROMPT_FILE = "resume-prompt.txt"
MAX_LISTED_PATHS = 30
MAX_SCAN_BYTES = 20_000_000  # a larger file fails the check instead of being skipped by the secret scan
RECENT_COMMITS = 5
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
REQUIRED_HEADINGS = [
    ("# Handover: <task>", r"^# Handover: "),
    ("## 1. Resume here", r"^## 1\. Resume here"),
    ("## 2. Waiting on you", r"^## 2\. Waiting on you"),
    ("## 3. Decisions and constraints", r"^## 3\. Decisions and constraints"),
    ("## 4. Work state", r"^## 4\. Work state"),
    ("## 5. Verification", r"^## 5\. Verification"),
    ("## 6. Workspace", r"^## 6\. Workspace"),
    ("## 7. References", r"^## 7\. References"),
]
REQUIRED_LINES = [  # (section, label): must-keep items stated explicitly in the core, even as "none"
    ("6", "Uncommitted work at risk:"),
    ("6", "Running processes:"),
]
VERIFY_SPAN = re.compile(r"`([^`]*handover\.py[\"']?\s+verify\s[^`]*)`")
SCRATCH_REFERENCE = re.compile(r"`(files/[^`]+)`|(?<![\w/.\\-])(files/[^\s`'\"()<>\[\],;]+)")
SECRET_PATTERNS = {
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "sk- API key": r"\bsk-[A-Za-z0-9_-]{20,}",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "JWT": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "credential assignment": (
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
        r"\s*[:=]\s*['\"]?[^\s'\"<>`]{8,}"
    ),
}
OPERATIONS = [  # marker in the Git directory -> operation in progress
    ("rebase-merge", "rebase"), ("rebase-apply", "rebase or am"), ("MERGE_HEAD", "merge"),
    ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert"), ("BISECT_LOG", "bisect"),
]


# --- small helpers -------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_name(text: str, fallback: str) -> str:
    """A folder-name-safe version of text: letters, digits, dot, dash, underscore; at most 40 chars."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-.")[:40].strip("-.")
    return name or fallback


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess | None:
    """Run a read-only Git query; None when Git is missing or hangs."""
    try:
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(cwd), *args], capture_output=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def git_text(cwd: Path, *args: str) -> str | None:
    result = git(cwd, *args)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace").strip()


def project_root(cwd: Path) -> tuple[Path, bool]:
    """The Git top level, or the working folder itself when there is no repository."""
    top = git_text(cwd, "rev-parse", "--show-toplevel")
    return (Path(top), True) if top else (cwd.resolve(), False)


def handover_base(cwd: Path, to: str | None) -> Path:
    if to:
        return Path(to).expanduser()
    root, _ = project_root(cwd)
    return DEFAULT_ROOT / safe_name(root.name, "project")


def read_status(folder: Path) -> dict | None:
    if is_link(folder / STATUS_FILE):
        return None
    try:
        data = json.loads((folder / STATUS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_status(folder: Path, data: dict) -> None:
    """Write through a temporary file and an atomic rename, so a reader never sees half a file."""
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".handover.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, folder / STATUS_FILE)


def check_session(session: str) -> str:
    if not SESSION_ID.match(session):
        sys.exit(f"error: not a session id: {session!r}")
    return session


def answers(test, path: Path) -> bool:
    """A path test on a name taken from the handover text; False, not an error, for an unusable name.

    Before Python 3.12, Path.exists() and friends raise on Windows for names such as '<path>'.
    """
    try:
        return bool(test(path))
    except (OSError, ValueError):
        return False


def is_link(path: Path) -> bool:
    """A symbolic link, or on Windows a junction: anything that can lead outside the folder.

    Junctions are read from the reparse tag in lstat, which every supported Python has on
    Windows; Path.is_junction() exists only from 3.12. Other reparse points (cloud-file
    placeholders, for example) are ordinary files and are not treated as links.
    """
    if path.is_symlink():
        return True
    try:
        tag = getattr(os.lstat(path), "st_reparse_tag", 0)
    except OSError:
        return False
    return tag == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1)


def walk(folder: Path) -> tuple[list[Path], list[str]]:
    """The regular files in a handover folder, and the links found in it. Links are never followed."""
    files: list[Path] = []
    links: list[str] = []
    for current, dirs, names in os.walk(folder):
        here = Path(current)
        for name in list(dirs):
            if is_link(here / name):
                links.append((here / name).relative_to(folder).as_posix())
                dirs.remove(name)
        for name in names:
            path = here / name
            if is_link(path):
                links.append(path.relative_to(folder).as_posix())
            elif path.is_file():
                files.append(path)
    return sorted(files), sorted(links)


def digests(folder: Path) -> dict[str, str]:
    """SHA-256 of every regular file, hidden ones included, except the top-level status file; links as 'link'."""
    files, links = walk(folder)
    result = {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
        if path != folder / STATUS_FILE
    }
    result.update({rel: "link" for rel in links})
    return result


def verify(folder: Path) -> tuple[str, list[str]]:
    """The status a reader can trust: complete only while every file still matches its passing check."""
    data = read_status(folder)
    if data is None:
        return "not-a-handover", [f"no readable {STATUS_FILE}"]
    status = data.get("status", "?")
    checked = data.get("checked") or {}
    if status != "complete":
        return status, checked.get("problems") or ["check has not passed yet"]
    recorded = checked.get("files") or {}
    current = digests(folder)
    changes = [f"{rel} changed" for rel in sorted(recorded) if rel in current and current[rel] != recorded[rel]]
    changes += [f"{rel} removed" for rel in sorted(recorded) if rel not in current]
    changes += [f"{rel} added" for rel in sorted(current) if rel not in recorded]
    return ("changed-since-check", changes) if changes else ("complete", [])


def effective_status(folder: Path) -> str:
    return verify(folder)[0]


# --- status and reserve ----------------------------------------------------------------------

def find_handovers(base: Path, session: str) -> list[tuple[Path, str]]:
    """This session's handovers under base with their effective status: unfinished first, then newest first."""
    if not base.is_dir():
        return []
    found = []
    for folder in base.iterdir():
        data = read_status(folder) if folder.is_dir() else None
        if data and data.get("session") == session:
            found.append((folder, effective_status(folder)))
    found.sort(key=lambda item: item[0].name, reverse=True)
    found.sort(key=lambda item: item[1] == "complete")
    return found


def reserve(base: Path, session: str, slug: str, cwd: Path, when: datetime | None = None) -> Path:
    """Create a brand-new handover folder; an existing folder is never reused or written into."""
    when = when or datetime.now().astimezone()
    root, _ = project_root(cwd)
    base.mkdir(parents=True, exist_ok=True)
    name = f"{when.strftime('%Y-%m-%d_%H%M%S')}_{safe_name(slug, 'handover')}"
    for attempt in range(1, 100):
        folder = base / (name if attempt == 1 else f"{name}-{attempt}")
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        write_status(folder, {
            "schema": 1,
            "session": session,
            "created": when.isoformat(timespec="seconds"),
            "status": "in-progress",
            "project_root": str(root),
            "cwd": str(cwd.resolve()),
            "checked": None,
        })
        return folder
    sys.exit(f"error: no free folder name for {name} under {base}")


# --- snapshot --------------------------------------------------------------------------------

def parse_porcelain(raw: bytes) -> tuple[dict, list[tuple[str, str]]]:
    """Parse `git status --porcelain=v2 --branch -z` into branch headers and (XY, path) entries."""
    tokens = raw.decode("utf-8", "replace").split("\0")
    headers: dict[str, str] = {}
    entries: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if not token:
            continue
        if token.startswith("# "):
            key, _, value = token[2:].partition(" ")
            headers[key] = value
        elif token[0] in "12u":
            parts = token.split(" ")
            path_start = {"1": 8, "2": 9, "u": 10}[token[0]]
            path = " ".join(parts[path_start:])
            if token[0] == "2":  # a rename or copy: the original path follows as its own token
                path = f"{tokens[i]} -> {path}"
                i += 1
            entries.append(("UU" if token[0] == "u" else parts[1], path))
        elif token[0] == "?":
            entries.append(("??", token[2:]))
    return headers, entries


def git_block(root: Path) -> list[str]:
    status = git(root, "status", "--porcelain=v2", "--branch", "-z")
    if status is None or status.returncode != 0:
        return ["- Git status could not be read."]
    headers, entries = parse_porcelain(status.stdout)
    lines = []

    head = headers.get("branch.head", "?")
    oid = headers.get("branch.oid", "")
    if oid == "(initial)":
        lines.append(f"- Branch: `{head}` (no commits yet)")
    elif head == "(detached)":
        lines.append(f"- Branch: detached HEAD at `{oid[:7]}`")
    else:
        upstream = headers.get("branch.upstream")
        if upstream:
            ab = headers.get("branch.ab", "+0 -0").split()
            lines.append(f"- Branch: `{head}` | upstream `{upstream}` (ahead {ab[0][1:]}, behind {ab[1][1:]})")
        else:
            lines.append(f"- Branch: `{head}` | no upstream")
    if oid != "(initial)":
        lines.append(f"- HEAD: `{git_text(root, 'log', '-1', '--format=%h %s') or oid[:7]}`")

    git_dir = git_text(root, "rev-parse", "--absolute-git-dir")
    if git_dir:
        ops = [label for marker, label in OPERATIONS if (Path(git_dir) / marker).exists()]
        lines.append(f"- Operation in progress: {', '.join(ops) if ops else 'none'}")

    tracked = [xy for xy, _ in entries if xy not in ("??", "UU")]
    lines.append(
        f"- Changes: {sum(xy[0] != '.' for xy in tracked)} staged | "
        f"{sum(xy[1] != '.' for xy in tracked)} unstaged | "
        f"{sum(xy == '??' for xy, _ in entries)} untracked | "
        f"{sum(xy == 'UU' for xy, _ in entries)} conflicted"
    )
    stashes = git_text(root, "stash", "list") or ""
    lines.append(f"- Stash entries: {len(stashes.splitlines())}")

    if entries and len(entries) <= MAX_LISTED_PATHS:
        lines.append("- Changed paths (XY: staged, unstaged; ?? untracked):")
        lines += [f"  - `{xy}` {path}" for xy, path in entries]
    elif entries:
        groups: dict[str, int] = {}
        for _, path in entries:
            top = path.split("/", 1)[0] + ("/" if "/" in path else "")
            groups[top] = groups.get(top, 0) + 1
        lines.append(f"- Changed paths: {len(entries)}, grouped by top folder:")
        lines += [f"  - {top}: {count}" for top, count in sorted(groups.items())]

    if oid != "(initial)":
        log = git_text(root, "log", f"-{RECENT_COMMITS}", "--format=%h %s") or ""
        lines.append("- Recent commits:")
        lines += [f"  - `{line}`" for line in log.splitlines()]
    return lines


def transcript_path(session: str) -> Path | None:
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    matches = sorted((config / "projects").glob(f"*/{session}.jsonl"))
    return matches[0] if matches else None


def snapshot(cwd: Path, session: str | None) -> str:
    root, in_git = project_root(cwd)
    lines = [
        f"- Date: {now_iso()}",
        f"- Working folder: `{cwd.resolve()}`",
        f"- Project: `{root.name}` | root `{root}`",
    ]
    if session:
        found = transcript_path(session)
        lines.append(f"- Session: `{session}` | transcript {f'`{found}`' if found else 'not found'}")
    if os.environ.get("CLAUDE_CODE_REMOTE"):
        lines.append("- Environment: cloud session (files outside the repository will not survive it)")
    lines.append("")
    lines.append("**Git**")
    lines += git_block(root) if in_git else ["- No Git repository."]
    return "\n".join(lines)


# --- check -----------------------------------------------------------------------------------

def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def workflow_problems(core: str, prompt: str, root: Path) -> list[str]:
    """When the core names an active workflow, the prompt must resume it, not start a new one."""
    if not re.search(r"^\*\*Active workflow\*\*", core, re.M):
        return []
    problems = []
    command_line = re.search(r"^\s*-\s*Resume command:\s*(.+?)\s*$", core, re.M)
    if not command_line:
        problems.append("the Active workflow block has no 'Resume command:' line")
    elif command_line.group(1).strip("`").lower().startswith("none"):
        if first_line(prompt).startswith("/"):
            problems.append("the resume command is 'none', but resume-prompt.txt starts with a slash command")
    else:
        quoted = re.match(r"`([^`]+)`", command_line.group(1))
        command = quoted.group(1).strip() if quoted else ""
        if not command.startswith("/"):
            problems.append("the resume command must be a slash command in backticks, or 'none'")
        elif len(command.split()) < 2:
            problems.append(
                f"the resume command `{command}` is the bare skill name: use the skill's own resume form "
                "(its mode and state identifier), or 'none' when the skill has no resume form"
            )
        if command and first_line(prompt) != command:
            problems.append("the first line of resume-prompt.txt must be exactly the resume command")
    if not (re.search(r"(?i)resume the existing", prompt) and re.search(r"(?i)do not start a new", prompt)):
        problems.append("resume-prompt.txt lacks 'Resume the existing <skill> workflow ...; do not start a new one'")
    if not re.search(r"(?i)stop and ask me to run", prompt):
        problems.append("resume-prompt.txt lacks the stop-and-ask sentence ('stop and ask me to run ...')")
    state = re.search(r"State file:\s*`([^`]+)`", core)
    if not state:
        problems.append("the Active workflow block has no 'State file: `<path>`'")
    else:
        path = Path(state.group(1)).expanduser()
        if not answers(Path.exists, path if path.is_absolute() else root / path):
            problems.append(f"the state file does not exist: {state.group(1)}")
    return problems


def split_sections(core: str) -> dict[str, str]:
    """The body of each '## N. Title' section, keyed by N."""
    parts = re.split(r"^## (\d+)\. [^\n]*\n?", core, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


@functools.lru_cache(maxsize=1)
def template_lines() -> frozenset[str]:
    """Every line of the core template in references/template.md, as written there."""
    path = Path(__file__).resolve().parent.parent / "references" / "template.md"
    try:
        block = path.read_text(encoding="utf-8").split("```markdown\n", 1)[1].split("\n```", 1)[0]
    except (OSError, IndexError):
        return frozenset()
    return frozenset(line.strip() for line in block.splitlines() if line.strip())


def placeholder_only(line: str) -> bool:
    """True for a template line left as written, or one with nothing but bullets, a 'Label:' and <...>."""
    text = line.strip()
    if text in template_lines():
        return True
    while True:  # innermost first, so nested placeholders such as <run /x <feature>> go too
        stripped = re.sub(r"<[^<>]*>", "", text)
        if stripped == text:
            break
        text = stripped
    text = re.sub(r"^[-*\d.\s]*", "", text)
    text = re.sub(r"^[^:<>`]{1,40}:", "", text)
    return not re.search(r"[A-Za-z0-9]", text)


def substantive(text: str) -> bool:
    """True when text holds at least one line that is more than an unfilled template line."""
    return any(not placeholder_only(line) for line in text.splitlines() if line.strip())


def content_problems(core: str) -> list[str]:
    """Headings alone are not a handover: each required section and must-keep line needs content."""
    problems = []
    bodies = split_sections(core)
    for label, _ in REQUIRED_HEADINGS[1:]:
        number = label.split()[1].rstrip(".")
        if number in bodies and not substantive(bodies[number]):
            problems.append(f"handover.md: section '{label[3:]}' is empty (write its content, or 'none')")
    actions = re.search(r"\*\*First actions\*\*(.*?)(?=^\*\*|\Z)", bodies.get("1", ""), re.S | re.M)
    if actions and not any(re.match(r"\s*\d+\.\s+\S", line) and not placeholder_only(line)
                           for line in actions.group(1).splitlines()):
        problems.append("handover.md: '**First actions**' has no numbered action")
    for number, label in REQUIRED_LINES:
        line = re.search(rf"^\s*-?\s*{re.escape(label)}(.*)$", bodies.get(number, ""), re.M)
        if not line or not substantive(line.group(1)):
            problems.append(f"handover.md: section {number} needs '{label} <what, or none>'")
    return problems


def scratch_problems(folder: Path, texts: dict[str, str], files: list[Path]) -> list[str]:
    """Every `files/...` path the handover names must be a regular file copied into its files/ folder."""
    present = {path.relative_to(folder).as_posix() for path in files}
    problems = []
    for name, text in texts.items():
        for match in SCRATCH_REFERENCE.finditer(text):
            ref = (match.group(1) or match.group(2)).rstrip(".:;,)")
            if ref.rstrip("/") == "files":
                continue
            normal = os.path.normpath(ref).replace("\\", "/")  # lexical only: links are never followed
            if not normal.startswith("files/"):
                problem = f"{name} names {ref}, which points outside files/"
            elif normal not in present:
                problem = f"{name} names {ref}, which is not a file in the handover folder"
            else:
                continue
            if problem not in problems:
                problems.append(problem)
    return problems


def verify_command_problems(prompt: str, folder: Path) -> list[str]:
    """The prompt's verify command must run a helper that exists against this very handover folder."""
    span = VERIFY_SPAN.search(prompt)
    if not span:
        return ['resume-prompt.txt lacks the verify command, in backticks: '
                'python "<helper dir>/handover.py" verify "<folder>"']
    try:
        tokens = [token.strip("\"'") for token in shlex.split(span.group(1), posix=False)]
    except ValueError:
        return ["the verify command in resume-prompt.txt could not be parsed; quote each path"]
    at = next((i for i, token in enumerate(tokens)
               if token.endswith("handover.py") and tokens[i + 1:i + 2] == ["verify"]), None)
    if at is None or len(tokens) < at + 3:
        return ["the verify command in resume-prompt.txt names no folder"]
    helper, target = Path(tokens[at]).expanduser(), Path(tokens[at + 2]).expanduser()
    problems = []
    if not answers(Path.is_file, helper):
        problems.append(f"the verify command's helper does not exist: {tokens[at]}")
    if not (answers(Path.is_dir, target) and answers(lambda p: os.path.samefile(p, folder), target)):
        problems.append(f"the verify command targets {tokens[at + 2]}, not this handover folder")
    return problems


def secret_findings(folder: Path, files: list[Path]) -> list[str]:
    """Pattern hits as 'file:line (kind)', plus every file that could not be scanned; never the match.

    Every regular file is scanned, hidden ones and the status file included.
    """
    findings = []
    for path in files:
        rel = path.relative_to(folder).as_posix()
        size = path.stat().st_size
        if size > MAX_SCAN_BYTES:
            findings.append(f"{rel} was not scanned for secrets: {size} bytes is over the "
                            f"{MAX_SCAN_BYTES}-byte limit; trim it or keep it out of the handover folder")
            continue
        try:
            text = path.read_bytes().decode("utf-8", "ignore")
        except OSError as e:
            findings.append(f"{rel} could not be read for the secret scan ({e.__class__.__name__})")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in SECRET_PATTERNS.items():
                if re.search(pattern, line):
                    findings.append(f"possible {kind} in {rel}:{number}")
    return findings


def check(folder: Path) -> tuple[list[str], int]:
    """Validate a handover folder and record the result; returns (problems, core line count)."""
    data = read_status(folder)
    if data is None:
        sys.exit(f"error: {folder} has no readable {STATUS_FILE}; is it a handover folder?")
    files, links = walk(folder)
    regular = set(files)
    problems = [f"{rel} is a symbolic link or junction: copy the real file in instead" for rel in links]
    texts = {}
    for name in (CORE_FILE, PROMPT_FILE):
        path = folder / name
        texts[name] = path.read_text(encoding="utf-8", errors="replace") if path in regular else ""
        if not texts[name].strip():
            problems.append(f"{name} is missing or empty")
    core, prompt = texts[CORE_FILE], texts[PROMPT_FILE]
    if core.strip():
        problems += [f"handover.md lacks the heading '{label}'"
                     for label, pattern in REQUIRED_HEADINGS if not re.search(pattern, core, re.M)]
        if "**First actions**" not in core:
            problems.append("handover.md lacks '**First actions**' in Resume here")
        problems += content_problems(core)
    if prompt.strip() and CORE_FILE not in prompt:
        problems.append("resume-prompt.txt does not point to handover.md")
    if prompt.strip():
        problems += verify_command_problems(prompt, folder)
    if core.strip() and prompt.strip():
        problems += workflow_problems(core, prompt, Path(data.get("project_root") or folder))
    appendix = folder / "appendix.md"
    if appendix in regular:
        texts["appendix.md"] = appendix.read_text(encoding="utf-8", errors="replace")
    problems += scratch_problems(folder, texts, files)
    problems += secret_findings(folder, files)
    core_lines = len(core.splitlines())
    data["status"] = "in-progress" if problems else "complete"
    data["checked"] = {"at": now_iso(), "passed": not problems, "problems": problems, "core_lines": core_lines,
                       "files": digests(folder) if not problems else None}
    write_status(folder, data)
    return problems, core_lines


# --- command line ----------------------------------------------------------------------------

def cmd_status(a: argparse.Namespace) -> int:
    base = handover_base(Path(a.cwd), a.to)
    found = find_handovers(base, check_session(a.session))
    if not found:
        print(f"No handovers for session {a.session} under {base}")
    for folder, status in found:
        print(f"{status:<20} {folder}")
    return 0


def cmd_reserve(a: argparse.Namespace) -> int:
    base = handover_base(Path(a.cwd), a.to)
    print(reserve(base, check_session(a.session), a.slug, Path(a.cwd)))
    return 0


def cmd_snapshot(a: argparse.Namespace) -> int:
    print(snapshot(Path(a.cwd), check_session(a.session) if a.session else None))
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    problems, core_lines = check(Path(a.folder).expanduser())
    note = f"handover.md: {core_lines} lines (guideline 80-200; length never fails the check)"
    if problems:
        print("FAIL: status stays in-progress")
        print("\n".join(f"- {problem}" for problem in problems))
        print(note)
        return 1
    print("PASS: status set to complete")
    print(note)
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    status, details = verify(Path(a.folder).expanduser())
    print(status if status != "complete" else "complete: every file matches its passing check")
    print("\n".join(f"- {detail}" for detail in details))
    return 0 if status == "complete" else 1


def self_test() -> int:
    """Run the regression tests in test_handover.py without pytest."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_handover  # noqa: E402  (sibling module, imported here so the script stays import-free)

    tests = [getattr(test_handover, name) for name in dir(test_handover) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"self-test OK ({len(tests)} checks)")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # paths and commit subjects may hold non-ASCII text
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="run the regression tests and exit")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("status", help="list this session's handovers, in-progress first")
    p.add_argument("--session", required=True)
    p.add_argument("--to", help="handover folder root used instead of the default")
    p.add_argument("--cwd", default=".")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("reserve", help="create a new handover folder with status in-progress")
    p.add_argument("--session", required=True)
    p.add_argument("--to", help="put the handover folder directly under this directory")
    p.add_argument("--slug", default="handover", help="a few words naming the task")
    p.add_argument("--cwd", default=".")
    p.set_defaults(fn=cmd_reserve)

    p = sub.add_parser("snapshot", help="print header facts and the Git block; read-only")
    p.add_argument("--session")
    p.add_argument("--cwd", default=".")
    p.set_defaults(fn=cmd_snapshot)

    p = sub.add_parser("check", help="validate a handover folder; a pass marks it complete")
    p.add_argument("folder")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("verify", help="exit 0 only when the folder still matches its passing check")
    p.add_argument("folder")
    p.set_defaults(fn=cmd_verify)

    a = parser.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.command:
        parser.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
