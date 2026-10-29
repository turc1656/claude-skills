#!/usr/bin/env python3
"""ATDD lock: freezes approved acceptance-test files, runs the frozen command, detects drift.

The manifest lives at <repo>/.atdd/<feature>/manifest.json and is meant to be
committed with the feature. It freezes the test cases AND their support files
(domain layer, drivers, stubs, fixtures) together with the command that runs
them, because a driver that fakes an answer, or a command that runs a weaker
file, changes a test's meaning as surely as an edited assertion.

Commands (--repo <root> goes before or after the subcommand; default: the current directory):
  approve  --feature F --story S --run CMD [--cwd DIR] --tests P... [--support P...]
           first approval, or the re-approval that closes an open amendment;
           refused while a feature is approved unless nothing at all changed
  check    --feature F        exit 0 clean, 1 drift, 2 no manifest, 3 amendment open
  record   --feature F --phase red|green [--summary TEXT]
           runs the frozen command from the frozen directory and stores the real result
  record   --feature F --phase verify --exit-code N --summary TEXT
           the repo's whole quality gate, reported by the agent
  record   --feature F --phase red|green --exit-code N --summary TEXT
           manual fallback when the script cannot run the command here; flagged "manual"
  record   --feature F --phase green --red-waived REASON
           only when the user approved recording green without a fresh red
  unlock   --feature F --reason TEXT      open an amendment; approve again to close it
  status   [--feature F]
  --self-test                             run the regression tests in test_atdd_lock.py

Guards: red needs a failing run; green needs red evidence for the current
approval (or a logged waiver) and a passing run; verify needs green; nothing is
recorded while an amendment is open or while frozen files drift; re-approval
with any change to the frozen set, the hashes, the run command or the working
directory resets the evidence and keeps the old evidence on the amendment record.

Paths: --repo is resolved to its canonical form and every other path is checked
against it. --feature is a single name, and its manifest directory must resolve to
exactly <repo>/.atdd/<feature>: no traversal, no absolute paths, no symlink or
junction redirecting it. The manifest file itself must be absent or a regular
file: a symlink (even dangling) or a hard link at .atdd/<feature>/manifest.json is
refused, and every write goes through a temporary file and an atomic rename, so it
replaces the directory entry instead of writing through it. --cwd and every frozen
file must resolve to somewhere inside the repository; nested package directories
are fine.

Standard library only. Python 3.8 or newer.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_DIR = ".atdd"
MANIFEST_FILE = "manifest.json"
OUTPUT_TAIL_LINES = 25  # enough to show the failing assertion and the summary line
FEATURE_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
WINDOWS_DEVICE_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def inside(path: Path, root: Path) -> bool:
    """True when the resolved path is root itself or lies beneath it."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def repo_root(a: argparse.Namespace) -> Path:
    """The canonical repository root; every other path is validated against it."""
    repo = Path(a.repo).resolve()
    if not repo.is_dir():
        sys.exit(f"error: --repo is not a directory: {a.repo}")
    return repo


def feature_dir(repo: Path, feature: str) -> Path:
    """<repo>/.atdd/<feature>, refused unless it is a plain name that resolves to exactly that place.

    The name check stops traversal, separators and absolute paths before anything is
    touched; the resolution check stops a symlink or junction at .atdd/ or at
    .atdd/<feature> from redirecting the manifest outside the repository.
    """
    if not FEATURE_NAME.match(feature) or feature.split(".")[0].upper() in WINDOWS_DEVICE_NAMES:
        sys.exit(f"error: --feature must be a single name (letters, digits, '.', '_', '-'), not a path: {feature!r}")
    atdd = (repo / MANIFEST_DIR).resolve()
    target = (atdd / feature).resolve()
    if atdd.parent != repo or target.parent != atdd:
        sys.exit(f"error: {MANIFEST_DIR}/{feature} resolves outside the repository's {MANIFEST_DIR}/ directory (symlink or junction?)")
    return target


def safe_cwd(repo: Path, raw: str) -> str:
    """A working directory inside the repository, returned as a normalised relative POSIX path."""
    p = Path(raw)
    if p.anchor:
        sys.exit(f"error: --cwd must be relative to the repository root, not absolute: {raw!r}")
    target = (repo / p).resolve()
    if not inside(target, repo):
        sys.exit(f"error: --cwd escapes the repository root: {raw!r}")
    if not target.is_dir():
        sys.exit(f"error: --cwd is not a directory inside the repository: {raw!r}")
    return "." if target == repo else target.relative_to(repo).as_posix()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_hash(path: Path) -> str:
    # ponytail: CRLF is normalised to LF before hashing, so a Windows checkout
    # with autocrlf and a Linux cloud session agree on the hash of the same file.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def manifest_path(repo: Path, feature: str) -> Path:
    """<repo>/.atdd/<feature>/manifest.json, refused unless absent or a plain regular file.

    A symlink (dangling or not), a hard link, or any other link at the manifest path
    could make a read or a write land in a file outside the repository, so all of them
    are refused before the file is opened. lstat is used so nothing is followed.
    """
    path = feature_dir(repo, feature) / MANIFEST_FILE
    shown = f"{MANIFEST_DIR}/{feature}/{MANIFEST_FILE}"
    if path.is_symlink():
        sys.exit(f"error: {shown} is a symlink; a manifest must be a regular file inside the repository")
    if not os.path.lexists(path):
        return path
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        sys.exit(f"error: {shown} is not a regular file")
    if info.st_nlink > 1:
        sys.exit(f"error: {shown} is a hard link ({info.st_nlink} names for one file); a manifest must be a regular file inside the repository")
    if path.resolve() != path:
        sys.exit(f"error: {shown} resolves somewhere else (a link?); a manifest must be a regular file inside the repository")
    return path


def load(repo: Path, feature: str) -> dict | None:
    path = manifest_path(repo, feature)
    if not os.path.lexists(path):
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save(repo: Path, feature: str, manifest: dict) -> Path:
    """Write the manifest through a temporary file and an atomic rename.

    os.replace swaps the directory entry, so even a link that appeared after the
    check is replaced rather than written through. LF line endings, for git.
    """
    path = manifest_path(repo, feature)
    path.parent.mkdir(parents=True, exist_ok=True)
    if feature_dir(repo, feature) != path.parent:
        sys.exit(f"error: {MANIFEST_DIR}/{feature} changed while it was being created")
    fd, tmp = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, indent=2) + "\n")
        if os.name != "nt":
            os.chmod(tmp, 0o644)  # mkstemp creates 0600; a committed manifest is an ordinary file
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
    return path


def rel(repo: Path, raw: str) -> str:
    """Path relative to the repo root, forward slashes, whatever form was passed."""
    p = Path(raw)
    if not p.is_absolute():
        p = repo / p
    try:
        return p.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        sys.exit(f"error: {raw} is outside the repository root {repo}")


def entries(repo: Path, paths: list[str], kind: str) -> list[dict]:
    out = []
    for raw in paths:
        r = rel(repo, raw)
        full = repo / r
        if not full.is_file():
            sys.exit(f"error: {kind} file not found: {r}")
        out.append({"path": r, "kind": kind, "sha256": file_hash(full)})
    return out


def drift(repo: Path, manifest: dict) -> list[str]:
    problems = []
    for f in manifest["files"]:
        full = repo / rel(repo, f["path"])  # a hand-edited manifest cannot point outside the repository
        if not full.is_file():
            problems.append(f"missing  {f['path']}")
        elif file_hash(full) != f["sha256"]:
            problems.append(f"changed  {f['path']}")
    return problems


def describe_changes(existing: dict, files: list[dict], run: dict, story: str) -> list[str]:
    """Every difference between the existing approval and the requested one."""
    old = {f["path"]: f for f in existing.get("files", [])}
    new = {f["path"]: f for f in files}
    changes = []
    for path in sorted(set(old) | set(new)):
        if path not in old:
            changes.append(f"added {new[path]['kind']} {path}")
        elif path not in new:
            changes.append(f"removed {old[path]['kind']} {path}")
        elif old[path]["sha256"] != new[path]["sha256"]:
            changes.append(f"changed {old[path]['kind']} {path}")
    old_run = existing.get("run", {})
    if old_run.get("command") != run["command"]:
        changes.append("run command changed")
    if old_run.get("cwd") != run["cwd"]:
        changes.append("working directory changed")
    if existing.get("story") != story:
        changes.append("story changed")
    return changes


def cmd_approve(a: argparse.Namespace) -> int:
    repo = repo_root(a)
    files = entries(repo, a.tests, "test") + entries(repo, a.support or [], "support")
    run = {"command": a.run, "cwd": safe_cwd(repo, a.cwd or ".")}
    existing = load(repo, a.feature)
    evidence: dict = {}
    amendments: list = []

    if existing is not None:
        changes = describe_changes(existing, files, run, a.story)
        amendments = existing.get("amendments", [])
        evidence = existing.get("evidence", {})
        if existing.get("status") == "approved":
            if not changes:
                print("already approved; nothing changed")
                return 0
            print("refused: this feature is approved. The frozen set, the run command and the story")
            print("change only through an amendment: unlock with the user's approval, then approve again.")
            for c in changes:
                print("  " + c)
            return 1
        # An amendment is open: close it, and reset evidence if anything changed.
        amendment = amendments[-1]
        amendment["reapproved_at"] = now()
        amendment["changes"] = changes
        if changes:
            amendment["superseded_evidence"] = evidence
            evidence = {}

    manifest = {
        "feature": a.feature,
        "story": a.story,
        "status": "approved",
        "approved_at": now(),
        "run": run,
        "files": files,
        "evidence": evidence,
        "amendments": amendments,
    }
    path = save(repo, a.feature, manifest)
    print(f"approved {len(files)} file(s); manifest: {path.relative_to(repo).as_posix()}")
    for f in files:
        print(f"  {f['kind']:7} {f['path']}  {f['sha256'][:12]}")
    if existing is not None and amendments[-1].get("changes"):
        print("amendment closed with changes; red, green and verify evidence reset:")
        for c in amendments[-1]["changes"]:
            print("  " + c)
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    repo = repo_root(a)
    manifest = load(repo, a.feature)
    if manifest is None:
        print(f"no manifest for feature {a.feature!r} under {MANIFEST_DIR}/")
        return 2
    if manifest["status"] == "amending":
        print(f"amendment open since {manifest['amendments'][-1]['at']}: approve again before running")
        return 3
    problems = drift(repo, manifest)
    if problems:
        print("DRIFT: frozen files differ from the approved versions")
        for p in problems:
            print("  " + p)
        print("Stop. Changes to frozen files need the user's approval through amend.")
        return 1
    print(f"clean: {len(manifest['files'])} frozen file(s) match the approval of {manifest['approved_at']}")
    return 0


def run_frozen_command(repo: Path, manifest: dict) -> tuple[int, list[str], str]:
    """Run the approved command from the approved directory.

    Returns the exit code, the non-empty output lines (stdout then stderr) and a
    one-line summary: the last stdout line, where test runners print their totals,
    falling back to stderr (a tool's environment setup often lands there).
    """
    run = manifest["run"]
    proc = subprocess.run(
        run["command"], shell=True, cwd=str(repo / safe_cwd(repo, run["cwd"])),
        capture_output=True, text=True, errors="replace",
    )
    out = [line for line in proc.stdout.splitlines() if line.strip()]
    err = [line for line in proc.stderr.splitlines() if line.strip()]
    summary = (out or err or ["no output"])[-1]
    return proc.returncode, out + err, summary


def cmd_record(a: argparse.Namespace) -> int:
    repo = repo_root(a)
    manifest = load(repo, a.feature)
    if manifest is None:
        sys.exit(f"error: no manifest for feature {a.feature!r}")
    manual = a.exit_code is not None
    if manual and a.summary is None:
        sys.exit("error: a manual record needs --summary")
    if a.phase == "verify" and not manual:
        sys.exit("error: verify is the repo's whole quality gate: pass --exit-code and --summary")
    if a.red_waived is not None and a.phase != "green":
        sys.exit("error: --red-waived applies to --phase green only")

    if manifest["status"] != "approved":
        print("refused: an amendment is open; approve again before recording evidence")
        return 1
    problems = drift(repo, manifest)
    if problems:
        print("refused: frozen files drifted, so a run now would not describe the approved specifications")
        for p in problems:
            print("  " + p)
        return 1

    evidence = manifest.setdefault("evidence", {})
    if a.phase == "red" and "green" in evidence:
        print("refused: green is already recorded for this approval; a failing run now is a regression,")
        print("not red. If the specifications changed, open an amendment.")
        return 1
    if a.phase == "green" and "red" not in evidence and a.red_waived is None:
        print("refused: no red evidence for this approval; record red first, or, with the user's")
        print("explicit approval, pass --red-waived with their reason")
        return 1
    if a.phase == "verify" and "green" not in evidence:
        print("refused: no green evidence for this approval; record green first")
        return 1

    if manual:
        exit_code, summary = a.exit_code, a.summary
    else:
        exit_code, lines, last_line = run_frozen_command(repo, manifest)
        for line in lines[-OUTPUT_TAIL_LINES:]:
            print("  | " + line)
        summary = a.summary or last_line

    if a.phase == "red" and exit_code == 0:
        print("refused: red requires a failing run; a passing test specifies nothing new")
        return 1
    if a.phase in ("green", "verify") and exit_code != 0:
        print(f"refused: {a.phase} requires a passing run; this run exited {exit_code}")
        return 1

    entry = {"at": now(), "exit_code": exit_code, "summary": summary, "manual": manual}
    if a.red_waived is not None:
        entry["red_waived"] = a.red_waived
    evidence[a.phase] = entry
    save(repo, a.feature, manifest)
    flags = (" (manual)" if manual else "") + (f" (red waived: {a.red_waived})" if a.red_waived else "")
    print(f"recorded {a.phase}: exit {exit_code}, {summary}{flags}")
    return 0


def cmd_unlock(a: argparse.Namespace) -> int:
    repo = repo_root(a)
    manifest = load(repo, a.feature)
    if manifest is None:
        sys.exit(f"error: no manifest for feature {a.feature!r}")
    if manifest["status"] == "amending":
        print("refused: an amendment is already open; approve again to close it first")
        return 1
    if drift(repo, manifest):
        print("warning: frozen files already differ, so the edit came before this amendment.")
        print("Show the user the diff and get an explicit approval before running approve.")
    manifest["status"] = "amending"
    manifest.setdefault("amendments", []).append({"at": now(), "reason": a.reason})
    save(repo, a.feature, manifest)
    print("amendment opened; edit the frozen file(s), then run approve again to re-lock")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    repo = repo_root(a)
    root = repo / MANIFEST_DIR
    if a.feature:
        feature_dir(repo, a.feature)  # an explicit name is validated like everywhere else, not skipped
        features = [a.feature]
    elif root.exists():
        features = sorted(p.name for p in root.iterdir() if p.is_dir())
    else:
        features = []
    if not features:
        print(f"no features under {MANIFEST_DIR}/")
        return 0
    for feature in features:
        try:
            m = load(repo, feature)
        except SystemExit as refusal:  # an entry under .atdd/ that is not a valid feature or manifest
            if a.feature:
                raise  # a feature the caller named fails like every other command
            print(f"{feature}: skipped ({refusal.code})")
            continue
        if m is None:
            print(f"{feature}: no manifest")
            continue
        problems = drift(repo, m)
        state = "DRIFT" if problems else "clean"
        print(f"{feature}: {m['status']}, story {m['story']}, approved {m['approved_at']}, {state}")
        print(f"  run: {m['run']['command']}  (cwd {m['run']['cwd']})")
        for f in m["files"]:
            print(f"  {f['kind']:7} {f['path']}")
        for phase, ev in m.get("evidence", {}).items():
            flags = (" (manual)" if ev.get("manual") else "") + (
                f" (red waived: {ev['red_waived']})" if ev.get("red_waived") else "")
            print(f"  {phase}: exit {ev['exit_code']} at {ev['at']}: {ev['summary']}{flags}")
        for am in m.get("amendments", []):
            closed = f", closed {am['reapproved_at']}" if "reapproved_at" in am else ", OPEN"
            changes = "; ".join(am.get("changes", [])) or "no changes"
            print(f"  amendment {am['at']}: {am['reason']}{closed}: {changes}")
        for p in problems:
            print("  " + p)
    return 0


def self_test() -> int:
    """Run the regression tests in test_atdd_lock.py without pytest."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_atdd_lock  # noqa: E402  (sibling module, imported here so the script stays import-free)

    tests = [getattr(test_atdd_lock, name) for name in dir(test_atdd_lock) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"self-test OK ({len(tests)} checks)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument("--self-test", action="store_true", help="run the regression tests and exit")
    sub = parser.add_subparsers(dest="command")

    def accepts_repo(subparser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        # SUPPRESS keeps the top-level --repo value when the option is not repeated after the subcommand.
        subparser.add_argument("--repo", default=argparse.SUPPRESS, help="repository root (same as the top-level option)")
        return subparser

    p = accepts_repo(sub.add_parser("approve", help="freeze the listed files and the run command"))
    p.add_argument("--feature", required=True)
    p.add_argument("--story", required=True, help="issue reference or short description")
    p.add_argument("--run", required=True, help="command that runs exactly the acceptance tests")
    p.add_argument("--cwd", help="directory to run it from, relative to --repo (default: .)")
    p.add_argument("--tests", nargs="+", required=True, help="test case files")
    p.add_argument("--support", nargs="*", help="domain layer, drivers, stubs, fixtures")
    p.set_defaults(fn=cmd_approve)

    p = accepts_repo(sub.add_parser("check", help="verify frozen files are unchanged"))
    p.add_argument("--feature", required=True)
    p.set_defaults(fn=cmd_check)

    p = accepts_repo(sub.add_parser("record", help="run the frozen command (red, green) or store verify evidence"))
    p.add_argument("--feature", required=True)
    p.add_argument("--phase", choices=["red", "green", "verify"], required=True)
    p.add_argument("--exit-code", type=int, help="manual result; required for verify, a flagged fallback otherwise")
    p.add_argument("--summary", help="one line; for red, name the missing behaviour")
    p.add_argument("--red-waived", metavar="REASON", help="green without a fresh red, only with the user's approval")
    p.set_defaults(fn=cmd_record)

    p = accepts_repo(sub.add_parser("unlock", help="open an amendment with the user's approval"))
    p.add_argument("--feature", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(fn=cmd_unlock)

    p = accepts_repo(sub.add_parser("status", help="show features, evidence, amendments and drift"))
    p.add_argument("--feature")
    p.set_defaults(fn=cmd_status)

    a = parser.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.command:
        parser.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
