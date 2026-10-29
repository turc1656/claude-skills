"""Regression tests for atdd_lock.py.

Run with pytest (`pytest test_atdd_lock.py`) or without it (`python atdd_lock.py --self-test`).
Plain asserts and the standard library only, so both paths work everywhere the skill runs.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atdd_lock  # noqa: E402

PYTHON = "python" if shutil.which("python") else "python3"
MANUAL_ERROR = 64  # how run() reports sys.exit("message"), the script's argument-error path


class Repo:
    """A throwaway repository with a frozen command whose exit code the test controls via rc.txt."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tests").mkdir()
        self.write("rc.py", 'import pathlib, sys\nsys.exit(int(pathlib.Path("rc.txt").read_text()))\n')
        self.write("tests/test_a.py", "def test_a():\n    assert False\n")
        self.write("tests/support.py", "x = 1\n")
        self.rc(1)
        self.approve_args = [
            "approve", "--feature", "f", "--story", "#1", "--run", f"{PYTHON} rc.py",
            "--tests", "tests/test_a.py", "--support", "tests/support.py",
        ]

    def close(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        (self.root / rel).write_bytes(text.encode("utf-8"))

    def rc(self, code: int) -> None:
        """What the frozen command will exit with on its next run."""
        self.write("rc.txt", str(code))

    def run(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                code = atdd_lock.main(["--repo", str(self.root), *argv])
            except SystemExit as e:
                if isinstance(e.code, str):  # the script's error path: message, exit 1
                    buf.write(e.code + "\n")
                    code = MANUAL_ERROR
                else:
                    code = int(e.code or 0)
        return code, buf.getvalue()

    def manifest(self) -> dict:
        return json.loads((self.root / ".atdd" / "f" / "manifest.json").read_text(encoding="utf-8"))

    def approve(self, *extra: str) -> tuple[int, str]:
        return self.run(*self.approve_args, *extra)


def test_fresh_approve_then_check_is_clean() -> None:
    repo = Repo()
    try:
        assert repo.run("check", "--feature", "f")[0] == 2, "no manifest yet"
        code, out = repo.approve()
        assert code == 0, out
        assert repo.run("check", "--feature", "f")[0] == 0
        assert repo.run("check", "--repo", str(repo.root), "--feature", "f")[0] == 0, "--repo after the subcommand"
        assert repo.manifest()["status"] == "approved"
    finally:
        repo.close()


def test_crlf_and_lf_hash_alike() -> None:
    repo = Repo()
    try:
        repo.write("tests/support.py", "x = 1\r\n")
        assert repo.approve()[0] == 0
        repo.write("tests/support.py", "x = 1\n")
        assert repo.run("check", "--feature", "f")[0] == 0, "line endings must not count as drift"
    finally:
        repo.close()


def test_drift_is_detected_and_blocks_reapproval_without_unlock() -> None:
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        repo.write("tests/test_a.py", "def test_a():\n    assert True\n")
        assert repo.run("check", "--feature", "f")[0] == 1, "drift"
        code, out = repo.approve()
        assert code == 1 and "changed test tests/test_a.py" in out, out
        assert repo.run("unlock", "--feature", "f", "--reason", "wrong expectation")[0] == 0
        assert repo.run("check", "--feature", "f")[0] == 3, "amendment open"
        assert repo.run("unlock", "--feature", "f", "--reason", "again")[0] == 1, "one amendment at a time"
        assert repo.approve()[0] == 0, "re-approval closes the amendment"
        assert repo.run("check", "--feature", "f")[0] == 0
        assert repo.manifest()["amendments"][0]["reapproved_at"]
    finally:
        repo.close()


def test_issue1_approve_cannot_alter_frozen_set_or_run_without_amend() -> None:
    """Issue 1: while approved, approve must not replace files, the run command, the cwd or the story."""
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        code, out = repo.approve()
        assert code == 0 and "nothing changed" in out, "identical re-approval is a harmless no-op"

        fewer = ["approve", "--feature", "f", "--story", "#1", "--run", f"{PYTHON} rc.py", "--tests", "tests/test_a.py"]
        code, out = repo.run(*fewer)
        assert code == 1 and "removed support tests/support.py" in out, out

        repo.write("tests/test_b.py", "def test_b():\n    assert False\n")
        code, out = repo.run(*repo.approve_args[:-2], "--tests", "tests/test_a.py", "tests/test_b.py",
                             "--support", "tests/support.py")
        assert code == 1 and "added test tests/test_b.py" in out, out

        weaker = list(repo.approve_args)
        weaker[weaker.index("--run") + 1] = f"{PYTHON} -c pass"
        code, out = repo.run(*weaker)
        assert code == 1 and "run command changed" in out, out

        code, out = repo.approve("--cwd", "tests")
        assert code == 1 and "working directory changed" in out, out

        rescoped = list(repo.approve_args)
        rescoped[rescoped.index("--story") + 1] = "#2"
        code, out = repo.run(*rescoped)
        assert code == 1 and "story changed" in out, out

        m = repo.manifest()
        assert [f["path"] for f in m["files"]] == ["tests/test_a.py", "tests/support.py"]
        assert m["run"] == {"command": f"{PYTHON} rc.py", "cwd": "."} and m["story"] == "#1"

        assert repo.run("unlock", "--feature", "f", "--reason", "re-scope")[0] == 0
        assert repo.run(*rescoped)[0] == 0, "the same change goes through once an amendment is open"
        assert repo.manifest()["story"] == "#2"
    finally:
        repo.close()


def test_issue2_reapproval_with_changes_resets_evidence_and_keeps_it_on_the_amendment() -> None:
    """Issue 2: evidence recorded against old specifications must not survive a content change."""
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        repo.rc(1)
        assert repo.run("record", "--feature", "f", "--phase", "red", "--summary", "missing reserve")[0] == 0
        repo.rc(0)
        assert repo.run("record", "--feature", "f", "--phase", "green")[0] == 0
        assert set(repo.manifest()["evidence"]) == {"red", "green"}

        assert repo.run("unlock", "--feature", "f", "--reason", "cosmetic")[0] == 0
        assert repo.approve()[0] == 0, "amendment closed without any change"
        m = repo.manifest()
        assert set(m["evidence"]) == {"red", "green"}, "no change, evidence kept"
        assert m["amendments"][0]["changes"] == [] and "superseded_evidence" not in m["amendments"][0]

        assert repo.run("unlock", "--feature", "f", "--reason", "expectation was wrong")[0] == 0
        repo.write("tests/test_a.py", "def test_a():\n    assert 1 == 2\n")
        code, out = repo.approve()
        assert code == 0 and "evidence reset" in out, out
        m = repo.manifest()
        assert m["evidence"] == {}, "stale evidence cleared"
        assert m["amendments"][1]["changes"] == ["changed test tests/test_a.py"]
        assert set(m["amendments"][1]["superseded_evidence"]) == {"red", "green"}, "old evidence kept for traceability"
    finally:
        repo.close()


def test_issue3_record_enforces_phase_order_and_lock_state() -> None:
    """Issue 3: record must respect red -> green -> verify and refuse while amending or drifted."""
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        repo.rc(0)
        code, out = repo.run("record", "--feature", "f", "--phase", "green")
        assert code == 1 and "no red evidence" in out, out
        code, out = repo.run("record", "--feature", "f", "--phase", "red")
        assert code == 1 and "passing test specifies nothing" in out, out
        code, out = repo.run("record", "--feature", "f", "--phase", "verify", "--exit-code", "0", "--summary", "ok")
        assert code == 1 and "no green evidence" in out, out

        repo.rc(1)
        assert repo.run("record", "--feature", "f", "--phase", "red", "--summary", "missing reserve")[0] == 0
        code, out = repo.run("record", "--feature", "f", "--phase", "green")
        assert code == 1 and "requires a passing run" in out, out
        repo.rc(0)
        assert repo.run("record", "--feature", "f", "--phase", "green")[0] == 0
        repo.rc(1)
        code, out = repo.run("record", "--feature", "f", "--phase", "red")
        assert code == 1 and "regression" in out, "red after green is a regression, not red"
        assert repo.run("record", "--feature", "f", "--phase", "verify", "--exit-code", "0", "--summary", "9 passed")[0] == 0

        repo.write("tests/support.py", "x = 2\n")
        code, out = repo.run("record", "--feature", "f", "--phase", "verify", "--exit-code", "0", "--summary", "ok")
        assert code == 1 and "drifted" in out, out
        assert repo.run("unlock", "--feature", "f", "--reason", "fix")[0] == 0
        code, out = repo.run("record", "--feature", "f", "--phase", "verify", "--exit-code", "0", "--summary", "ok")
        assert code == 1 and "amendment is open" in out, out
    finally:
        repo.close()


def test_record_runs_the_frozen_command_and_flags_manual_records() -> None:
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        repo.rc(3)
        code, out = repo.run("record", "--feature", "f", "--phase", "red")
        assert code == 0 and repo.manifest()["evidence"]["red"]["exit_code"] == 3, out
        assert repo.manifest()["evidence"]["red"]["manual"] is False
        repo.rc(0)
        assert repo.run("record", "--feature", "f", "--phase", "green", "--exit-code", "0", "--summary", "ran by hand")[0] == 0
        assert repo.manifest()["evidence"]["green"]["manual"] is True
        assert repo.run("record", "--feature", "f", "--phase", "green", "--exit-code", "0")[0] == MANUAL_ERROR, "manual needs --summary"
        assert repo.run("record", "--feature", "f", "--phase", "verify")[0] == MANUAL_ERROR, "verify is always manual"
    finally:
        repo.close()


def test_auto_summary_prefers_the_last_stdout_line() -> None:
    """Tool setup noise on stderr (uv creating a venv) must not displace the runner's totals line."""
    repo = Repo()
    try:
        repo.write("rc.py", 'import sys\nprint("2 failed, 3 passed")\nprint("Creating virtual environment", file=sys.stderr)\nsys.exit(1)\n')
        assert repo.approve()[0] == 0
        assert repo.run("record", "--feature", "f", "--phase", "red")[0] == 0
        assert repo.manifest()["evidence"]["red"]["summary"] == "2 failed, 3 passed"
    finally:
        repo.close()


def test_red_waiver_is_explicit_and_recorded() -> None:
    repo = Repo()
    try:
        assert repo.approve()[0] == 0
        repo.rc(0)
        assert repo.run("record", "--feature", "f", "--phase", "red", "--red-waived", "x")[0] == MANUAL_ERROR, "green only"
        code, out = repo.run("record", "--feature", "f", "--phase", "green", "--red-waived", "behaviour already existed; user approved")
        assert code == 0 and "red waived" in out, out
        assert repo.manifest()["evidence"]["green"]["red_waived"].startswith("behaviour already existed")
        code, out = repo.run("status", "--feature", "f")
        assert code == 0 and "red waived" in out
    finally:
        repo.close()


def feature_args(repo: Repo, name: str) -> list[str]:
    args = list(repo.approve_args)
    args[args.index("--feature") + 1] = name
    return args


def try_link(link: Path, target: Path) -> bool:
    """A directory symlink, or a junction on Windows where symlinks need privileges."""
    try:
        os.symlink(str(target), str(link), target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return done.returncode == 0 and link.exists()
    return False


def remove_link(link: Path) -> None:
    try:
        os.unlink(link)
    except OSError:
        os.rmdir(link)


def test_feature_name_cannot_escape_atdd() -> None:
    """A feature is one name: traversal, absolute paths, separators and device names are refused before any write."""
    repo = Repo()
    outside = tempfile.TemporaryDirectory()
    try:
        bad = ["../../outside-atdd", "..", ".", "a/b", "a\\b", "/abs", str(Path(outside.name) / "abs-feature"),
               "con", "NUL.txt", "trailing.", "", "sp ace"]
        for name in bad:
            code, out = repo.run(*feature_args(repo, name))
            assert code == MANUAL_ERROR and "--feature" in out, (name, code, out)
        assert not (repo.root.parent / "outside-atdd").exists()
        assert not (Path(outside.name) / "abs-feature").exists()
        assert not (repo.root / ".atdd").exists(), "nothing is written for a refused name"
        for command in (["check"], ["unlock", "--reason", "r"], ["record", "--phase", "red"], ["status"]):
            assert repo.run(*command, "--feature", "../x")[0] == MANUAL_ERROR, command
        for name in ("f", "135-garage-reservations", "v1.2_x"):
            assert repo.run(*feature_args(repo, name))[0] == 0, name
            assert (repo.root / ".atdd" / name / "manifest.json").is_file()
    finally:
        outside.cleanup()
        repo.close()


def test_feature_symlink_or_junction_escape_is_refused() -> None:
    """A link at .atdd/<feature> or at .atdd/ itself must not redirect the manifest outside the repository."""
    repo = Repo()
    outside = tempfile.TemporaryDirectory()
    outside_dir = Path(outside.name)
    atdd = repo.root / ".atdd"
    links: list[Path] = []
    try:
        atdd.mkdir()
        evil = atdd / "evil"
        if not try_link(evil, outside_dir):
            print("  (no symlink or junction support here; escape-by-link assertions skipped)")
            return
        links.append(evil)
        code, out = repo.run(*feature_args(repo, "evil"))
        assert code == MANUAL_ERROR and "resolves outside" in out, out
        assert not (outside_dir / "manifest.json").exists()
        remove_link(evil)
        links.remove(evil)

        atdd.rmdir()
        assert try_link(atdd, outside_dir)
        links.append(atdd)
        code, out = repo.run(*repo.approve_args)
        assert code == MANUAL_ERROR and "resolves outside" in out, out
        assert not (outside_dir / "f").exists()
    finally:
        for link in links:
            try:
                remove_link(link)
            except OSError:
                pass
        outside.cleanup()
        repo.close()


MANIFEST_COMMANDS = (
    ["unlock", "--feature", "f", "--reason", "probe"],
    ["check", "--feature", "f"],
    ["status", "--feature", "f"],
    ["record", "--feature", "f", "--phase", "red", "--exit-code", "1", "--summary", "probe"],
)


def refused_everywhere(repo: Repo, victim: Path | None) -> None:
    """Every command that reads or writes the manifest refuses, and the outside file is untouched."""
    before = victim.read_bytes() if victim is not None and victim.exists() else None
    for command in MANIFEST_COMMANDS:
        code, out = repo.run(*command)
        assert code == MANUAL_ERROR and "manifest.json" in out, (command, code, out)
    code, out = repo.approve()
    assert code == MANUAL_ERROR and "manifest.json" in out, ("approve", code, out)
    code, out = repo.run("status")
    assert code == 0 and "f: skipped" in out, "a listing skips the entry instead of following it"
    if victim is not None:
        after = victim.read_bytes() if victim.exists() else None
        assert after == before, "the file outside the repository must not change or appear"


def test_manifest_file_symlink_is_refused() -> None:
    """A symlink at .atdd/<feature>/manifest.json, live or dangling, must not be read or written through."""
    repo = Repo()
    outside = tempfile.TemporaryDirectory()
    try:
        assert repo.approve()[0] == 0
        manifest = repo.root / ".atdd" / "f" / "manifest.json"
        victim = Path(outside.name) / "victim.json"
        shutil.copy(manifest, victim)
        manifest.unlink()
        try:
            os.symlink(str(victim), str(manifest))
        except (OSError, NotImplementedError):
            print("  (no file symlink support here; symlink assertions skipped, hard-link test still runs)")
            return
        refused_everywhere(repo, victim)

        manifest.unlink()
        dangling = Path(outside.name) / "created-through-link.json"
        os.symlink(str(dangling), str(manifest))
        refused_everywhere(repo, dangling)
        assert not dangling.exists(), "a dangling link must not create the outside file"
    finally:
        outside.cleanup()
        repo.close()


def test_manifest_file_hard_link_is_refused() -> None:
    """A hard link shares the outside file's contents; a write through it would change that file."""
    repo = Repo()
    outside = tempfile.TemporaryDirectory()
    try:
        assert repo.approve()[0] == 0
        manifest = repo.root / ".atdd" / "f" / "manifest.json"
        victim = Path(outside.name) / "victim.json"
        shutil.copy(manifest, victim)
        manifest.unlink()
        try:
            os.link(str(victim), str(manifest))
        except (OSError, NotImplementedError):
            print("  (no hard-link support here; assertions skipped)")
            return
        refused_everywhere(repo, victim)
    finally:
        outside.cleanup()
        repo.close()


def test_manifest_must_be_a_regular_file_and_saves_are_atomic() -> None:
    repo = Repo()
    try:
        (repo.root / ".atdd" / "f" / "manifest.json").mkdir(parents=True)
        code, out = repo.approve()
        assert code == MANUAL_ERROR and "not a regular file" in out, out
        shutil.rmtree(repo.root / ".atdd")

        assert repo.approve()[0] == 0
        assert repo.run("unlock", "--feature", "f", "--reason", "r")[0] == 0
        assert repo.approve()[0] == 0
        manifest = repo.root / ".atdd" / "f" / "manifest.json"
        assert os.lstat(manifest).st_nlink == 1 and not manifest.is_symlink()
        assert b"\r\n" not in manifest.read_bytes(), "manifests are written with LF"
        leftovers = [p.name for p in manifest.parent.iterdir() if p.name != "manifest.json"]
        assert leftovers == [], f"temporary files left behind: {leftovers}"
    finally:
        repo.close()


def test_cwd_stays_inside_the_repo_and_nested_dirs_work() -> None:
    """--cwd is validated against the canonical root; monorepo package directories still work."""
    repo = Repo()
    outside = tempfile.TemporaryDirectory()
    links: list[Path] = []
    try:
        nested = repo.root / "packages" / "api"
        nested.mkdir(parents=True)
        shutil.copy(repo.root / "rc.py", nested / "rc.py")
        bad = ["..", "../", "tests/../..", str(Path(outside.name)), "/", "missing-dir", "rc.py"]
        if os.name == "nt":
            bad += ["C:\\", "C:relative"]
        for cwd in bad:
            code, out = repo.approve("--cwd", cwd)
            assert code == MANUAL_ERROR and "--cwd" in out, (cwd, code, out)
        assert not (repo.root / ".atdd").exists(), "nothing is written for a refused --cwd"

        assert repo.approve("--cwd", "./packages/api/")[0] == 0
        assert repo.manifest()["run"]["cwd"] == "packages/api", "stored in normalised relative POSIX form"
        if os.name == "nt":
            code, out = repo.approve("--cwd", "packages\\api")
            assert code == 0 and "nothing changed" in out, "the backslash form is the same directory"
        (nested / "rc.txt").write_text("1")
        assert repo.run("record", "--feature", "f", "--phase", "red")[0] == 0, "the command ran in the nested directory"

        manifest_file = repo.root / ".atdd" / "f" / "manifest.json"
        m = json.loads(manifest_file.read_text(encoding="utf-8"))
        m["run"]["cwd"] = "../"
        manifest_file.write_text(json.dumps(m), encoding="utf-8")
        code, out = repo.run("record", "--feature", "f", "--phase", "green")
        assert code == MANUAL_ERROR and "--cwd" in out, "a hand-edited manifest cannot move the run outside"

        link = repo.root / "linked"
        if try_link(link, Path(outside.name)):
            links.append(link)
            code, out = repo.run(*feature_args(repo, "g"), "--cwd", "linked")
            assert code == MANUAL_ERROR and "--cwd" in out, out
    finally:
        for link in links:
            try:
                remove_link(link)
            except OSError:
                pass
        outside.cleanup()
        repo.close()
