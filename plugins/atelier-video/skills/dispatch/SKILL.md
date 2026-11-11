---
name: dispatch
description: Hands ready task cards (segments, transcript, assembly, renders) to parallel atelier-video:worker subagents with minimal briefs, limits how many run at once, sends shared bottlenecks through one queue, and tracks status in files. Use when the board and task cards exist and the lead is ready to start work, or when resuming a job after a crash or a limit hit.
---

# Dispatch

The lead hands out task cards. `atelier-video:worker` subagents do the work: one segment, one transcript cleanup, one assembly. Files hold the state, so nothing depends on what anyone remembers from chat.

## Before you dispatch

1. Run `python3 .atelier/bin/atelier.py status` and read the board summary.
2. List the cards with status `todo`.
3. Keep only cards whose `depends_on` tasks are all `done`. A dependency in `review` is not done. `set-status T-03 in-progress` refuses a card with an unfinished dependency and names each one with its status. `--force` overrides this with a warning; use it only when the card says how it works without the dependency (for example against a placeholder transcript), and note why on the board.
4. Run `python3 .atelier/bin/atelier.py check-card T-01` on each candidate. A card that fails does not go out; fix the card first (only the lead edits cards).
5. Group the ready cards by their `queue` field. Cards with an empty queue are free to run in parallel.

## Write the brief

Keep the brief short. The card already holds the goal, constraints, quality bar and what is left open. Repeating it in the brief adds noise and lowers quality.

The whole brief is three things:

1. The task card path, for example `.atelier/tasks/T-03.md`.
2. The contract path: `.atelier/contract.md`.
3. This instruction: "When done, write your handoff note with `python3 .atelier/bin/atelier.py new-handoff T-03 --author <owner from the card>` and fill every section. Do not edit the card or run `set-status`. Mention T-03 in your final message."

Do not add your own opinions on how to solve it. If something matters, it belongs on the card.

The task id in the worker's final message matters: the SubagentStop hook reads it and refuses to let the worker stop while that task's handoff note is incomplete.

## Start the work

1. For each card you send, write `owner:` and `reviewer:` on the card (for example `worker-1`, `reviewer-1`; never the same name), then run `python3 .atelier/bin/atelier.py set-status T-03 in-progress`. Workers never run `set-status` and never edit the card.
2. Dispatch each card to its own `atelier-video:worker` subagent with the brief, all in the same turn so they run in parallel.
3. Record the owner on the board so the next session knows who holds what.

## Limit parallel workers

Default maximum: 4 workers at once. This is the one place that says when it may go higher.

Raise it, up to 8 at most, only when all of these hold:

- the pieces share no file and no queue;
- each piece can be checked on its own;
- your plan and rate limits allow the extra load.

More agents is not faster. Each extra worker:

- adds review load on the lead and on the reviewers, who become the real bottleneck;
- raises the chance that two workers collide on the same timeline or asset file;
- burns the same rate limit, so all workers slow down or stop together;
- makes a crash or limit hit cost more work to resume.

## Bottleneck queues

A queue is a lane for a resource only one worker may touch at a time. Typical queues:

- `render`: full renders share one machine
- `generate`: paid image or clip generation, with a budget per task
- `mix`: the audio mix of the whole video, done once
- `brand-lock`: the reference file only the lead edits
- a shared file (the master timeline or project file, a caption style file)

Rules:

1. Each card that touches a bottleneck names it in its `queue` field.
2. Only one card per queue is `in-progress` at a time. The next one waits as `todo`.
3. Cards in different queues may run in parallel with each other.
4. When the card in a queue reaches `done`, dispatch the next card in that queue.

Example: T-04 and T-06 both have `queue: generate`. Dispatch T-04. T-06 waits, even if a worker slot is free; a card with no queue takes the slot instead.

## Track status

Statuses: `todo`, `in-progress`, `review`, `done`, `blocked`.

1. On dispatch: `python3 .atelier/bin/atelier.py set-status T-03 in-progress`. The lead moves every card; workers never do.
2. When a worker reports back, check the handoff file (see below), then `python3 .atelier/bin/atelier.py set-status T-03 review` and hand it to the `gate` skill.
3. If a worker is stuck on something only the person or another task can answer: `python3 .atelier/bin/atelier.py set-status T-03 blocked`, and write the reason on the board.
4. To reopen a card (after a failed gate, or when the person asks for a change), run `set-status T-03 in-progress` (or `todo`). The CLI moves its gate report to `.atelier/gates/archive/` and prints the path, so the reworked output gets a new review.
5. Never set `done` by hand. Only `python3 .atelier/bin/atelier.py gate T-03` marks a task done; `set-status` refuses `done` unless the gate passed.
6. After every `set-status`, update the Status column of that row in `.atelier/board.md`. The card is the source of truth; `status` lists a board row that disagrees with its card as a problem.
7. Run `python3 .atelier/bin/atelier.py status --strict` before telling the person where things stand. Fix every integrity problem it lists.

## Never trust "done" in chat

A worker saying "finished" is not evidence. The file is.

1. Run `python3 .atelier/bin/atelier.py check-handoff T-03`.
2. If it fails (no file, no author, an empty section), the task is not finished. Send the worker back to complete the handoff note.
3. Read "Against the quality bar" and "Not done or open issues". A non-empty open issue list means you decide: send it back, or open a new card.
4. Only then move the card to `review`.

## Resume after a crash or a limit hit

Files are the memory. A new session can pick up the job with no chat history.

1. Run `python3 .atelier/bin/atelier.py status`.
2. For every card in `in-progress`:
   - handoff note exists and `check-handoff` passes: move it to `review`;
   - handoff note missing or incomplete: the work is unfinished. Look at the files the card names, then re-dispatch the card to a new `atelier-video:worker` subagent with the same brief. Tell it what partial output already exists (a half-cut segment, a render that stopped).
3. For every card in `review`: run the `gate` skill.
4. Re-check queues: at most 1 `in-progress` card per queue. A render that stopped mid-way restarts from the card, not from the partial file.
5. Continue dispatching from "Before you dispatch".

If you hit a usage limit mid-job, stop dispatching, let running workers finish, and write down on the board which cards were in flight. Do not start new cards until the limit resets.

## Checklist

- [ ] Every dispatched card passed `check-card`.
- [ ] Every dispatched card has all `depends_on` tasks `done`.
- [ ] No more than 4 workers at once, or up to 8 only when the three conditions above hold and you wrote down why.
- [ ] At most 1 `in-progress` card per queue.
- [ ] Every "finished" claim confirmed with `check-handoff`.
- [ ] `status --strict` exits 0 before you report progress.
