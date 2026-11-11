---
name: board
description: Maps the whole video job before any work starts, splitting it into segments and pieces sized for one worker, with dependencies, parallel groups, shared bottleneck queues, owners, and reviewers, and writes .atelier/board.md. Use after interrogate and before contract, and whenever the scope changes enough to add or remove a piece.
---

# Board: map the whole job first

No piece of work starts until the whole job is on the board. A map drawn after half the work is done only explains why the pieces do not fit. You are the lead; only you write `.atelier/board.md`.

## Step 1: list everything the job produces

1. Read the restatement the person approved in the `interrogate` phase.
2. Write down every output the job must produce: the cleaned transcript, each segment or clip, title and end cards, generated clips, captions, the audio mix, the draft and the final render.
3. Add the hidden work: the brand lock, transcript cleanup, assembly of the segments, the audio mix, the final render, the final check. Hidden work is where boards usually fail.

## Step 2: cut it into pieces

Each piece becomes one task card and goes to one worker. Size pieces with these rules:

1. **One worker, one session.** A piece must be finishable by one worker in one sitting, roughly 1 to 3 hours of focused work. If it needs more, split it.
2. **One owner per file.** Two pieces never write the same file. If two pieces must change one file, either merge them or put that file in a queue.
3. **Gate-sized.** A reviewer must be able to check the piece against its quality bar in under 30 minutes. If the check would take longer, the piece is too big.
4. **A clear exit.** Every piece produces something you can point at: a cleaned transcript, a 480p segment, a caption file, a rendered draft.
5. **Not too small.** A piece shorter than about 15 minutes costs more in briefing and gating than it saves. Merge it into a neighbour.

For video, split anything longer than 30 seconds into segments of 10 to 20 seconds (chapters of 1 to 3 minutes for a screen-recording edit, one clip each for a set of vertical clips); one worker owns one segment. A typical job has 3 to 12 pieces. More than 15 means you are planning shots, not pieces.

## Step 3: dependencies and parallel groups

1. For each piece, write which pieces must be `done` before it can start (`depends_on`).
2. Group pieces with no dependency between them into **parallel groups**: A, B, C, in order.
3. Check for cycles. If T-03 waits for T-05 and T-05 waits for T-03, the cut is wrong; redraw it.
4. Cap a parallel group at 4 workers by default (the `dispatch` skill says when you may raise it). More agents is not faster: each extra worker adds briefing, merging, and gating for you.

## Step 4: shared bottlenecks and queues

A bottleneck is anything only one worker may touch at a time: a full render, a paid or rate-limited generation, the audio mix of the whole video, the master timeline or project file, the brand lock.

1. List every bottleneck under "Shared bottlenecks".
2. Give each one a **queue** name (for example `render`, `generate`, `mix`, `brand-lock`).
3. Put that name in the `queue` field of every piece that uses it.
4. Work in one queue runs one at a time, in board order, even when the pieces are in the same parallel group.

## Step 5: owners and reviewers

1. Name an owner (worker) and a reviewer for every piece, with distinct names such as `worker-1` and `reviewer-1`. These go into the card's `owner:` and `reviewer:` fields; the worker and reviewer sign their files with them.
2. The reviewer must never be the owner. Workers run as `atelier-video:worker` subagents and reviewers as separate `atelier-video:reviewer` subagents.
3. One reviewer may check several pieces; one worker may own several pieces in different groups.

## Step 6: write the file

Write `.atelier/board.md` using its template sections: Pieces, Shared bottlenecks, Order of work. Add the listen-only table from `profile-video` after Pieces: for each segment, whether it passes by audio alone and, if not, exactly what must be on screen and when. Keep the Status column in step with the task cards; the card is the source of truth. Run `python3 .atelier/bin/atelier.py status` to see integrity problems; it lists any row whose Status differs from its card (board drift).

Then move to the `contract` skill, which turns each row into a task card.

## Worked example

Request: "Turn my 14-minute screen recording into a 6-minute tutorial with chapters."

```markdown
## Pieces

| Task | Title | Depends on | Parallel group | Bottleneck queue | Owner | Reviewer | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-01 | Clean transcript and cut list | - | A | - | worker-1 | reviewer-1 | todo |
| T-02 | Title card and chapter cards | - | A | - | worker-2 | reviewer-1 | todo |
| T-03 | Chapter 1 edit, 0:00-2:00 | T-01 | B | - | worker-1 | reviewer-2 | todo |
| T-04 | Chapter 2 edit, 2:00-4:00 | T-01 | B | - | worker-2 | reviewer-2 | todo |
| T-05 | Chapter 3 edit, 4:00-6:00 | T-01 | B | - | worker-3 | reviewer-1 | todo |
| T-06 | Assemble and mix, 480p draft | T-02, T-03, T-04, T-05 | C | render | worker-1 | reviewer-2 | todo |
| T-07 | Final render, 1080p | T-06 | D | render | worker-1 | reviewer-1 | todo |

## Listen-only test
| Task | Passes by audio alone? | Must be on screen |
| --- | --- | --- |
| T-03 | no | zoom on the settings menu while "open settings" is said, 0:42-0:50 |
| T-04 | yes | none |
| T-05 | no | the exact command typed, as a callout, 4:20-4:31 |

## Shared bottlenecks
- render: full renders share one machine; T-06 and T-07 run one after the other.
- mix: the audio mix of the whole tutorial happens once, inside T-06.
- brand-lock: only the lead edits assets/brand-lock.md; every card reads it.

## Order of work
- Group A (T-01, T-02) runs in parallel: 2 workers.
- Group B (T-03, T-04, T-05) starts when T-01 is done: 3 workers.
- Group C (T-06) starts when T-02 to T-05 are done; group D after the person approves the draft.
```

## Anti-patterns

- **Too many agents.** Ten workers on a five-segment video means ten briefs, ten gates, and ten looks to reconcile. Match workers to the widest parallel group, 4 at most by default (see `dispatch` for when to raise it).
- **Two workers on one file.** Two segments written into the same timeline overwrite each other. One file, one owner.
- **A board of shots.** "Zoom on logo, cut to screenshot, fade" is a recipe, not a board. Pieces are outcomes: a segment, a transcript, a render.
- **Forgetting assembly.** Six perfect segments with no piece to join and mix them is not a finished video.
- **A bottleneck with no queue.** Two renders started at once on one machine finish slower than two in a row.
- **Drawing the board after work starts.** Stop the work, draw the board, then resume.
