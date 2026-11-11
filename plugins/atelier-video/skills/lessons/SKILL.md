---
name: lessons
description: Runs the learning loop: logs every mistake under a stable tag, turns a tag that repeats into an automated check that blocks the gate, and records every rejection by the person in their own words. Use whenever something goes wrong, the person turns something down, before proposing anything new, and at periodic reviews.
---

# Lessons

A note is a hope. A check is a guarantee. The first time a mistake happens, write it down. The second time, write code that blocks it.

## Log every mistake

When something goes wrong (a failed gate, captions out of sync, an off-brand colour, a misheard number, a clip generated twice):

1. Pick a stable tag: short, lowercase, hyphenated, about the kind of mistake, not the instance. Good: `sync-drift`, `caption-too-long`, `off-brand-colour`. Bad: `bug-in-t04`, `oops`. `profile-video` lists the common video tags.
2. Before inventing a new tag, read `.atelier/lessons.md` and reuse an existing tag if it is the same kind of mistake. A new tag for an old mistake hides the repeat.
3. Log it:

```
python3 .atelier/bin/atelier.py lesson caption-too-long "T-04 caption at 0:37 has a 41-character line"
```

4. Write what went wrong in one sentence, with the task id.

The CLI's own warnings are mistakes too. When `status` reports that board.md disagrees with a card, fix the board row and log it under `board-drift`. When `gate` reports a stale report (the bar or the handoff note changed after the review), log it under `stale-review` if the change was not agreed first.

## Second time: write a check

`lesson` exits with code 3 when a tag appears for the second time and no check carries `lesson: TAG`. That exit code means: stop writing notes.

1. Create a script in `.atelier/checks/`, for example `.atelier/checks/caption_length.py`.
2. Put `lesson: TAG` in its first 5 lines, so the CLI can match it to the lesson.
3. Make it exit 0 when the project is clean and non-zero when the bad pattern is present.
4. Print the file and line of every hit, so the fix is obvious.
5. Use Python 3.9+ standard library only.
6. Run `python3 .atelier/bin/atelier.py run-checks` and confirm the check fails on the current mistake, then passes after the fix.

From now on `python3 .atelier/bin/atelier.py gate T-01` runs every check, so the mistake cannot pass a gate again.

### Example check

```python
#!/usr/bin/env python3
# lesson: caption-too-long
# Fails if any caption in captions/*.srt has more than 2 lines or a line over 32 characters.
import pathlib
import sys

MAX_LINES, MAX_CHARS = 2, 32
hits = []
for path in sorted(pathlib.Path("captions").glob("*.srt")):
    blocks = path.read_text(encoding="utf-8", errors="ignore").replace("\r", "").split("\n\n")
    for block in blocks:
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        cue, text = lines[0], lines[2:]
        if len(text) > MAX_LINES:
            hits.append(f"{path}: cue {cue}: {len(text)} lines")
        for line in text:
            if len(line) > MAX_CHARS:
                hits.append(f"{path}: cue {cue}: {len(line)} characters: {line[:60]}")
for hit in hits:
    print(hit)
sys.exit(1 if hits else 0)
```

Keep checks small and fast: one pattern per check, under 1 second on a normal project. A slow check gets skipped; a skipped check protects nothing.

## Log every rejection

When the person turns something down, log it the moment it happens, before you start fixing:

```
python3 .atelier/bin/atelier.py reject "end card v2 with the spinning logo: 'too flashy, just let it sit'"
```

1. Use the person's own words, in quotes. Do not paraphrase into something softer.
2. Name what was rejected: which file, version, timestamp, or direction.
3. One entry per rejection. The CLI adds the date and writes it to both `.atelier/rejections.md` and `~/.atelier/rejections.md`, so the lesson follows the person to the next project.

## Read before proposing

Before any proposal, draft, or set of directions:

1. Read `.atelier/rejections.md` and `~/.atelier/rejections.md`.
2. Read `.atelier/lessons.md`.
3. Make sure nothing you are about to show repeats a rejection. If it must (the person changed their mind), say so openly.
4. Start from the shelf. Every generated output gets a tag (in its file name or metadata) the moment it is made; only approved outputs go on the shelf with `shelve`. A rejected output keeps its tag, stays off the shelf, and gets a `reject` entry.

## The person has the final word

- Never trust a transcript blindly. Speech-to-text mishears names, numbers and prices, and summaries drop details and add things that were never said. Check them against the person's notes.
- Never trust an agent report blindly. A worker or reviewer can be wrong, can misread the card, or can report numbers no command produced. Check the files.
- If an agent report and the person disagree, the person wins. Log the disagreement as a lesson so the gap gets closed.
- Approval comes only from the person, never from a reviewer or the lead's own judgment.

## Periodic review

Every 5 finished tasks, or at the end of each approval checkpoint:

1. Run `python3 .atelier/bin/atelier.py status` and read `.atelier/lessons.md`.
2. Confirm every tag with 2 or more entries has a check. Write any that are missing.
3. Find lessons that apply to the whole job, not just one task. Promote them into the contract's Constraints section as "never ..." lines (only the lead edits the contract).
4. Look at rejections for a pattern (for example 3 rejections that all say "too busy", or two that reject bouncing text). Turn the pattern into a constraint or a quality-bar line, and ask the person to confirm it.
5. Remove checks that no longer apply only with the person's approval, and log why.

## Checklist

- [ ] Every mistake logged with a stable, reused tag.
- [ ] Every repeated tag has a check with `lesson: TAG` in its first 5 lines.
- [ ] `run-checks` passes.
- [ ] Every rejection logged at once, in the person's words.
- [ ] Rejections and lessons read before the last proposal.
- [ ] Recurring lessons promoted into the contract's constraints.
