"""Behaviour tests for scripts/atelier.py. Run from the repo root:

    python3 -m unittest discover -s plugins/atelier/scripts/tests -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atelier.py"

CARD_BODY = {
    "Goal": "Produce the login page.",
    "Constraints": "Never store passwords in plain text.",
    "Quality bar": "- Page loads in under 2 seconds.\n- 0 failing tests.",
    "Examples and references": "See docs/style.md.",
    "Approval checkpoint": "none",
    "Fixed decisions": "Use the approved voice recording.",
    "Left open on purpose": "none",
}
HANDOFF_BODY = {
    "What was done": "Built the page.",
    "Files changed": "src/login.html",
    "Against the quality bar": "- Load time 1.2 s.\n- 0 failing tests.",
    "Not done or open issues": "none",
    "How to verify": "Open src/login.html.",
}


def fill_sections(path, values):
    text = path.read_text()
    for heading, content in values.items():
        pattern = re.compile(r"(^## %s\n(?:<!--.*?-->\n)?)" % re.escape(heading), re.M)
        text, n = pattern.subn(lambda m: m.group(1) + content + "\n", text, count=1)
        assert n == 1, heading
    path.write_text(text)


def set_meta(path, key, value):
    text = path.read_text()
    text, n = re.subn(r"^%s:.*$" % re.escape(key), "%s: %s" % (key, value), text, count=1, flags=re.M)
    assert n == 1, key
    path.write_text(text)


class AtelierTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="atelier-test-"))
        self.root = self.tmp / "proj"
        self.root.mkdir()
        self.home = self.tmp / "home"
        self.env = dict(os.environ)
        for key in ("ATELIER_ROOT", "CLAUDE_PROJECT_DIR"):
            self.env.pop(key, None)
        self.env["ATELIER_HOME"] = str(self.home)

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    @property
    def st(self):
        return self.root / ".atelier"

    def run_cli(self, *args, stdin=None, script=SCRIPT, cwd=None, env=None, root=True):
        cmd = [sys.executable, str(script)] + (["--root", str(self.root)] if root else []) + list(args)
        return subprocess.run(cmd, input=stdin if stdin is not None else "", capture_output=True, text=True,
                              cwd=str(cwd or self.tmp), env=env or self.env, timeout=120)

    def ok(self, *args, **kw):
        r = self.run_cli(*args, **kw)
        self.assertEqual(r.returncode, 0, "stdout:%s\nstderr:%s" % (r.stdout, r.stderr))
        return r

    def init(self):
        return self.ok("init")

    def status_of(self, tid):
        return re.search(r"^status:\s*(.*)$", (self.st / "tasks" / ("%s.md" % tid)).read_text(), re.M).group(1)

    def make_ready_task(self, tid="T-01", author="worker-a", reviewer="reviewer-b", owner="", result="pass"):
        self.ok("new-task", tid, "Login page")
        card = self.st / "tasks" / ("%s.md" % tid)
        fill_sections(card, CARD_BODY)
        if owner:
            set_meta(card, "owner", owner)
        self.ok("new-handoff", tid, "--author", author)
        fill_sections(self.st / "handoffs" / ("%s.md" % tid), HANDOFF_BODY)
        self.ok("new-gate", tid, "--reviewer", reviewer)
        gate = self.st / "gates" / ("%s.md" % tid)
        set_meta(gate, "result", result)
        fill_sections(gate, {"Measurements": "- load 1.2 s: pass\n- tests 0 failing: pass", "Findings": "none"})

    def add_check(self, name, body, executable=False):
        path = self.st / "checks" / name
        path.write_text(body)
        if executable:
            path.chmod(0o755)
        return path

    def hook(self, event, payload=None, raw=None):
        stdin = raw if raw is not None else json.dumps(payload or {})
        return self.run_cli("hook", event, stdin=stdin)


class TestInit(AtelierTestCase):
    def test_init_creates_layout(self):
        r = self.init()
        for d in ("tasks", "handoffs", "gates", "checks", "bin", "bin/templates"):
            self.assertTrue((self.st / d).is_dir(), d)
        for f in ("contract.md", "board.md", "lessons.md", "rejections.md", "shelf.md"):
            self.assertTrue((self.st / f).is_file(), f)
        self.assertTrue((self.st / "bin" / "atelier.py").is_file())
        self.assertTrue(os.access(str(self.st / "bin" / "atelier.py"), os.X_OK))
        self.assertTrue((self.st / "bin" / "templates" / "task.md").is_file())
        self.assertTrue((self.home / "rejections.md").is_file())
        self.assertIn("atelier ready", r.stdout)

    def test_init_keeps_existing_files_without_force(self):
        self.init()
        (self.st / "contract.md").write_text("MY CONTRACT")
        self.init()
        self.assertEqual((self.st / "contract.md").read_text(), "MY CONTRACT")

    def test_init_force_overwrites(self):
        self.init()
        (self.st / "contract.md").write_text("MY CONTRACT")
        self.ok("init", "--force")
        self.assertIn("# Contract", (self.st / "contract.md").read_text())

    def test_init_refreshes_bin_copy(self):
        self.init()
        (self.st / "bin" / "atelier.py").write_text("stale")
        (self.st / "bin" / "templates" / "task.md").write_text("stale")
        self.init()
        self.assertEqual((self.st / "bin" / "atelier.py").read_text(), SCRIPT.read_text())
        self.assertNotEqual((self.st / "bin" / "templates" / "task.md").read_text(), "stale")

    def test_bin_copy_works_with_its_own_templates(self):
        self.init()
        r = self.run_cli("new-task", "T-05", "From bin", script=self.st / "bin" / "atelier.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("title: From bin", (self.st / "tasks" / "T-05.md").read_text())

    def test_init_fails_when_root_is_a_file(self):
        bad = self.tmp / "afile"
        bad.write_text("x")
        r = self.run_cli("--root", str(bad), "init", root=False)
        self.assertEqual(r.returncode, 1)


class TestRootResolution(AtelierTestCase):
    def test_env_atelier_root(self):
        env = dict(self.env, ATELIER_ROOT=str(self.root))
        r = self.run_cli("init", root=False, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(self.st.is_dir())

    def test_claude_project_dir_and_cwd(self):
        env = dict(self.env, CLAUDE_PROJECT_DIR=str(self.root))
        self.assertEqual(self.run_cli("init", root=False, env=env).returncode, 0)
        other = self.tmp / "other"
        other.mkdir()
        self.assertEqual(self.run_cli("init", root=False, cwd=other).returncode, 0)
        self.assertTrue((other / ".atelier").is_dir())

    def test_commands_fail_without_atelier(self):
        for args in (["new-task", "T-01", "x"], ["gate", "T-01"], ["check-card", "T-01"], ["run-checks"],
                     ["lesson", "tag", "x"], ["set-status", "T-01", "todo"], ["check-handoff", "T-01"]):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("init", r.stderr)


class TestNewFiles(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_new_task_fills_placeholders(self):
        self.ok("new-task", "T-01", "Login page")
        text = (self.st / "tasks" / "T-01.md").read_text()
        self.assertIn("id: T-01", text)
        self.assertIn("title: Login page", text)
        self.assertIn("# T-01: Login page", text)
        self.assertNotIn("{{", text)

    def test_new_task_refuses_duplicate_and_bad_id(self):
        self.ok("new-task", "T-01", "x")
        self.assertEqual(self.run_cli("new-task", "T-01", "y").returncode, 1)
        self.assertEqual(self.run_cli("new-task", "../evil", "y").returncode, 1)
        self.assertFalse((self.st / "evil.md").exists())

    def test_new_handoff_sets_author(self):
        self.ok("new-task", "T-01", "x")
        self.ok("new-handoff", "T-01", "--author", "worker-a")
        text = (self.st / "handoffs" / "T-01.md").read_text()
        self.assertIn("author: worker-a", text)
        self.assertIn("task: T-01", text)

    def test_new_handoff_needs_card(self):
        r = self.run_cli("new-handoff", "T-09")
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.st / "handoffs" / "T-09.md").exists())

    def test_new_gate_sets_reviewer(self):
        self.ok("new-task", "T-01", "x")
        self.ok("new-gate", "T-01", "--reviewer", "rev")
        text = (self.st / "gates" / "T-01.md").read_text()
        self.assertIn("reviewer: rev", text)
        self.assertIn("result: fail", text)

    def test_new_gate_refuses_duplicate(self):
        self.ok("new-task", "T-01", "x")
        self.ok("new-gate", "T-01")
        self.assertEqual(self.run_cli("new-gate", "T-01").returncode, 1)


class TestChecksOfFiles(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_check_card_pass(self):
        self.ok("new-task", "T-01", "x")
        fill_sections(self.st / "tasks" / "T-01.md", CARD_BODY)
        r = self.ok("check-card", "T-01")
        self.assertNotIn("FAIL", r.stdout)

    def test_check_card_fails_on_template(self):
        self.ok("new-task", "T-01", "x")
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card section 'Goal' is filled", r.stdout)
        self.assertIn("FAIL card quality bar holds at least one number", r.stdout)

    def test_check_card_needs_number_in_quality_bar(self):
        self.ok("new-task", "T-01", "x")
        fill_sections(self.st / "tasks" / "T-01.md", dict(CARD_BODY, **{"Quality bar": "Looks good."}))
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card quality bar holds at least one number", r.stdout)
        self.assertIn("PASS card section 'Quality bar' is filled", r.stdout)

    def test_check_card_fails_without_fixed_decisions(self):
        self.ok("new-task", "T-01", "x")
        body = dict(CARD_BODY)
        body.pop("Fixed decisions")
        fill_sections(self.st / "tasks" / "T-01.md", body)
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card section 'Fixed decisions' is filled", r.stdout)
        self.assertIn("PASS card section 'Left open on purpose' is filled", r.stdout)

    def test_check_card_fails_without_left_open(self):
        self.ok("new-task", "T-01", "x")
        body = dict(CARD_BODY)
        body.pop("Left open on purpose")
        fill_sections(self.st / "tasks" / "T-01.md", body)
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card section 'Left open on purpose' is filled", r.stdout)
        self.assertIn("PASS card section 'Fixed decisions' is filled", r.stdout)

    def test_check_card_new_sections_pass_with_none(self):
        self.ok("new-task", "T-01", "x")
        fill_sections(self.st / "tasks" / "T-01.md",
                      dict(CARD_BODY, **{"Fixed decisions": "none", "Left open on purpose": "none"}))
        r = self.ok("check-card", "T-01")
        self.assertIn("PASS card section 'Fixed decisions' is filled", r.stdout)
        self.assertIn("PASS card section 'Left open on purpose' is filled", r.stdout)

    def test_bare_bullets_headings_punctuation_count_as_empty(self):
        self.ok("new-task", "T-01", "x")
        fill_sections(self.st / "tasks" / "T-01.md",
                      dict(CARD_BODY, **{"Goal": "-", "Constraints": "### Later\n*\n", "Fixed decisions": "...\n- \n"}))
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        for name in ("Goal", "Constraints", "Fixed decisions"):
            self.assertIn("FAIL card section '%s' is filled" % name, r.stdout)
        self.assertIn("PASS card section 'Left open on purpose' is filled", r.stdout)

    def test_fail_lines_name_file_and_who_fixes(self):
        self.ok("new-task", "T-01", "x")
        r = self.run_cli("check-card", "T-01")
        self.assertIn("FAIL card section 'Goal' is filled (lead: fix it in .atelier/tasks/T-01.md)", r.stdout)
        self.ok("new-handoff", "T-01")
        r = self.run_cli("check-handoff", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL handoff author is set (worker: set `author:` in .atelier/handoffs/T-01.md)", r.stdout)
        self.assertIn("(worker: fill it in .atelier/handoffs/T-01.md)", r.stdout)
        self.ok("new-gate", "T-01")
        r = self.run_cli("gate", "T-01")
        self.assertIn("FAIL gate reviewer is set (reviewer: set `reviewer:` in .atelier/gates/T-01.md)", r.stdout)
        self.assertIn("FAIL gate result is pass (found 'fail') (reviewer: fix it in .atelier/gates/T-01.md)",
                      r.stdout)

    def test_check_card_id_mismatch(self):
        self.ok("new-task", "T-01", "x")
        card = self.st / "tasks" / "T-01.md"
        fill_sections(card, CARD_BODY)
        set_meta(card, "id", "T-02")
        r = self.run_cli("check-card", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card front matter id", r.stdout)

    def test_check_handoff_pass(self):
        self.ok("new-task", "T-01", "x")
        self.ok("new-handoff", "T-01", "--author", "w")
        fill_sections(self.st / "handoffs" / "T-01.md", HANDOFF_BODY)
        self.ok("check-handoff", "T-01")

    def test_check_handoff_missing_and_no_author(self):
        self.ok("new-task", "T-01", "x")
        r = self.run_cli("check-handoff", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("new-handoff T-01", r.stdout)
        self.ok("new-handoff", "T-01")
        fill_sections(self.st / "handoffs" / "T-01.md", HANDOFF_BODY)
        r = self.run_cli("check-handoff", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL handoff author is set", r.stdout)

    def test_check_handoff_comment_only_section_is_empty(self):
        self.ok("new-task", "T-01", "x")
        self.ok("new-handoff", "T-01", "--author", "w")
        body = dict(HANDOFF_BODY)
        body.pop("Not done or open issues")
        fill_sections(self.st / "handoffs" / "T-01.md", body)
        r = self.run_cli("check-handoff", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL handoff section 'Not done or open issues' is filled", r.stdout)


class TestGate(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_gate_pass_marks_done(self):
        self.make_ready_task()
        r = self.ok("gate", "T-01")
        self.assertIn("Gate T-01: PASS", r.stdout)
        self.assertNotIn("FAIL", r.stdout)
        self.assertEqual(self.status_of("T-01"), "done")

    def test_gate_fails_when_reviewer_is_author(self):
        self.make_ready_task(author="Worker-A", reviewer=" worker-a ")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL reviewer", r.stdout)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_gate_fails_when_reviewer_is_owner(self):
        self.make_ready_task(owner="boss", reviewer="Boss")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not the card owner", r.stdout)

    def test_gate_and_set_status_fail_when_card_lacks_fixed_decisions(self):
        self.make_ready_task()
        card = self.st / "tasks" / "T-01.md"
        card.write_text(card.read_text().replace("Use the approved voice recording.\n", ""))
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL card section 'Fixed decisions' is filled", r.stdout)
        self.assertEqual(self.run_cli("set-status", "T-01", "done").returncode, 1)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_gate_requires_reviewer_assigned_on_card(self):
        self.make_ready_task(reviewer="reviewer-c")
        set_meta(self.st / "tasks" / "T-01.md", "reviewer", "reviewer-b")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL reviewer 'reviewer-c' is the one assigned on the card (reviewer-b)", r.stdout)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_gate_passes_with_assigned_reviewer(self):
        self.make_ready_task(reviewer="Reviewer-B")
        set_meta(self.st / "tasks" / "T-01.md", "reviewer", "reviewer-b")
        r = self.ok("gate", "T-01")
        self.assertIn("PASS reviewer 'Reviewer-B' is the one assigned on the card", r.stdout)

    def test_gate_fails_on_dash_only_measurements(self):
        self.make_ready_task()
        gate = self.st / "gates" / "T-01.md"
        gate.write_text(gate.read_text().replace("- load 1.2 s: pass\n- tests 0 failing: pass\n", "-\n"))
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL gate section 'Measurements' is filled", r.stdout)

    def test_gate_fails_on_result_fail(self):
        self.make_ready_task(result="fail")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL gate result is pass", r.stdout)

    def test_gate_fails_without_report(self):
        self.make_ready_task()
        (self.st / "gates" / "T-01.md").unlink()
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("new-gate T-01", r.stdout)

    def test_gate_fails_on_empty_measurements(self):
        self.make_ready_task()
        gate = self.st / "gates" / "T-01.md"
        gate.write_text(gate.read_text().replace("- load 1.2 s: pass\n- tests 0 failing: pass\n", ""))
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL gate section 'Measurements' is filled", r.stdout)

    def test_gate_fails_when_a_check_fails(self):
        self.make_ready_task()
        self.add_check("no_todo.py", "import sys\nprint('found TODO')\nsys.exit(2)\n")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL check no_todo.py (exit 2)", r.stdout)
        self.assertIn("found TODO", r.stdout)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_gate_fails_on_repeated_lesson_without_check(self):
        self.make_ready_task()
        self.run_cli("lesson", "typo", "one")
        self.run_cli("lesson", "typo", "two")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("lesson 'typo' repeated", r.stdout)


class TestStaleGate(AtelierTestCase):
    """A gate report is tied to the card's quality bar and the handoff note it reviewed."""

    def setUp(self):
        super().setUp()
        self.init()
        self.make_ready_task()
        self.gate_file = self.st / "gates" / "T-01.md"

    def test_new_gate_records_hashes(self):
        text = self.gate_file.read_text()
        self.assertRegex(text, r"(?m)^card_hash: [0-9a-f]{12}$")
        self.assertRegex(text, r"(?m)^handoff_hash: [0-9a-f]{12}$")
        r = self.ok("gate", "T-01")
        self.assertIn("PASS the card's quality bar is unchanged since this review", r.stdout)
        self.assertIn("PASS the handoff note is unchanged since this review", r.stdout)

    def test_hash_ignores_comments_and_whitespace(self):
        card = self.st / "tasks" / "T-01.md"
        card.write_text(card.read_text().replace("- 0 failing tests.", "-   0 failing   tests.\n<!-- note -->\n"))
        self.ok("gate", "T-01")

    def test_gate_fails_when_handoff_changed(self):
        handoff = self.st / "handoffs" / "T-01.md"
        handoff.write_text(handoff.read_text().replace("Built the page.", "Built the page, then rewrote it."))
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL the handoff note changed after this review", r.stdout)
        self.assertIn("new-gate T-01 --reviewer NAME --force", r.stdout)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_gate_fails_when_quality_bar_changed(self):
        card = self.st / "tasks" / "T-01.md"
        card.write_text(card.read_text().replace("under 2 seconds", "under 5 seconds"))
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL the card's quality bar changed after this review", r.stdout)
        self.assertEqual(self.run_cli("set-status", "T-01", "done").returncode, 1)

    def test_gate_fails_when_hashes_missing(self):
        text = re.sub(r"(?m)^(card_hash|handoff_hash):.*\n", "", self.gate_file.read_text())
        self.gate_file.write_text(text)
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL gate report records card_hash", r.stdout)
        self.assertIn("FAIL gate report records handoff_hash", r.stdout)

    def test_new_gate_force_archives_and_new_review_passes(self):
        card = self.st / "tasks" / "T-01.md"
        card.write_text(card.read_text().replace("under 2 seconds", "under 5 seconds"))
        self.assertEqual(self.run_cli("new-gate", "T-01", "--reviewer", "reviewer-b").returncode, 1)
        r = self.ok("new-gate", "T-01", "--reviewer", "reviewer-b", "--force")
        self.assertIn("Archived the old gate report", r.stdout)
        self.assertEqual(len(list((self.st / "gates" / "archive").glob("T-01-*.md"))), 1)
        self.assertEqual(self.run_cli("gate", "T-01").returncode, 1)  # fresh report is not filled in yet
        set_meta(self.gate_file, "result", "pass")
        fill_sections(self.gate_file, {"Measurements": "- load 4 s: pass"})
        self.ok("gate", "T-01")

    def test_reopen_rework_then_gate_needs_new_review(self):
        self.ok("gate", "T-01")
        r = self.ok("set-status", "T-01", "in-progress")
        self.assertIn("new review is needed", r.stdout)
        handoff = self.st / "handoffs" / "T-01.md"
        handoff.write_text(handoff.read_text().replace("Built the page.", "Reworked the page."))
        self.ok("set-status", "T-01", "review")
        r = self.run_cli("gate", "T-01")
        self.assertEqual(r.returncode, 1)
        self.assertIn("gate report .atelier/gates/T-01.md exists", r.stdout)
        self.assertEqual(self.status_of("T-01"), "review")


class TestReopenAndDependencies(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_in_progress_archives_gate_report(self):
        self.make_ready_task()
        r = self.ok("set-status", "T-01", "in-progress")
        archived = list((self.st / "gates" / "archive").glob("T-01-*.md"))
        self.assertEqual(len(archived), 1)
        self.assertRegex(archived[0].name, r"^T-01-\d{8}-\d{6}\.md$")
        self.assertIn("result: pass", archived[0].read_text())
        self.assertFalse((self.st / "gates" / "T-01.md").exists())
        self.assertIn("gates/archive/T-01-", r.stdout)

    def test_todo_archives_but_review_and_blocked_keep_report(self):
        self.make_ready_task()
        self.ok("set-status", "T-01", "review")
        self.ok("set-status", "T-01", "blocked")
        self.assertTrue((self.st / "gates" / "T-01.md").is_file())
        self.ok("set-status", "T-01", "todo")
        self.assertFalse((self.st / "gates" / "T-01.md").exists())
        self.assertEqual(len(list((self.st / "gates" / "archive").glob("T-01-*.md"))), 1)

    def test_in_progress_refused_while_dependency_open(self):
        self.ok("new-task", "T-01", "Base")
        self.ok("new-task", "T-02", "Uses base")
        set_meta(self.st / "tasks" / "T-02.md", "depends_on", "[T-01, T-09]")
        r = self.run_cli("set-status", "T-02", "in-progress")
        self.assertEqual(r.returncode, 1)
        self.assertIn("T-01 (todo)", r.stdout)
        self.assertIn("T-09 (missing)", r.stdout)
        self.assertEqual(self.status_of("T-02"), "todo")

    def test_in_progress_force_overrides_with_warning(self):
        self.ok("new-task", "T-01", "Base")
        self.ok("new-task", "T-02", "Uses base")
        set_meta(self.st / "tasks" / "T-02.md", "depends_on", "[T-01]")
        r = self.ok("set-status", "T-02", "in-progress", "--force")
        self.assertIn("Warning", r.stdout)
        self.assertIn("T-01 (todo)", r.stdout)
        self.assertEqual(self.status_of("T-02"), "in-progress")

    def test_in_progress_allowed_when_dependencies_done(self):
        self.make_ready_task()
        self.ok("gate", "T-01")
        self.ok("new-task", "T-02", "Uses base")
        set_meta(self.st / "tasks" / "T-02.md", "depends_on", "[T-01]")
        r = self.ok("set-status", "T-02", "in-progress")
        self.assertNotIn("Warning", r.stdout)
        self.assertEqual(self.status_of("T-02"), "in-progress")


class TestBoardDrift(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()
        self.ok("new-task", "T-01", "Base")
        self.ok("new-task", "T-02", "Other")
        board = self.st / "board.md"
        board.write_text(board.read_text().replace(
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| T-01 | Base | | A | | w | r | in-progress |\n"
            "| `T-02` | Other | | A | | w | r | todo |\n"))

    def test_board_status_differs_from_card(self):
        r = self.run_cli("status", "--strict")
        self.assertEqual(r.returncode, 1)
        self.assertIn("T-01: board.md says 'in-progress' but the card says 'todo'", r.stdout)
        self.assertNotIn("T-02: board.md", r.stdout)

    def test_board_in_step_with_cards_and_missing_rows_ignored(self):
        self.ok("set-status", "T-01", "in-progress")
        self.ok("new-task", "T-03", "Not on the board")
        self.ok("set-status", "T-03", "blocked")
        r = self.ok("status", "--strict")
        self.assertIn("Problems: none", r.stdout)


class TestSetStatus(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()
        self.ok("new-task", "T-01", "x")

    def test_set_status_valid(self):
        r = self.ok("set-status", "T-01", "in-progress")
        self.assertEqual(self.status_of("T-01"), "in-progress")
        self.assertIn("in-progress", r.stdout)

    def test_set_status_invalid_value(self):
        r = self.run_cli("set-status", "T-01", "finished")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_set_status_done_refused_without_gate(self):
        r = self.run_cli("set-status", "T-01", "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Refused", r.stdout)
        self.assertEqual(self.status_of("T-01"), "todo")

    def test_set_status_done_allowed_after_gate_criteria(self):
        (self.st / "tasks" / "T-01.md").unlink()
        self.make_ready_task()
        self.ok("set-status", "T-01", "done")
        self.assertEqual(self.status_of("T-01"), "done")


class TestRunChecks(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_run_checks_all_kinds_pass(self):
        self.add_check("a.py", "import os, sys\nsys.exit(0 if os.path.isdir('.atelier') else 1)\n")
        self.add_check("b.sh", "test -d .atelier\n")
        self.add_check("c", "#!/bin/sh\nexit 0\n", executable=True)
        self.add_check("README.md", "not a check")
        self.add_check("notes.md", "not a check")
        r = self.ok("run-checks")
        self.assertEqual(r.stdout.count("PASS check"), 3)
        self.assertNotIn("check README.md", r.stdout)
        self.assertNotIn("check notes.md", r.stdout)

    def test_run_checks_notes_skipped_md_files(self):
        self.add_check("README.md", "how checks work")
        self.add_check("old_check.md", "exit 1")
        self.add_check("ok.sh", "exit 0\n")
        r = self.ok("run-checks")
        self.assertIn("NOTE skipped checks/README.md", r.stdout)
        self.assertIn("NOTE skipped checks/old_check.md", r.stdout)
        self.assertIn("PASS check ok.sh", r.stdout)

    def test_run_checks_failure(self):
        self.add_check("ok.sh", "exit 0\n")
        self.add_check("bad.sh", "echo broken; exit 4\n")
        r = self.run_cli("run-checks")
        self.assertEqual(r.returncode, 1)
        self.assertIn("PASS check ok.sh", r.stdout)
        self.assertIn("FAIL check bad.sh (exit 4)", r.stdout)

    def test_run_checks_non_executable_unknown_file_fails(self):
        self.add_check("data.txt", "x")
        r = self.run_cli("run-checks")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL check data.txt", r.stdout)

    def test_run_checks_none(self):
        r = self.ok("run-checks")
        self.assertIn("No checks", r.stdout)


class TestLesson(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_lesson_first_time_logs_row(self):
        r = self.ok("lesson", "missing-alt", "image without alt | text")
        text = (self.st / "lessons.md").read_text()
        self.assertRegex(text, r"\| \d{4}-\d{2}-\d{2} \| missing-alt \| image without alt \\\| text \|")
        self.assertIn("seen 1 time", r.stdout)

    def test_lesson_second_time_exits_3(self):
        self.ok("lesson", "missing-alt", "one")
        r = self.run_cli("lesson", "missing-alt", "two")
        self.assertEqual(r.returncode, 3)
        self.assertIn(".atelier/checks/", r.stdout)
        self.assertIn("lesson: missing-alt", r.stdout)

    def test_lesson_second_time_ok_when_check_carries_tag(self):
        self.add_check("alt.py", "# guard\n# lesson: missing-alt\nimport sys\nsys.exit(0)\n")
        self.ok("lesson", "missing-alt", "one")
        self.ok("lesson", "missing-alt", "two")

    def test_lesson_tag_beyond_line_5_does_not_count(self):
        self.add_check("alt.py", "#\n#\n#\n#\n#\n# lesson: missing-alt\n")
        self.ok("lesson", "missing-alt", "one")
        self.assertEqual(self.run_cli("lesson", "missing-alt", "two").returncode, 3)

    def test_lesson_bad_tag(self):
        self.assertEqual(self.run_cli("lesson", "bad tag!", "x").returncode, 1)


class TestReject(AtelierTestCase):
    def test_reject_writes_both_logs(self):
        self.init()
        self.ok("reject", "too much blue | and pink", "--project", "demo")
        pattern = r"\| \d{4}-\d{2}-\d{2} \d{2}:\d{2} \| demo \| too much blue \\\| and pink \|"
        self.assertRegex((self.st / "rejections.md").read_text(), pattern)
        self.assertRegex((self.home / "rejections.md").read_text(), pattern)

    def test_reject_default_project_is_folder_name(self):
        self.init()
        self.ok("reject", "no serif")
        self.assertIn("| proj | no serif |", (self.home / "rejections.md").read_text())

    def test_reject_empty_text_fails(self):
        self.init()
        r = self.run_cli("reject", "  ")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("proj", (self.home / "rejections.md").read_text())


class TestShelve(AtelierTestCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_shelve_existing_path(self):
        (self.root / "logo.svg").write_text("<svg/>")
        self.ok("shelve", "logo-v1", "logo.svg", "Approved logo")
        self.assertRegex((self.st / "shelf.md").read_text(), r"\| logo-v1 \| logo.svg \| Approved logo \| \d{4}-")

    def test_shelve_missing_path_fails(self):
        r = self.run_cli("shelve", "logo-v1", "nope.svg", "x")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("logo-v1", (self.st / "shelf.md").read_text())


class TestStatus(AtelierTestCase):
    def test_status_without_atelier(self):
        r = self.ok("status")
        self.assertIn("No .atelier", r.stdout)
        self.assertEqual(self.run_cli("status", "--strict").returncode, 1)

    def test_status_table_and_clean_strict(self):
        self.init()
        self.make_ready_task()
        self.ok("gate", "T-01")
        r = self.ok("status", "--strict")
        self.assertRegex(r.stdout, r"T-01\s+Login page\s+done\s+yes\s+pass")
        self.assertIn("Problems: none", r.stdout)

    def test_status_reports_problems(self):
        self.init()
        self.ok("new-task", "T-01", "Base")
        self.ok("new-task", "T-02", "Uses base")
        self.ok("new-task", "T-03", "Fake done")
        self.ok("new-task", "T-04", "Review")
        set_meta(self.st / "tasks" / "T-02.md", "depends_on", "[T-01]")
        set_meta(self.st / "tasks" / "T-02.md", "status", "in-progress")
        set_meta(self.st / "tasks" / "T-03.md", "status", "done")
        set_meta(self.st / "tasks" / "T-04.md", "status", "review")
        self.run_cli("lesson", "dup", "a")
        self.run_cli("lesson", "dup", "b")
        r = self.run_cli("status", "--strict")
        self.assertEqual(r.returncode, 1)
        self.assertIn("T-02: in progress while dependency T-01 is todo", r.stdout)
        self.assertIn("T-03: marked done but its gate does not pass", r.stdout)
        self.assertIn("T-04: in review without a handoff note", r.stdout)
        self.assertIn("lesson 'dup'", r.stdout)
        self.assertEqual(self.run_cli("status").returncode, 0)


class TestHooks(AtelierTestCase):
    def test_session_start_silent_without_atelier(self):
        r = self.hook("session-start", raw="")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_session_start_shows_state(self):
        self.init()
        self.ok("new-task", "T-01", "Base")
        set_meta(self.st / "tasks" / "T-01.md", "status", "done")
        self.ok("reject", "no gradients")
        r = self.hook("session-start", raw="not json")
        self.assertEqual(r.returncode, 0)
        self.assertIn("atelier", r.stdout.splitlines()[0])
        self.assertIn("T-01", r.stdout)
        self.assertIn("Problems:", r.stdout)
        self.assertIn("no gradients", r.stdout)
        self.assertLessEqual(len(r.stdout.splitlines()), 60)

    def test_session_start_caps_output_at_60_lines(self):
        self.init()
        for i in range(40):
            self.ok("new-task", "T-%02d" % i, "t")
            set_meta(self.st / "tasks" / ("T-%02d.md" % i), "status", "review")
        for i in range(12):
            self.ok("reject", "thing %d" % i)
        r = self.hook("session-start")
        self.assertEqual(r.returncode, 0)
        self.assertLessEqual(len(r.stdout.splitlines()), 60)
        self.assertIn("thing 11", r.stdout)
        self.assertNotIn("thing 1\n", r.stdout)

    def test_stop_allows_clean_and_in_progress(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        r = self.hook("stop", {})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_stop_blocks_fake_done(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        set_meta(self.st / "tasks" / "T-01.md", "status", "done")
        r = self.hook("stop", {"stop_hook_active": False})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("T-01", out["reason"])

    def test_stop_blocks_repeated_lesson(self):
        self.init()
        self.run_cli("lesson", "dup", "a")
        self.run_cli("lesson", "dup", "b")
        out = json.loads(self.hook("stop", {}).stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("lesson: dup", out["reason"])

    def test_stop_respects_stop_hook_active_and_missing_state(self):
        r = self.hook("stop", {})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.init()
        self.ok("new-task", "T-01", "x")
        set_meta(self.st / "tasks" / "T-01.md", "status", "done")
        r = self.hook("stop", {"stop_hook_active": True})
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_subagent_stop_blocks_without_handoff(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        r = self.hook("subagent-stop", {"last_assistant_message": "Finished T-01, all good.",
                                        "stop_hook_active": False})
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("new-handoff T-01", out["reason"])
        self.assertIn("not finished", out["reason"])

    def test_subagent_stop_allows_with_handoff_or_other_status(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("new-task", "T-02", "y")
        self.ok("set-status", "T-01", "review")
        self.ok("new-handoff", "T-01", "--author", "w")
        fill_sections(self.st / "handoffs" / "T-01.md", HANDOFF_BODY)
        r = self.hook("subagent-stop", {"last_assistant_message": "Done with T-01 and looked at T-02."})
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_subagent_stop_ignores_unmentioned_and_active(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        r = self.hook("subagent-stop", {"last_assistant_message": "Worked on T-010 and T-01x."})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        r = self.hook("subagent-stop", {"last_assistant_message": "T-01", "stop_hook_active": True})
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_stop_hook_active_must_be_true_boolean(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        set_meta(self.st / "tasks" / "T-01.md", "status", "done")
        for value in ("false", "true", 1):
            out = json.loads(self.hook("stop", {"stop_hook_active": value}).stdout)
            self.assertEqual(out["decision"], "block", value)

    def test_subagent_stop_string_active_still_checks(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        r = self.hook("subagent-stop", {"last_assistant_message": "T-01 done", "stop_hook_active": "false"})
        self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_subagent_stop_falls_back_to_transcript(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        transcript = self.tmp / "agent.jsonl"
        transcript.write_text("x" * 9000 + '\n{"role": "user", "content": "Do task T-01"}\n')
        r = self.hook("subagent-stop", {"last_assistant_message": "Done.",
                                        "agent_transcript_path": str(transcript)})
        out = json.loads(r.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("new-handoff T-01", out["reason"])
        r = self.hook("subagent-stop", {"last_assistant_message": "Done.", "transcript_path": str(transcript)})
        self.assertEqual(json.loads(r.stdout)["decision"], "block")

    def test_subagent_stop_transcript_only_tail_counts(self):
        self.init()
        self.ok("new-task", "T-01", "x")
        self.ok("set-status", "T-01", "in-progress")
        transcript = self.tmp / "agent.jsonl"
        transcript.write_text("T-01 mentioned long ago\n" + "x" * 9000 + "\n")
        r = self.hook("subagent-stop", {"last_assistant_message": "Done.", "transcript_path": str(transcript)})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        r = self.hook("subagent-stop", {"last_assistant_message": "Done.",
                                        "transcript_path": str(self.tmp / "missing.jsonl")})
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    @unittest.skipIf(sys.platform.startswith("win"), "select on pipes is not supported on Windows")
    def test_hook_does_not_hang_on_open_stdin(self):
        self.init()
        cmd = [sys.executable, str(SCRIPT), "--root", str(self.root), "hook", "session-start"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=self.env, text=True)
        try:
            proc.wait(timeout=15)
            out = proc.stdout.read()
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("hook hung on a stdin pipe that was never closed")
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("atelier", out)

    def test_hooks_never_crash_on_bad_input(self):
        self.init()
        (self.st / "tasks" / "T-01.md").write_bytes(b"\xff\xfe broken")
        for event in ("session-start", "stop", "subagent-stop"):
            r = self.hook(event, raw="[1, 2")
            self.assertEqual(r.returncode, 0, event)
            self.assertNotIn("Traceback", r.stderr)
        r = self.run_cli("hook", "unknown-event")
        self.assertEqual(r.returncode, 0)


class TestScriptHygiene(unittest.TestCase):
    def test_compiles_and_is_executable(self):
        compile(SCRIPT.read_text(), str(SCRIPT), "exec")
        self.assertTrue(os.access(str(SCRIPT), os.X_OK))
        self.assertTrue(SCRIPT.read_text().startswith("#!/usr/bin/env python3"))
        self.assertLess(len(SCRIPT.read_text().splitlines()), 900)


if __name__ == "__main__":
    unittest.main()
