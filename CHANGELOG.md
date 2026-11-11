# Changelog

All notable changes to atelier-video are listed here. Versions follow semantic versioning.

## 0.1.0 (2026-11-11)

Initial release: a Claude Code plugin for producing videos (explainers, motion videos from a voice recording, screen-recording edits, short vertical clips) like a workshop.

### Method
- The 11 principles in video terms: transcript and research first, then questions with recommended answers; map every segment before work; one lead; four-part task cards with an approval checkpoint; minimal briefs; shared state in files; independent gates at every exit; repeated mistakes become checks; low-res draft before the full-resolution final; limited parallelism with render, generation and mix queues; dated rejections with the person's word as final.

### Skills (`/atelier-video:<name>`)
- `start`: makes the main session the lead, sets up `.atelier/`, always loads `profile-video`, walks the phases in order (interrogate, board, contract, approval, dispatch, gate, deliver), small job fast path, resume from files after a crash.
- `interrogate`: research first (transcript, rejections, shelf, assets, risks) through the `atelier-video:researcher` subagent, then rounds of at most 7 numbered questions (3 to 5 for a small job), each with a recommended answer; ends with a restatement of 5 lines or fewer.
- `board`: maps the whole video into segments and hidden pieces (transcript, assembly, mix, final render), dependencies, parallel groups (capped at 4 workers), queues, owners and reviewers.
- `contract`: turns the request into `.atelier/contract.md` and one task card per piece, with vague words ("punchy", "in sync", "on brand") turned into numbers.
- `dispatch`: three-line briefs to `atelier-video:worker` subagents, at most 4 at once by default, one `in-progress` card per queue, status tracked in files.
- `gate`: an `atelier-video:reviewer` subagent measures every quality-bar line (frame times, durations, sampled colours, loudness); failed work goes back, never forward; stop after 3 failed rounds.
- `draft-first`: shelf first, a draft at about 10% of the final's cost (480p cut, stills, test clip), approval in the person's words, revise in place, shelve approved outputs.
- `lessons`: stable lesson tags, a check on the second occurrence, rejections logged in the person's words.
- `profile-video`: formats, transcript first, listen-only test per segment, brand lock, constraints, quality bar defaults, queues (`render`, `generate`, `mix`, `brand-lock`), cost control, a sample segment card and common lesson tags; names no tool.

### Subagents
- `atelier-video:worker`: carries out one task card and writes the handoff note.
- `atelier-video:reviewer`: measures one task against its card and writes the gate report.
- `atelier-video:researcher`: gathers facts for the lead; writes no files.

### CLI (`scripts/atelier.py`, Python 3.9+ standard library only)
- Commands: `init`, `new-task`, `new-handoff`, `new-gate`, `set-status`, `check-card`, `check-handoff`, `gate`, `run-checks`, `status`, `lesson`, `reject`, `shelve`, `hook`.
- `set-status` refuses `done` unless the gate passes; only `gate` marks a task done.
- `set-status T-01 in-progress` refuses while any `depends_on` task is not done and names each one; `--force` overrides it with a warning.
- Reopening a task (`set-status` to `in-progress` or `todo`) moves its gate report to `.atelier/gates/archive/`, so reworked output gets a new review.
- `check-card` requires all 7 card sections (Goal, Constraints, Quality bar, Examples and references, Approval checkpoint, Fixed decisions, Left open on purpose) and a number in the quality bar.
- `gate` requires a complete card, a complete handoff note, a passing gate report by a reviewer who is neither the author nor the owner and is the reviewer named on the card, a report that is not stale, passing checks, and no repeated lesson without a check.
- `new-gate` records `card_hash` and `handoff_hash` (hashes of the card's quality bar and of the handoff note); `gate` and `set-status done` fail when either changed after the review. `new-gate --force` archives the old report into `.atelier/gates/archive/` and starts a new one.
- `status` flags board drift: a row in `board.md` whose Status differs from the card.
- FAIL lines name the file to fix and, where it applies, who fixes it (lead, worker or reviewer).
- `lesson` exits with code 3 on the second occurrence of a tag that no check carries.
- `reject` writes a dated entry to `.atelier/rejections.md` and `~/.atelier/rejections.md`.
- `shelve` adds an approved output to `.atelier/shelf.md` and refuses a path that does not exist.
- Each project gets its own copy of the CLI and templates in `.atelier/bin/`.

### Hooks
- SessionStart: board summary, integrity problems and the 10 most recent rejections.
- Stop: blocks while a task is marked done without a passing gate, or a lesson repeats without a check.
- SubagentStop: blocks a worker that names a task without a complete handoff note.

### Templates
- Contract, board, task card, handoff note, gate report, lessons, rejections, shelf.

### Packaging and docs
- Claude Code marketplace (`.claude-plugin/marketplace.json`) and plugin manifest (`plugins/atelier-video/.claude-plugin/plugin.json`).
- Docs: the method, install, a worked example (a 90-second explainer from a voice recording), FAQ, contributing guide.
- CI: repository lint, unit tests and an end-to-end smoke test on Python 3.9 and 3.12.
