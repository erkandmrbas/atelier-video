---
name: gate
description: Runs an independent review of finished work: an atelier-video:reviewer subagent, never the author, measures every quality-bar line of the task card (sync, duration, colours, loudness, what must be on screen), writes a gate report, and only a pass lets the task move on. Use when a task card reaches review, before marking anything done, or whenever a worker claims a piece is finished.
---

# Gate

One agent works. A different agent checks. Work that fails a gate goes back, never forward.

## When to run a gate

- A card is in `review` and its handoff note passes `python3 .atelier/bin/atelier.py check-handoff T-01`.
- Before any output is shown to the person as finished.
- Before work leaves one station for the next (segment to assembly, 480p draft to final render).

## Rules

1. The reviewer must not be the author. Not the same subagent, not the lead if the lead made it. It must be the reviewer named on the card; `gate` fails for anyone else.
2. Measure, do not eyeball. Every quality-bar line gets a measured value: a duration read from the file, a frame offset, a count of visual changes, a sampled colour, a loudness reading, a command output.
3. Never accept "in sync" or "on brand" from a handoff note. Read the frame times against the transcript timestamps and sample the frames yourself, and record the result.
4. Check only against the card. The reviewer does not invent new requirements; it may note them as findings for the lead.
5. One failed line fails the gate. There is no "mostly pass".

## Steps

### 1. Pick the reviewer

1. Run the gate with the `atelier-video:reviewer` subagent. It starts with no memory of the work.
2. The reviewer's name is the card's `reviewer` field, written by the lead at dispatch (workers never edit cards). The reviewer signs the gate report with that name.

### 2. Brief the reviewer

Give the `atelier-video:reviewer` subagent only:

1. The task card path: `.atelier/tasks/T-01.md`.
2. The handoff note path: `.atelier/handoffs/T-01.md`.
3. This instruction: "Measure every quality-bar line yourself. Write the gate report with `python3 .atelier/bin/atelier.py new-gate T-01 --reviewer <reviewer from the card>`. Set result to pass only if every line passes."

### 3. Measure

The reviewer:

1. Reads the card's Quality bar section and makes one line per bar item.
2. Runs the steps in the handoff note's "How to verify", then takes its own measurements too: frame times, durations, sampled colours, loudness. The worker's numbers are claims, not results.
3. Runs `python3 .atelier/bin/atelier.py run-checks` to see every automated check from past lessons.
4. Records each value and pass or fail in the Measurements section.
5. Lists what must change in Findings. On a pass, writes "none".
6. Sets `result: pass` or `result: fail` in the front matter.

### 4. Close the gate

The lead runs:

```
python3 .atelier/bin/atelier.py gate T-01
```

This command passes only when the card is complete (all 7 sections and a number in the bar), the handoff note is complete, the gate report is by the reviewer named on the card (never the owner or the author) with `result: pass`, the report is not stale, every check in `.atelier/checks/` passes, and no lesson tag repeats without a check. On success it marks the task `done`.

### Stale reports

`new-gate` writes `card_hash` and `handoff_hash` into the report: hashes of the card's Quality bar section and of the handoff note. If either file changes after the review, `gate` and `set-status done` fail with "the card's quality bar changed after this review" or "the handoff note changed after this review". A report missing either hash fails too. The reviewer then re-measures and starts a new report:

```
python3 .atelier/bin/atelier.py new-gate T-01 --reviewer reviewer-1 --force
```

`--force` moves the old report to `.atelier/gates/archive/`. Without it, `new-gate` refuses to overwrite an existing report. Never edit the hashes by hand.

### 5. On a fail

1. Keep the card out of `done`. Run `python3 .atelier/bin/atelier.py set-status T-01 in-progress`. This moves the failed gate report to `.atelier/gates/archive/` (so does `todo`); the worker reads it there.
2. Send the same worker (or a fresh one, if the first is gone) the card path, the archived gate report path that `set-status` printed, and: "Fix every finding, then update your handoff note."
3. Do not pass the work forward to the next station "to save time". A segment that failed its gate never goes into assembly; a draft that failed never goes to the final render.
4. If the same kind of finding shows up again on another task, log it with `python3 .atelier/bin/atelier.py lesson TAG "..."` (see the `lessons` skill).
5. After the fix, the lead runs `check-handoff`, then `set-status T-01 review`, and the card's reviewer (a fresh `atelier-video:reviewer` subagent) writes a new report with `new-gate` and measures everything again. A reviewer different from the author is still required; the same reviewer may check again.

Stop after 3 failed rounds on one card. The card is probably wrong or too large. The lead rewrites or splits it.

## Watch for gamed results

A worker under pressure may make the numbers pass without making the work good. Look for:

- a segment trimmed to hit its duration by cutting into the voice;
- a tolerance loosened (a colour match raised from 3 to 30 per channel, sync from 1 frame to 5);
- a quality bar reinterpreted (for example "drift at most 1 frame" measured only on the first caption, or colours sampled from frames picked to pass);
- checks in `.atelier/checks/` that were changed or removed;
- a clip on the shelf copied in where the card asked for new material, or a new clip generated where the card said to reuse one;
- a handoff note that reports numbers no command or measurement produced.

Compare file changes against the card's constraints. If the brand lock, the transcript or a check changed, the gate fails unless the card asked for it. Only the lead may change a quality bar, and only with the person's approval. A bar changed after the review makes the gate report stale, so the reviewer measures again against the new bar.

## Sample gate report

```
---
task: T-04
reviewer: reviewer-2
result: fail
card_hash: 4b1f0c9a7e21
handoff_hash: 9d03e6b5a118
---

# Gate: T-04

## Measurements
- Duration 15.0 s within 0.5 s: measured 15.04 s from the file. PASS
- Caption sync within 1 frame: 6 captions; caption 3 starts 3 frames after its word timestamp. FAIL
- 12 to 15 visual changes: counted 14; longest still 2.6 s. PASS
- "Track, Invoice, Get paid" on screen 0:33-0:41: present 0:33.2-0:41.0, 84 px. PASS
- Brand colours within 3 per channel: 5 frames sampled; frame at 0:38 holds #3A7BFF, not in the brand lock. FAIL
- run-checks: 2 checks, 2 passed. PASS

## Findings
- Re-time caption 3 from its word timestamp, not the sentence start.
- The generated clip at 0:36-0:40 uses an off-brand blue; regenerate or grade it to #2F6FED.
```

## Checklist

- [ ] Reviewer is not the author and is the one named on the card.
- [ ] The report was made with `new-gate` after the last change to the bar and the handoff note.
- [ ] Every quality-bar line has a measured value.
- [ ] Sync, duration and colours were measured by the reviewer, not taken from the handoff note.
- [ ] `run-checks` was run.
- [ ] No check, tolerance or bar was weakened.
- [ ] `gate T-01` was run by the lead; on a fail the work went back, not forward.
