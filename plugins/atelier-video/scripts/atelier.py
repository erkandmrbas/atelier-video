#!/usr/bin/env python3
"""atelier: shared state, checks and gates for a lead-and-workers workflow.

Standard library only (Python 3.9+). Every project keeps its state in
<root>/.atelier/ and its own copy of this script in .atelier/bin/atelier.py.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

STATUSES = ("todo", "in-progress", "review", "done", "blocked")
CARD_SECTIONS = ("Goal", "Constraints", "Quality bar", "Examples and references", "Approval checkpoint",
                 "Fixed decisions", "Left open on purpose")
HANDOFF_SECTIONS = ("What was done", "Files changed", "Against the quality bar",
                    "Not done or open issues", "How to verify")
STATE_FILES = ("contract.md", "board.md", "lessons.md", "rejections.md", "shelf.md")
STATE_DIRS = ("tasks", "handoffs", "gates", "checks")
CHECK_TIMEOUT = 300
CMD = "python3 .atelier/bin/atelier.py"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
LESSON_RE = re.compile(r"lesson:\s*([A-Za-z0-9_.\-]+)", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class AtelierError(Exception):
    """A user-facing error: printed as one line, exit code 1."""


# ---------------------------------------------------------------- paths

def script_dir():
    return Path(os.path.abspath(__file__)).parent


def templates_dir():
    up = script_dir().parent / "templates"
    if up.is_dir():
        return up
    return script_dir() / "templates"


def project_root(arg_root=None):
    for value in (arg_root, os.environ.get("ATELIER_ROOT"), os.environ.get("CLAUDE_PROJECT_DIR")):
        if value:
            return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def global_dir():
    value = os.environ.get("ATELIER_HOME")
    return Path(value).expanduser() if value else Path.home() / ".atelier"


class State:
    def __init__(self, root):
        self.root = Path(root)
        self.dir = self.root / ".atelier"

    def exists(self):
        return self.dir.is_dir()

    def require(self):
        if not self.exists():
            raise AtelierError("No .atelier/ in %s. Run the init command first." % self.root)

    def card(self, tid):
        return self.dir / "tasks" / ("%s.md" % tid)

    def handoff(self, tid):
        return self.dir / "handoffs" / ("%s.md" % tid)

    def gate(self, tid):
        return self.dir / "gates" / ("%s.md" % tid)

    def task_ids(self):
        tdir = self.dir / "tasks"
        return sorted(p.stem for p in tdir.glob("*.md") if p.is_file()) if tdir.is_dir() else []


def valid_id(tid):
    if not ID_RE.match(tid or ""):
        raise AtelierError("Invalid task id %r. Use letters, digits, '-', '_' or '.', e.g. T-01." % tid)
    return tid


# ---------------------------------------------------------------- parsing

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def split_front_matter(text):
    """Return (front matter dict, body). Values: str, or list for [a, b]."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:])
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            value = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()] if inner else []
        else:
            value = value.strip("'\"")
        meta[key.strip()] = value
    return {}, text


def set_front_matter(path, key, value):
    text = read_text(path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AtelierError("%s has no front matter." % path)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            lines.insert(i, "%s: %s" % (key, value))
            break
        if re.match(r"^%s\s*:" % re.escape(key), lines[i]):
            lines[i] = "%s: %s" % (key, value)
            break
    else:
        raise AtelierError("%s has an unclosed front matter block." % path)
    Path(path).write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


def sections(body):
    """Map '## Heading' -> content until the next level-1 or level-2 heading."""
    result, current = {}, None
    for line in body.splitlines():
        m = re.match(r"^(#{1,2})\s+(.*?)\s*$", line)
        if m:
            current = m.group(2) if len(m.group(1)) == 2 else None
            if current is not None:
                result.setdefault(current, "")
            continue
        if current is not None:
            result[current] += line + "\n"
    return result


EMPTY_LINE_RE = re.compile(r"^\s*(#+.*|[\W_]*)$")


def meaningful(content):
    """Section text without comments, headings, bare bullets or punctuation-only lines."""
    lines = COMMENT_RE.sub("", content or "").splitlines()
    return "\n".join(line for line in lines if not EMPTY_LINE_RE.match(line)).strip()


def norm(name):
    return (name or "").strip().lower()


def as_list(value):
    if isinstance(value, list):
        return value
    return [v.strip() for v in str(value or "").split(",") if v.strip()]


def table_rows(path, text=None, header=None):
    """Data rows of a markdown table (separator skipped). The header row goes into `header` if given."""
    rows, seen_header = [], False
    for line in (read_text(path) if text is None else text).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if all(re.match(r"^:?-{3,}:?$", c) for c in cells if c):
            continue
        if not seen_header:
            seen_header = True
            if header is not None:
                header.extend(norm(c) for c in cells)
            continue
        rows.append(cells)
    return rows


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def append_row(path, cells):
    """Append a table row; a missing log is first created from its template (same file name)."""
    text = read_text(path) if Path(path).exists() else read_text(templates_dir() / Path(path).name)
    if text and not text.endswith("\n"):
        text += "\n"
    text += "| " + " | ".join(cell(c) for c in cells) + " |\n"
    Path(path).write_text(text, encoding="utf-8")


def fill_template(name, tid, title=""):
    src = templates_dir() / name
    if not src.is_file():
        raise AtelierError("Template %s not found in %s." % (name, templates_dir()))
    return read_text(src).replace("{{id}}", tid).replace("{{title}}", title)


# ---------------------------------------------------------------- checks

def is_doc(p):
    return p.name.upper().startswith("README") or p.suffix.lower() == ".md"


def check_files(state, docs=False):
    """Runnable checks; with docs=True, the README*/*.md files that are skipped instead."""
    cdir = state.dir / "checks"
    if not cdir.is_dir():
        return []
    return [p for p in sorted(cdir.iterdir())
            if p.is_file() and not p.name.startswith(".") and is_doc(p) == docs]


def check_lessons(path):
    head = "\n".join(read_text(path).splitlines()[:5])
    return {norm(t) for t in LESSON_RE.findall(head)}


def carried_lessons(state):
    tags = set()
    for p in check_files(state):
        tags |= check_lessons(p)
    return tags


def lesson_counts(state):
    counts = {}
    for row in table_rows(state.dir / "lessons.md"):
        if len(row) >= 2 and row[1]:
            counts[norm(row[1])] = counts.get(norm(row[1]), 0) + 1
    return counts


def repeated_lessons(state):
    carried = carried_lessons(state)
    return sorted(t for t, n in lesson_counts(state).items() if n >= 2 and t not in carried)


def run_one_check(state, path):
    if path.suffix == ".py":
        cmd = [sys.executable or "python3", str(path)]
    elif path.suffix == ".sh":
        cmd = ["bash", str(path)]
    elif os.access(str(path), os.X_OK):
        cmd = [str(path)]
    else:
        return False, "not runnable (use .py, .sh, or make it executable)", ""
    try:
        proc = subprocess.run(cmd, cwd=str(state.root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=CHECK_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "timed out after %d s" % CHECK_TIMEOUT, ""
    except OSError as exc:
        return False, "could not run: %s" % exc, ""
    output = proc.stdout.decode("utf-8", "replace").strip()
    return proc.returncode == 0, "exit %d" % proc.returncode, output


def run_checks(state, verbose=True):
    results = [(None, "NOTE skipped checks/%s: README and .md files are not run as checks" % p.name)
               for p in check_files(state, docs=True)] if verbose else []
    for p in check_files(state):
        ok, why, output = run_one_check(state, p)
        results.append((ok, "check %s (%s)" % (p.name, why)))
        if verbose and not ok and output:
            tail = output.splitlines()[-5:]
            results.append((None, "\n".join("    " + line for line in tail)))
    return results


# ---------------------------------------------------------------- criteria

def card_meta(state, tid):
    return split_front_matter(read_text(state.card(tid)))[0] if ID_RE.match(tid) else {}


def short_hash(text):
    text = " ".join(COMMENT_RE.sub("", text or "").split())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def review_hashes(state, tid):
    """What a gate report is tied to: the card's Quality bar and the handoff note body."""
    bar = sections(split_front_matter(read_text(state.card(tid)))[1]).get("Quality bar", "")
    handoff = split_front_matter(read_text(state.handoff(tid)))[1]
    return {"card_hash": short_hash(bar), "handoff_hash": short_hash(handoff)}


def card_criteria(state, tid):
    path = state.card(tid)
    if not path.is_file():
        return [(False, "task card %s exists (create it: %s new-task %s \"title\")" % (rel(state, path), CMD, tid))]
    meta, body = split_front_matter(read_text(path))
    secs = sections(body)
    fix = "(lead: fix it in %s)" % rel(state, path)
    res = [(meta.get("id") == tid, "card front matter id is %s (found %r) %s" % (tid, meta.get("id", ""), fix))]
    for name in CARD_SECTIONS:
        res.append((bool(meaningful(secs.get(name))), "card section '%s' is filled %s" % (name, fix)))
    res.append((bool(re.search(r"\d", meaningful(secs.get("Quality bar")))),
                "card quality bar holds at least one number %s" % fix))
    return res


def handoff_criteria(state, tid):
    path = state.handoff(tid)
    if not path.is_file():
        return [(False, "handoff note %s exists (create it: %s new-handoff %s --author NAME)"
                 % (rel(state, path), CMD, tid))]
    meta, body = split_front_matter(read_text(path))
    secs = sections(body)
    where = rel(state, path)
    res = [(bool(str(meta.get("author", "")).strip()),
            "handoff author is set (worker: set `author:` in %s)" % where)]
    for name in HANDOFF_SECTIONS:
        res.append((bool(meaningful(secs.get(name))),
                    "handoff section '%s' is filled (worker: fill it in %s)" % (name, where)))
    return res


def report_criteria(state, tid):
    path = state.gate(tid)
    if not path.is_file():
        return [(False, "gate report %s exists (reviewer creates it: %s new-gate %s --reviewer NAME)"
                 % (rel(state, path), CMD, tid))]
    meta, body = split_front_matter(read_text(path))
    where = rel(state, path)
    fix = "(reviewer: fix it in %s)" % where
    other = "(a different agent must review and write the gate report %s)" % where
    reviewer = norm(meta.get("reviewer"))
    author = norm(split_front_matter(read_text(state.handoff(tid)))[0].get("author"))
    cmeta = card_meta(state, tid)
    owner, assigned = norm(cmeta.get("owner")), norm(cmeta.get("reviewer"))
    res = [(meta.get("task") == tid, "gate report task is %s %s" % (tid, fix)),
           (bool(reviewer), "gate reviewer is set (reviewer: set `reviewer:` in %s)" % where)]
    if reviewer:
        res.append((reviewer != author, "reviewer '%s' is not the handoff author %s" % (meta.get("reviewer"), other)))
        if owner:
            res.append((reviewer != owner, "reviewer '%s' is not the card owner %s" % (meta.get("reviewer"), other)))
        if assigned:
            res.append((reviewer == assigned, "reviewer '%s' is the one assigned on the card (%s); only that "
                        "reviewer writes %s" % (meta.get("reviewer"), cmeta.get("reviewer"), where)))
    redo = ("the reviewer must re-measure and create a new gate report: %s new-gate %s --reviewer NAME --force"
            % (CMD, tid))
    current = review_hashes(state, tid)
    for key, what in (("card_hash", "the card's quality bar"), ("handoff_hash", "the handoff note")):
        recorded = str(meta.get(key, "")).strip()
        if not recorded:
            res.append((False, "gate report records %s (%s missing); %s" % (key, what, redo)))
        elif recorded == current[key]:
            res.append((True, "%s is unchanged since this review" % what))
        else:
            res.append((False, "%s changed after this review; %s" % (what, redo)))
    res.append((norm(meta.get("result")) == "pass",
                "gate result is pass (found %r) %s" % (meta.get("result", ""), fix)))
    res.append((bool(meaningful(sections(body).get("Measurements"))),
                "gate section 'Measurements' is filled %s" % fix))
    return res


def lesson_criteria(state):
    rep = repeated_lessons(state)
    if not rep:
        return [(True, "no repeated lesson without a check")]
    return [(False, "lesson '%s' repeated without a check in .atelier/checks/" % t) for t in rep]


def gate_criteria(state, tid, with_checks=True):
    res = card_criteria(state, tid) + handoff_criteria(state, tid) + report_criteria(state, tid)
    if with_checks:
        res += run_checks(state)
        res += lesson_criteria(state)
    return res


def passed(results):
    return all(ok for ok, _ in results if ok is not None)


def print_results(results):
    for ok, msg in results:
        if ok is None:
            print(msg)
        else:
            if ok:
                # The "who fixes it" hint only matters on a failure.
                msg = re.sub(r" \((lead|worker|reviewer): [^)]*\)$", "", msg)
            print("%s %s" % ("PASS" if ok else "FAIL", msg))


def rel(state, path):
    try:
        return str(Path(path).relative_to(state.root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- status

def task_rows(state):
    rows = []
    for tid in state.task_ids():
        meta = card_meta(state, tid)
        has_handoff = state.handoff(tid).is_file()
        if not state.gate(tid).is_file():
            gate = "none"
        else:
            gate = "pass" if passed(report_criteria(state, tid)) else "fail"
        rows.append({"id": tid, "title": str(meta.get("title", "")), "status": str(meta.get("status", "")),
                     "depends_on": as_list(meta.get("depends_on")), "handoff": has_handoff, "gate": gate})
    return rows


def board_statuses(state):
    """Task -> Status from the Pieces table in board.md (empty when the board or the columns are missing)."""
    body = split_front_matter(read_text(state.dir / "board.md"))[1]
    header = []
    rows = table_rows(None, text=sections(body).get("Pieces", ""), header=header)
    if "task" not in header or "status" not in header:
        return {}
    ti, si = header.index("task"), header.index("status")
    return {r[ti].strip("` "): r[si].strip("` ") for r in rows if len(r) > max(ti, si) and r[ti].strip("` ")}


def find_problems(state, rows=None):
    rows = task_rows(state) if rows is None else rows
    by_id = {r["id"]: r for r in rows}
    problems = []
    for r in rows:
        if r["status"] not in STATUSES:
            problems.append("%s: unknown status %r (use one of: %s)" % (r["id"], r["status"], ", ".join(STATUSES)))
        if r["status"] == "done" and not passed(gate_criteria(state, r["id"], with_checks=False)):
            problems.append("%s: marked done but its gate does not pass (run: %s gate %s)" % (r["id"], CMD, r["id"]))
        if r["status"] == "review" and not r["handoff"]:
            problems.append("%s: in review without a handoff note" % r["id"])
        if r["status"] == "in-progress":
            for dep in r["depends_on"]:
                dep_status = by_id.get(dep, {}).get("status")
                if dep_status != "done":
                    problems.append("%s: in progress while dependency %s is %s"
                                    % (r["id"], dep, dep_status or "missing"))
    for tid, board_status in board_statuses(state).items():
        card_status = by_id.get(tid, {}).get("status")
        if card_status is not None and norm(board_status) != norm(card_status):
            problems.append("%s: board.md says %r but the card says %r (lead: update the row in .atelier/board.md)"
                            % (tid, board_status, card_status))
    for tag in repeated_lessons(state):
        problems.append("lesson '%s' happened twice and no check carries it (add a check in .atelier/checks/ "
                        "with 'lesson: %s' in its first 5 lines)" % (tag, tag))
    return problems


def format_table(rows, limit=None):
    if not rows:
        return ["No tasks yet."]
    head = ("id", "title", "status", "handoff", "gate")
    data = [(r["id"], r["title"][:40], r["status"], "yes" if r["handoff"] else "no", r["gate"]) for r in rows]
    shown = data if limit is None else data[:limit]
    widths = [max(len(head[i]), *(len(d[i]) for d in shown)) for i in range(5)]
    fmt = "  ".join("%%-%ds" % w for w in widths)
    lines = [fmt % head, fmt % tuple("-" * w for w in widths)] + [fmt % d for d in shown]
    if len(data) > len(shown):
        lines.append("... and %d more tasks" % (len(data) - len(shown)))
    return lines


# ---------------------------------------------------------------- commands

def cmd_init(state, args):
    created = []
    for d in STATE_DIRS + ("bin/templates",):
        (state.dir / d).mkdir(parents=True, exist_ok=True)
    bindir = state.dir / "bin"
    me = Path(os.path.abspath(__file__))
    target = bindir / "atelier.py"
    if me.resolve() != target.resolve():
        shutil.copyfile(str(me), str(target))
    os.chmod(str(target), 0o755)
    src_t = templates_dir()
    if src_t.resolve() != (bindir / "templates").resolve():
        for t in sorted(src_t.glob("*.md")):
            shutil.copyfile(str(t), str(bindir / "templates" / t.name))
    for name in STATE_FILES:
        path = state.dir / name
        if args.force or not path.exists():
            path.write_text(read_text(src_t / name), encoding="utf-8")
            created.append(name)
    global_dir().mkdir(parents=True, exist_ok=True)
    if not (global_dir() / "rejections.md").exists():
        (global_dir() / "rejections.md").write_text(read_text(src_t / "rejections.md"), encoding="utf-8")
    print("atelier ready in %s" % state.dir)
    print("Created: %s" % (", ".join(created) if created else "nothing new (existing files kept)"))
    print("Next: the lead fills contract.md and board.md, then: %s new-task T-01 \"title\"" % CMD)
    return 0


def cmd_new_task(state, args):
    state.require()
    tid = valid_id(args.id)
    path = state.card(tid)
    if path.exists():
        raise AtelierError("%s already exists." % rel(state, path))
    path.write_text(fill_template("task.md", tid, args.title), encoding="utf-8")
    print("Created %s. The lead fills Goal, Constraints, Quality bar (with numbers), Examples and references, "
          "Approval checkpoint, Fixed decisions, Left open on purpose (\"none\" counts as filled)." % rel(state, path))
    return 0


def _new_from(state, tid, template, path, key, value, label):
    state.require()
    valid_id(tid)
    if not state.card(tid).is_file():
        raise AtelierError("No task card for %s. The lead creates it first: %s new-task %s \"title\""
                           % (tid, CMD, tid))
    if path.exists():
        raise AtelierError("%s already exists." % rel(state, path))
    path.write_text(fill_template(template, tid), encoding="utf-8")
    if value:
        set_front_matter(path, key, value)
    print("Created %s. Fill every section, then: %s" % (rel(state, path), label))
    return 0


def cmd_new_handoff(state, args):
    return _new_from(state, args.id, "handoff.md", state.handoff(args.id), "author", args.author,
                     "%s check-handoff %s" % (CMD, args.id))


def archive_gate(state, tid):
    """Move an existing gate report to gates/archive/<id>-<stamp>.md and return the new path."""
    adir = state.dir / "gates" / "archive"
    adir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    target, n = adir / ("%s-%s.md" % (tid, stamp)), 1
    while target.exists():
        n += 1
        target = adir / ("%s-%s-%d.md" % (tid, stamp, n))
    shutil.move(str(state.gate(tid)), str(target))
    return target


def cmd_new_gate(state, args):
    state.require()
    tid = valid_id(args.id)
    if args.force and state.card(tid).is_file() and state.gate(tid).is_file():
        print("Archived the old gate report to %s." % rel(state, archive_gate(state, tid)))
    code = _new_from(state, tid, "gate.md", state.gate(tid), "reviewer", args.reviewer, "%s gate %s" % (CMD, tid))
    for key, value in review_hashes(state, tid).items():
        set_front_matter(state.gate(tid), key, value)
    if not state.handoff(tid).is_file():
        print("Warning: %s has no handoff note yet; this report will not pass. Review after the worker hands off."
              % tid)
    return code


def cmd_set_status(state, args):
    state.require()
    tid = valid_id(args.id)
    if args.status not in STATUSES:
        raise AtelierError("Invalid status %r. Use one of: %s." % (args.status, ", ".join(STATUSES)))
    if not state.card(tid).is_file():
        raise AtelierError("No task card %s." % rel(state, state.card(tid)))
    if args.status == "in-progress":
        deps = as_list(card_meta(state, tid).get("depends_on"))
        open_deps = ["%s (%s)" % (d, card_meta(state, d).get("status") or "missing")
                     for d in deps if not ID_RE.match(d) or card_meta(state, d).get("status") != "done"]
        if open_deps and not args.force:
            print("Refused: %s depends on tasks that are not done: %s. Finish them first, or pass --force."
                  % (tid, ", ".join(open_deps)))
            return 1
        if open_deps:
            print("Warning: forced; %s starts before its dependencies are done: %s." % (tid, ", ".join(open_deps)))
    if args.status in ("in-progress", "todo") and state.gate(tid).is_file():
        print("Archived the gate report to %s. The work is reopened, so a new review is needed (new-gate)."
              % rel(state, archive_gate(state, tid)))
    if args.status == "done":
        results = gate_criteria(state, tid)
        if not passed(results):
            print("Refused: %s cannot be done until its gate passes." % tid)
            print_results([r for r in results if r[0] is not True])
            return 1
    set_front_matter(state.card(tid), "status", args.status)
    print("%s status: %s" % (tid, args.status))
    return 0


def _report(results, ok_msg, fail_msg):
    print_results(results)
    if passed(results):
        print(ok_msg)
        return 0
    print(fail_msg)
    return 1


def cmd_check_card(state, args):
    state.require()
    tid = valid_id(args.id)
    return _report(card_criteria(state, tid), "Card %s is complete." % tid,
                   "Card %s is incomplete. The lead fixes the FAIL lines." % tid)


def cmd_check_handoff(state, args):
    state.require()
    tid = valid_id(args.id)
    return _report(handoff_criteria(state, tid), "Handoff %s is complete." % tid,
                   "Handoff %s is incomplete. Without a complete handoff note the task is not finished." % tid)


def cmd_gate(state, args):
    state.require()
    tid = valid_id(args.id)
    results = gate_criteria(state, tid)
    print_results(results)
    if not passed(results):
        print("Gate %s: FAIL. The work does not move on until every line passes." % tid)
        return 1
    set_front_matter(state.card(tid), "status", "done")
    print("Gate %s: PASS. Status set to done." % tid)
    return 0


def cmd_run_checks(state, args):
    state.require()
    results = run_checks(state)
    if not results:
        print("No checks in .atelier/checks/.")
        return 0
    return _report(results, "All checks pass.", "Some checks fail.")


def cmd_status(state, args):
    if not state.exists():
        print("No .atelier/ in %s. This project does not use atelier yet (run init)." % state.root)
        return 1 if args.strict else 0
    rows = task_rows(state)
    print("\n".join(format_table(rows)))
    problems = find_problems(state, rows)
    print("")
    if problems:
        print("Problems:")
        for p in problems:
            print("- " + p)
    else:
        print("Problems: none")
    return 1 if (args.strict and problems) else 0


def cmd_lesson(state, args):
    state.require()
    tag = args.tag.strip()
    if not re.match(r"^[A-Za-z0-9_.\-]+$", tag):
        raise AtelierError("Invalid tag %r. Use letters, digits, '-', '_' or '.'." % args.tag)
    if not args.text.strip():
        raise AtelierError("Say what went wrong.")
    append_row(state.dir / "lessons.md", [datetime.date.today().isoformat(), tag, args.text])
    count = lesson_counts(state).get(norm(tag), 0)
    print("Lesson logged: %s (seen %d time%s)." % (tag, count, "" if count == 1 else "s"))
    if count >= 2 and norm(tag) not in carried_lessons(state):
        print("STOP: '%s' happened %d times. Turn it into code, not a note: write a check in .atelier/checks/ "
              "(.py, .sh, or executable) that exits non-zero when this mistake is present, with the line "
              "'lesson: %s' in its first 5 lines. Gates fail until it exists." % (tag, count, tag))
        return 3
    return 0


def cmd_reject(state, args):
    text = args.text.strip()
    if not text:
        raise AtelierError("Say what the person rejected.")
    project = args.project or state.root.name
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    global_dir().mkdir(parents=True, exist_ok=True)
    targets = [global_dir() / "rejections.md"]
    if state.exists():
        targets.insert(0, state.dir / "rejections.md")
    else:
        print("Note: no .atelier/ here, so only the global log was written.")
    for path in targets:
        append_row(path, [stamp, project, text])
    print("Rejection recorded (%s, %s) in: %s" % (stamp, project, ", ".join(str(p) for p in targets)))
    return 0


def cmd_shelve(state, args):
    state.require()
    if "://" not in args.path:
        p = Path(args.path).expanduser()
        if not (p if p.is_absolute() else state.root / p).exists():
            raise AtelierError("%s does not exist. Only real, approved outputs go on the shelf." % args.path)
    append_row(state.dir / "shelf.md", [args.tag, args.path, args.text, datetime.date.today().isoformat()])
    print("Shelved %s as '%s'." % (args.path, args.tag))
    return 0


# ---------------------------------------------------------------- hooks

STDIN_TIMEOUT = 2.0


def stdin_ready():
    """False when stdin has nothing to read within STDIN_TIMEOUT s; True when unknown (no select)."""
    try:
        import select
        return bool(select.select([sys.stdin], [], [], STDIN_TIMEOUT)[0])
    except (ImportError, OSError, ValueError, TypeError):
        return True


def read_stdin_json():
    try:
        if sys.stdin is None or sys.stdin.isatty() or not stdin_ready():
            return {}
        data = sys.stdin.read()
        value = json.loads(data) if data.strip() else {}
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def recent_rejections(state, n=10):
    seen, rows = set(), []
    for path in (state.dir / "rejections.md", global_dir() / "rejections.md"):
        for row in table_rows(path):
            key = tuple(row[:3])
            if len(row) >= 3 and key not in seen:
                seen.add(key)
                rows.append(row)
    rows.sort(key=lambda r: r[0])
    return rows[-n:]


def hook_session_start(state, data):
    if not state.exists():
        return 0
    lines = ["This project uses atelier: you are the lead; only the lead writes contract, board and task cards; "
             "every task needs a handoff note and a gate by a different agent before it is done (%s status)." % CMD]
    rows = task_rows(state)
    lines += [""] + format_table(rows, limit=25)
    problems = find_problems(state, rows)
    if problems:
        lines += ["", "Problems:"] + ["- " + p for p in problems[:10]]
        if len(problems) > 10:
            lines.append("- ... %d more (run status)" % (len(problems) - 10))
    rej = recent_rejections(state)
    if rej:
        lines += ["", "Recent rejections by the person (do not repeat these):"]
        lines += ["- %s [%s] %s" % (r[0], r[1], r[2]) for r in rej]
    print("\n".join(lines[:60]))
    return 0


def hook_stop(state, data):
    if not state.exists() or data.get("stop_hook_active") is True:
        return 0
    reasons = []
    for r in task_rows(state):
        if r["status"] == "done" and not passed(gate_criteria(state, r["id"], with_checks=False)):
            reasons.append("%s is marked done but its gate does not pass; run `%s gate %s` and fix every FAIL line, "
                           "or set it back to review." % (r["id"], CMD, r["id"]))
    for tag in repeated_lessons(state):
        reasons.append("lesson '%s' happened twice; write a check in .atelier/checks/ with 'lesson: %s' "
                       "in its first 5 lines." % (tag, tag))
    if reasons:
        return block("atelier: " + " ".join(reasons))
    return 0


TRANSCRIPT_TAIL = 4000


def mentioned_ids(ids, text):
    return [t for t in ids if re.search(r"(?<![A-Za-z0-9_\-])%s(?![A-Za-z0-9_\-])" % re.escape(t), text)]


def hook_subagent_stop(state, data):
    if not state.exists() or data.get("stop_hook_active") is True:
        return 0
    ids = state.task_ids()
    named = mentioned_ids(ids, str(data.get("last_assistant_message") or ""))
    if not named:
        transcript = data.get("agent_transcript_path") or data.get("transcript_path")
        if transcript:
            named = mentioned_ids(ids, read_text(Path(str(transcript)).expanduser())[-TRANSCRIPT_TAIL:])
    missing = []
    for tid in named:
        status = card_meta(state, tid).get("status")
        if status in ("in-progress", "review") and not passed(handoff_criteria(state, tid)):
            missing.append(tid)
    if not missing:
        return 0
    steps = " ".join("Run `%s new-handoff %s --author YOUR-NAME` (if the file is missing) and fill every section "
                     "of .atelier/handoffs/%s.md, then `%s check-handoff %s`." % (CMD, t, t, CMD, t) for t in missing)
    return block("atelier: a task without a complete handoff note is not finished (%s). %s"
                 % (", ".join(missing), steps))


HOOKS = {"session-start": hook_session_start, "stop": hook_stop, "subagent-stop": hook_subagent_stop}


def cmd_hook(state, args):
    try:
        return HOOKS[args.event](state, read_stdin_json())
    except Exception:
        return 0


# ---------------------------------------------------------------- main

def build_parser():
    root_opt = argparse.ArgumentParser(add_help=False)
    root_opt.add_argument("--root", default=argparse.SUPPRESS, help="project root (default: env or cwd)")
    p = argparse.ArgumentParser(prog="atelier.py", description="Shared state, checks and gates for atelier.")
    p.add_argument("--root", default=None, help="project root (default: ATELIER_ROOT, CLAUDE_PROJECT_DIR, cwd)")
    sub = p.add_subparsers(dest="command", metavar="command")
    sub.required = True

    def add(name, func, help_text, *positionals):
        sp = sub.add_parser(name, parents=[root_opt], help=help_text)
        sp.set_defaults(func=func)
        for arg in positionals:
            sp.add_argument(arg)
        return sp

    add("init", cmd_init, "create .atelier/ and copy the script and templates").add_argument(
        "--force", action="store_true", help="overwrite contract, board, lessons, rejections, shelf")
    add("new-task", cmd_new_task, "create a task card", "id", "title")
    add("new-handoff", cmd_new_handoff, "create a handoff note", "id").add_argument("--author", default="")
    sp = add("new-gate", cmd_new_gate, "create a gate report", "id")
    sp.add_argument("--reviewer", default="")
    sp.add_argument("--force", action="store_true", help="archive an existing gate report and start a new one")
    add("set-status", cmd_set_status, "change a task status", "id", "status").add_argument(
        "--force", action="store_true", help="start in-progress even if dependencies are not done")
    add("check-card", cmd_check_card, "check a task card", "id")
    add("check-handoff", cmd_check_handoff, "check a handoff note", "id")
    add("gate", cmd_gate, "run the full gate; marks the task done on success", "id")
    add("run-checks", cmd_run_checks, "run every check in .atelier/checks/")
    add("status", cmd_status, "board summary and problems").add_argument("--strict", action="store_true")
    add("lesson", cmd_lesson, "log a mistake", "tag", "text")
    add("reject", cmd_reject, "record what the person rejected", "text").add_argument("--project", default="")
    add("shelve", cmd_shelve, "add an approved output to the shelf", "tag", "path", "text")
    add("hook", cmd_hook, "entry point for Claude Code hooks").add_argument("event", choices=sorted(HOOKS))
    return p


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    is_hook = bool(argv) and "hook" in argv[:3]
    try:
        args = build_parser().parse_args(argv)
        state = State(project_root(getattr(args, "root", None)))
        return args.func(state, args)
    except AtelierError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    except SystemExit:
        if is_hook:
            return 0
        raise
    except Exception as exc:
        if is_hook:
            return 0
        print("Error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
