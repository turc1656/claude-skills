"""Regression tests for handover.py.

Run with pytest (`pytest test_handover.py`) or without it (`python handover.py --self-test`).
Plain asserts and the standard library only. Every test works in a throwaway folder; the
Git repositories it creates and commits to are temporary fixtures, never the user's.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handover  # noqa: E402

GIT = ["git", "-c", "user.name=handover-test", "-c", "user.email=test@example.invalid",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", "-c", "init.defaultBranch=main"]
SESSION = "11111111-2222-3333-4444-555555555555"
OTHER_SESSION = "99999999-8888-7777-6666-555555555555"
WHEN = datetime(2026, 10, 24, 12, 0, 0).astimezone()

CORE = """# Handover: test task (2026-10-24 12:00)

Project `demo`

## 1. Resume here
The work is half done.
**First actions**
1. Finish the thing.

## 2. Waiting on you
none

## 3. Decisions and constraints
- Keep it small: the user asked for that.

## 4. Work state
Done: part one.

## 5. Verification
- `pytest -q` | pass | 2026-10-24 11:50 | [verified] | cheap

## 6. Workspace
No Git repository.
- Uncommitted work at risk: none
- Running processes: none

## 7. References
none
"""
HELPER = Path(handover.__file__).resolve()
TEMPLATE = HELPER.parent.parent / "references" / "template.md"
VERIFY = 'Before anything else, run `python "' + str(HELPER) + '" verify "{folder}"`.'
PROMPT = VERIFY + "\nRead `{folder}/handover.md` in full. It is the handover for the test task.\n"

WORKFLOW_BLOCK = """**Active workflow** (only when a skill drove the work):
- Skill: `atdd` | Phase: green | State file: `.atdd/reservations/manifest.json`
- Next action in the workflow: make scenario 3 pass
- Resume command: `{command}`
- Resume the existing state; never start a new workflow.
"""
WORKFLOW_PROMPT = (
    "{first}\n"
    + VERIFY + "\n"
    "Read `{folder}/handover.md` in full. It is the handover for the reservations feature.\n"
    "Resume the existing atdd workflow from `.atdd/reservations/manifest.json`; do not start a new one.\n"
    "If you cannot invoke `atdd`, stop and ask me to run `/atdd green reservations`.\n"
)


@contextlib.contextmanager
def scratch():
    """A temporary folder, removed afterwards even when Git left read-only object files in it."""
    path = Path(tempfile.mkdtemp(prefix="handover-test-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def git(repo: Path, *args: str) -> None:
    subprocess.run([*GIT, "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(path: Path, commit: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    if commit:
        (path / "a.txt").write_text("one\n", encoding="utf-8")
        git(path, "add", "a.txt")
        git(path, "commit", "-q", "-m", "first commit")
    return path


def run(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = handover.main(list(argv))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
            buf.write(f"{e.code}\n")
    return code, buf.getvalue()


def status_of(folder: Path) -> str:
    return json.loads((folder / handover.STATUS_FILE).read_text(encoding="utf-8"))["status"]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def new_handover(tmp: Path, session: str = SESSION) -> Path:
    project = tmp / "project"
    project.mkdir(exist_ok=True)
    return handover.reserve(tmp / "handovers", session, "test task", project)


# --- snapshot: Git states --------------------------------------------------------------------

def test_snapshot_without_a_repository() -> None:
    with scratch() as tmp:
        text = handover.snapshot(tmp, SESSION)
        assert "No Git repository." in text, text
        assert f"`{SESSION}`" in text


def test_snapshot_clean_repository() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "repo")
        text = handover.snapshot(repo, None)
        assert "- Branch: `main` | no upstream" in text, text
        assert "first commit" in text
        assert "0 staged | 0 unstaged | 0 untracked | 0 conflicted" in text
        assert "Operation in progress: none" in text


def test_snapshot_dirty_repository_with_spaces_is_read_only() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "my repo")
        write(repo / "a.txt", "two\n")
        write(repo / "b file.txt", "new\n")
        git(repo, "add", "b file.txt")
        write(repo / "sub dir" / "c d.txt", "untracked\n")
        before = subprocess.run([*GIT, "-C", str(repo), "status", "--porcelain"], capture_output=True).stdout
        index = (repo / ".git" / "index").read_bytes()  # read after our own status may have refreshed it
        text = handover.snapshot(repo, None)
        assert "1 staged | 1 unstaged | 1 untracked" in text, text
        assert "b file.txt" in text and "sub dir/" in text
        assert (repo / ".git" / "index").read_bytes() == index, "snapshot rewrote the index"
        after = subprocess.run([*GIT, "-C", str(repo), "status", "--porcelain"], capture_output=True).stdout
        assert before == after


def test_snapshot_detached_head() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "repo")
        write(repo / "a.txt", "two\n")
        git(repo, "commit", "-q", "-am", "second commit")
        git(repo, "checkout", "-q", "--detach", "HEAD~1")
        assert "detached HEAD at" in handover.snapshot(repo, None)


def test_snapshot_unborn_branch() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "repo", commit=False)
        text = handover.snapshot(repo, None)
        assert "(no commits yet)" in text, text
        assert "Recent commits" not in text


def test_snapshot_reports_an_operation_in_progress() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "repo")
        head = subprocess.run([*GIT, "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
        write(repo / ".git" / "MERGE_HEAD", head)
        assert "Operation in progress: merge" in handover.snapshot(repo, None)


def test_snapshot_groups_many_paths() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "repo")
        for n in range(handover.MAX_LISTED_PATHS + 5):
            write(repo / ("src" if n % 2 else "docs") / f"f{n}.txt", "x\n")
        git(repo, "add", ".")
        text = handover.snapshot(repo, None)
        assert "grouped by top folder" in text, text
        assert "  - src/: 17" in text and "  - docs/: 18" in text


# --- reserve and status ----------------------------------------------------------------------

def test_reserve_never_reuses_a_folder() -> None:
    with scratch() as tmp:
        base = tmp / "handovers"
        taken = base / "2026-10-24_120000_test-task"
        write(taken / "keep.txt", "someone else's\n")
        first = handover.reserve(base, SESSION, "test task", tmp, WHEN)
        second = handover.reserve(base, SESSION, "test task", tmp, WHEN)
        assert first.name == "2026-10-24_120000_test-task-2", first
        assert second.name == "2026-10-24_120000_test-task-3", second
        assert (taken / "keep.txt").read_text(encoding="utf-8") == "someone else's\n"
        assert not (taken / handover.STATUS_FILE).exists()


def test_reserve_uses_the_project_folder_under_the_default_root() -> None:
    with scratch() as tmp:
        repo = make_repo(tmp / "my repo")
        saved = handover.DEFAULT_ROOT
        handover.DEFAULT_ROOT = tmp / "root"
        try:
            code, out = run("reserve", "--session", SESSION, "--slug", "fix bug", "--cwd", str(repo / "."))
        finally:
            handover.DEFAULT_ROOT = saved
        folder = Path(out.strip())
        assert code == 0, out
        assert folder.parent == tmp / "root" / "my-repo", folder
        assert status_of(folder) == "in-progress"


def test_reserve_with_to_writes_directly_under_that_folder() -> None:
    with scratch() as tmp:
        code, out = run("reserve", "--session", SESSION, "--to", str(tmp / "plans"), "--cwd", str(tmp))
        assert code == 0, out
        assert Path(out.strip()).parent == tmp / "plans"


def test_status_lists_only_this_sessions_handovers_in_progress_first() -> None:
    with scratch() as tmp:
        base = tmp / "handovers"
        done = new_handover(tmp)
        write(done / handover.CORE_FILE, CORE)
        write(done / handover.PROMPT_FILE, PROMPT.format(folder=done))
        assert handover.check(done)[0] == []
        open_one = new_handover(tmp)
        other = new_handover(tmp, OTHER_SESSION)
        found = [folder for folder, _ in handover.find_handovers(base, SESSION)]
        assert found == [open_one, done], found
        assert other not in found
        code, out = run("status", "--session", SESSION, "--to", str(base))
        assert code == 0 and out.splitlines()[0].startswith("in-progress"), out


def test_bad_session_ids_are_refused() -> None:
    with scratch() as tmp:
        code, out = run("status", "--session", "../x", "--to", str(tmp))
        assert code != 0 and "not a session id" in out, out


# --- check and the completion marker ---------------------------------------------------------

def test_only_a_passing_check_marks_complete() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        assert status_of(folder) == "in-progress"
        write(folder / handover.CORE_FILE, CORE)
        problems, _ = handover.check(folder)
        assert problems == ["resume-prompt.txt is missing or empty"], problems
        assert status_of(folder) == "in-progress"
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == []
        assert status_of(folder) == "complete"


def test_a_failing_recheck_reverts_complete() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == [] and status_of(folder) == "complete"
        write(folder / handover.CORE_FILE, CORE.replace("## 5. Verification", "## 5. Checks"))
        problems, _ = handover.check(folder)
        assert problems == ["handover.md lacks the heading '## 5. Verification'"], problems
        assert status_of(folder) == "in-progress"


def test_finishing_an_interrupted_handover_keeps_the_core_unchanged() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)  # the run stopped here
        digest = hashlib.sha256((folder / handover.CORE_FILE).read_bytes()).hexdigest()
        assert [f for f, _ in handover.find_handovers(tmp / "handovers", SESSION)] == [folder]
        assert handover.find_handovers(tmp / "handovers", OTHER_SESSION) == []
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))  # the resumed run
        code, out = run("check", str(folder))
        assert code == 0 and out.startswith("PASS"), out
        assert hashlib.sha256((folder / handover.CORE_FILE).read_bytes()).hexdigest() == digest


def test_length_is_reported_but_never_fails() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE + "\n".join(f"- detail {n}" for n in range(400)) + "\n")
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        code, out = run("check", str(folder))
        assert code == 0, out
        assert "lines (guideline 80-200; length never fails the check)" in out


def test_headings_without_content_fail() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        skeleton = "\n".join(label for label, _ in handover.REQUIRED_HEADINGS) + "\n"
        skeleton = skeleton.replace("# Handover: <task>", "# Handover: demo")
        skeleton = skeleton.replace("## 1. Resume here\n", "## 1. Resume here\n**First actions**\n")
        write(folder / handover.CORE_FILE, skeleton)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        for section in ("2. Waiting on you", "3. Decisions and constraints", "4. Work state",
                        "5. Verification", "6. Workspace", "7. References"):
            assert f"section '{section}' is empty" in "\n".join(problems), (section, problems)
        assert "handover.md: '**First actions**' has no numbered action" in problems
        assert any("Uncommitted work at risk:" in p for p in problems)
        assert any("Running processes:" in p for p in problems)
        assert status_of(folder) == "in-progress"


def test_unfilled_placeholders_count_as_empty() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        core = CORE.replace("Done: part one.", "- Done: <item>").replace(
            "1. Finish the thing.", "1. <exact action, with the command or path>")
        core = core.replace("- Running processes: none", "- Running processes: <what, or none>")
        write(folder / handover.CORE_FILE, core)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        assert "handover.md: section '4. Work state' is empty (write its content, or 'none')" in problems, problems
        assert "handover.md: '**First actions**' has no numbered action" in problems
        assert any("Running processes:" in p for p in problems)


def test_the_unfilled_template_fails() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    core = template.split("```markdown\n", 1)[1].split("\n```", 1)[0]
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, core)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        for section in ("2. Waiting on you", "3. Decisions and constraints", "4. Work state", "7. References"):
            assert f"section '{section}' is empty" in "\n".join(problems), (section, problems)
        assert "handover.md: '**First actions**' has no numbered action" in problems
        assert status_of(folder) == "in-progress"


def test_files_too_large_to_scan_fail_the_check() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        write(folder / "files" / "big.log", "x" * 300 + "\n" + "gh" + "p_" + "A" * 36 + "\n")
        saved = handover.MAX_SCAN_BYTES
        handover.MAX_SCAN_BYTES = 200
        try:
            code, out = run("check", str(folder))
        finally:
            handover.MAX_SCAN_BYTES = saved
        assert code == 1 and "files/big.log was not scanned for secrets" in out, out
        assert status_of(folder) == "in-progress"


def test_named_scratch_files_must_exist() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        core = CORE.replace("## 7. References\nnone", "## 7. References\n- Copied scratch files: "
                            "`files/missing-critical-builder.py`, files/notes.txt.\n"
                            "- Not scratch: src/files/a.py, the files/ folder")
        write(folder / handover.CORE_FILE, core)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        assert problems == [
            "handover.md names files/missing-critical-builder.py, which is not a file in the handover folder",
            "handover.md names files/notes.txt, which is not a file in the handover folder",
        ], problems
        write(folder / "files" / "missing-critical-builder.py", "print('built')\n")
        write(folder / "files" / "notes.txt", "notes\n")
        assert handover.check(folder)[0] == []
        assert status_of(folder) == "complete"


def test_scratch_references_cannot_leave_the_files_folder() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE.replace("none\n", "See `files/../../escape.txt`.\n", 1))
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        assert "handover.md names files/../../escape.txt, which points outside files/" in problems, problems


def test_status_flags_changes_made_after_a_passing_check() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == []
        assert handover.find_handovers(tmp / "handovers", SESSION) == [(folder, "complete")]
        write(folder / handover.CORE_FILE, CORE + "- one more line\n")
        assert handover.find_handovers(tmp / "handovers", SESSION) == [(folder, "changed-since-check")]
        code, out = run("status", "--session", SESSION, "--to", str(tmp / "handovers"))
        assert out.startswith("changed-since-check"), out
        assert handover.check(folder)[0] == []
        assert handover.find_handovers(tmp / "handovers", SESSION) == [(folder, "complete")]


def test_verify_catches_edits_the_status_file_cannot_show() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == []
        code, out = run("verify", str(folder))
        assert code == 0 and out.startswith("complete"), out
        write(folder / handover.CORE_FILE, CORE + "- edited after the check\n")
        write(folder / "files" / "late.txt", "added after the check\n")
        assert status_of(folder) == "complete", "the JSON alone still says complete"
        code, out = run("verify", str(folder))
        assert code == 1 and out.startswith("changed-since-check"), out
        assert "- handover.md changed" in out and "- files/late.txt added" in out, out
        (folder / handover.PROMPT_FILE).unlink()
        assert "- resume-prompt.txt removed" in run("verify", str(folder))[1]


def test_verify_reports_an_unchecked_handover() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        code, out = run("verify", str(folder))
        assert code == 1 and out.startswith("in-progress") and "check has not passed yet" in out, out


def test_resume_prompt_must_carry_the_verify_command() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder).replace(" verify ", " check "))
        problems, _ = handover.check(folder)
        assert any("lacks the verify command" in p for p in problems), problems


def test_a_directory_is_not_a_copied_file() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        (folder / "files" / "needed.py").mkdir(parents=True)
        write(folder / handover.CORE_FILE, CORE.replace("## 7. References\nnone",
                                                        "## 7. References\n- Copied scratch files: `files/needed.py`"))
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        assert problems == ["handover.md names files/needed.py, which is not a file in the handover folder"], problems
        assert status_of(folder) == "in-progress"


def outside_secret(tmp: Path) -> Path:
    """A file outside the handover holding a token-shaped string, so any read of it would show up."""
    path = tmp / "outside" / "secret.txt"
    write(path, "gh" + "p_" + "B" * 36 + "\n")
    return path


def test_symlinked_files_are_rejected_without_being_read() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE.replace("## 7. References\nnone",
                                                        "## 7. References\n- Copied scratch files: `files/linked.txt`"))
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        (folder / "files").mkdir()
        os.symlink(outside_secret(tmp), folder / "files" / "linked.txt")
        code, out = run("check", str(folder))
        assert code == 1 and "files/linked.txt is a symbolic link or junction" in out, out
        assert "names files/linked.txt, which is not a file" in out
        assert "possible GitHub token" not in out, "the link target was read"
        assert status_of(folder) == "in-progress"


def test_a_symlinked_core_document_is_not_read() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(tmp / "outside" / "core.md", CORE)
        os.symlink(tmp / "outside" / "core.md", folder / handover.CORE_FILE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        problems, _ = handover.check(folder)
        assert "handover.md is a symbolic link or junction: copy the real file in instead" in problems, problems
        assert "handover.md is missing or empty" in problems


def test_linked_directories_are_rejected_without_being_walked() -> None:
    with scratch() as tmp:
        outside_secret(tmp)
        kinds = [("dirlink", lambda link: os.symlink(tmp / "outside", link, target_is_directory=True))]
        if os.name == "nt":
            kinds.append(("junction", lambda link: subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(tmp / "outside")], check=True, capture_output=True)))
        for name, make in kinds:
            folder = new_handover(tmp)
            write(folder / handover.CORE_FILE, CORE)
            write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
            (folder / "files").mkdir()
            make(folder / "files" / name)
            problems, _ = handover.check(folder)
            assert f"files/{name} is a symbolic link or junction: copy the real file in instead" in problems, problems
            assert not any("possible" in p for p in problems), (name, problems)
            assert "link" == handover.digests(folder)[f"files/{name}"], "a link must be recorded, not followed"


def test_a_link_added_after_the_check_breaks_verify() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == []
        os.symlink(outside_secret(tmp), folder / "sneaky.txt")
        code, out = run("verify", str(folder))
        assert code == 1 and "- sneaky.txt added" in out, out


def test_hidden_files_are_scanned_and_fingerprinted() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        write(folder / ".handover.private.txt", "gh" + "p_" + "C" * 36 + "\n")
        write(folder / "files" / ".env", "pass" + "word=" + "hunter2hunter2\n")
        problems, _ = handover.check(folder)
        assert "possible GitHub token in .handover.private.txt:1" in problems, problems
        assert "possible credential assignment in files/.env:1" in problems, problems
        (folder / ".handover.private.txt").unlink()
        (folder / "files" / ".env").unlink()
        assert handover.check(folder)[0] == []
        write(folder / ".handover.notes", "added after the check\n")
        code, out = run("verify", str(folder))
        assert code == 1 and "- .handover.notes added" in out, out


def test_verify_command_must_target_this_folder() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        other = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        good = PROMPT.format(folder=folder)
        for target in (str(other), str(tmp / "missing-folder")):
            write(folder / handover.PROMPT_FILE, good.replace(f'verify "{folder}"', f'verify "{target}"'))
            problems, _ = handover.check(folder)
            assert f"the verify command targets {target}, not this handover folder" in problems, problems
            assert status_of(folder) == "in-progress"
        write(folder / handover.PROMPT_FILE, good.replace(f'verify "{folder}"', "verify "))
        assert "the verify command in resume-prompt.txt names no folder" in handover.check(folder)[0]
        same = str(folder).replace("\\", "/") + "/"  # the same folder, spelled differently
        write(folder / handover.PROMPT_FILE, good.replace(f'verify "{folder}"', f'verify "{same}"'))
        assert handover.check(folder)[0] == []


def test_verify_command_helper_must_exist() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        write(folder / handover.CORE_FILE, CORE)
        missing = str(tmp / "nowhere" / "handover.py")
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder).replace(str(HELPER), missing))
        problems, _ = handover.check(folder)
        assert f"the verify command's helper does not exist: {missing}" in problems, problems


def fill_template(text: str, **values: str) -> str:
    """Fill the named placeholders, then every other <...> with 'x', innermost first."""
    for key, value in values.items():
        text = text.replace(f"<{key}>", value)
    while re.search(r"<[^<>]*>", text):
        text = re.sub(r"<[^<>]*>", "x", text)
    return text


def test_the_filled_template_passes_check_and_verify() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    core = template.split("```markdown\n", 1)[1].split("\n```", 1)[0]
    plain_prompt, workflow_prompt = re.findall(r"```text\n(.*?)\n```", template, re.S)
    for with_workflow in (False, True):
        with scratch() as tmp:
            folder = new_handover(tmp)
            text, prompt = core, plain_prompt
            if with_workflow:
                write(tmp / "project" / ".atdd" / "res" / "manifest.json", "{}\n")
                text = re.sub(r"State file: `[^\n]*", "State file: `.atdd/res/manifest.json`", text)
                text = re.sub(r"- Resume command: [^\n]*", "- Resume command: `/atdd green res`", text)
                prompt = "/atdd green res\n" + workflow_prompt.split("\n", 1)[1]
            else:
                text = text[:text.index("**Active workflow**")] + text[text.index("**First actions**"):]
            values = {"helper dir": str(HELPER.parent), "folder": str(folder), "resume command": "/atdd green res"}
            write(folder / handover.CORE_FILE, fill_template(text, **values))
            write(folder / handover.PROMPT_FILE, fill_template(prompt, **values))
            assert handover.check(folder)[0] == [], (with_workflow, handover.check(folder)[0])
            code, out = run("verify", str(folder))
            assert code == 0 and out.startswith("complete"), out


def test_check_requires_a_status_file() -> None:
    with scratch() as tmp:
        code, out = run("check", str(tmp))
        assert code != 0 and "has no readable" in out, out


# --- active workflow -------------------------------------------------------------------------

def workflow_case(tmp: Path, command: str = "/atdd green reservations", first: str | None = None,
                  prompt_edit=lambda text: text, with_state: bool = True) -> list[str]:
    folder = new_handover(tmp)
    if with_state:
        write(tmp / "project" / ".atdd" / "reservations" / "manifest.json", "{}\n")
    core = CORE.replace("**First actions**", WORKFLOW_BLOCK.format(command=command) + "**First actions**")
    write(folder / handover.CORE_FILE, core)
    prompt = WORKFLOW_PROMPT.format(first=command if first is None else first, folder=folder)
    write(folder / handover.PROMPT_FILE, prompt_edit(prompt))
    return handover.check(folder)[0]


def test_workflow_handover_passes_when_it_resumes_the_existing_state() -> None:
    with scratch() as tmp:
        assert workflow_case(tmp) == []


def test_workflow_bare_skill_prefix_fails() -> None:
    with scratch() as tmp:
        problems = workflow_case(tmp, command="/atdd")
        assert any("bare skill name" in p for p in problems), problems


def test_workflow_prompt_must_start_with_the_resume_command() -> None:
    with scratch() as tmp:
        problems = workflow_case(tmp, first="/atdd Read the handover and continue")
        assert any("must be exactly the resume command" in p for p in problems), problems


def test_workflow_prompt_must_say_resume_not_restart() -> None:
    with scratch() as tmp:
        problems = workflow_case(tmp, prompt_edit=lambda t: t.replace("; do not start a new one", ""))
        assert any("do not start a new one" in p for p in problems), problems


def test_workflow_prompt_must_keep_the_stop_and_ask_line() -> None:
    with scratch() as tmp:
        problems = workflow_case(tmp, prompt_edit=lambda t: t.replace("stop and ask me to run", "run"))
        assert any("stop-and-ask" in p for p in problems), problems


def test_workflow_state_file_must_exist() -> None:
    with scratch() as tmp:
        problems = workflow_case(tmp, with_state=False)
        assert any("state file does not exist" in p for p in problems), problems


def test_workflow_without_a_resume_form_must_not_use_a_slash_prefix() -> None:
    with scratch() as tmp:
        assert workflow_case(tmp, command="none (the skill has no resume form)", first="Plain start") == []
    with scratch() as tmp:
        problems = workflow_case(tmp, command="none (the skill has no resume form)", first="/atdd")
        assert any("starts with a slash command" in p for p in problems), problems


# --- secret scan -----------------------------------------------------------------------------

def test_secret_scan_flags_each_pattern_without_echoing_it() -> None:
    # Built at runtime so this file itself never holds anything token-shaped.
    samples = {
        "private key": "-----BEGIN RSA " + "PRIVATE KEY-----",
        "sk- API key": "sk-" + "ant-" + "A1" * 12,
        "GitHub token": "gh" + "p_" + "A" * 36,
        "AWS access key": "AK" + "IA" + "ABCDEFGHIJKLMNOP",
        "Slack token": "xo" + "xb-" + "1234567890-abc",
        "JWT": "ey" + "J" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
        "credential assignment": "pass" + "word=" + "hunter2hunter2",
    }
    for kind, sample in samples.items():
        with scratch() as tmp:
            folder = new_handover(tmp)
            write(folder / handover.CORE_FILE, CORE + f"\nnote: {sample}\n")
            write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
            code, out = run("check", str(folder))
            assert code == 1 and f"possible {kind} in handover.md:" in out, (kind, out)
            assert sample not in out, f"the {kind} was echoed"


def test_secret_scan_leaves_ordinary_text_alone() -> None:
    with scratch() as tmp:
        folder = new_handover(tmp)
        ordinary = (
            "Never print the password: <ask the user>. Keys use the sk- prefix. token: short.\n"
            "Run `gh pr view`. The API key lives in .env, which is never read.\n"
        )
        write(folder / handover.CORE_FILE, CORE + ordinary)
        write(folder / "files" / "notes.txt", ordinary)
        write(folder / handover.PROMPT_FILE, PROMPT.format(folder=folder))
        assert handover.check(folder)[0] == []


if __name__ == "__main__":
    sys.exit(handover.self_test())
