---
name: start
description: Starts an atelier-video job and makes the main session the lead. Sets up .atelier/, always loads profile-video, reads past rejections, then walks the phases in order (interrogate, board, contract, approval, dispatch, gate, deliver). Use at the start of any video job that needs more than one piece of work, more than one session, or a measurable result (an explainer, a motion video from a voice recording, a screen-recording edit, a set of vertical clips); also use to resume a job after a crash.
---

# Start an atelier-video job

You are now the **lead**. You run this video job like a workshop: you talk to the person, you write the plan into files, you hand segments to `atelier-video:worker` subagents, and nothing reaches the person without passing a gate run by an `atelier-video:reviewer` subagent, never by its author.

## When not to use the full method

Skip the method entirely when the job is trimming a clip, fixing one caption, swapping one still, or a question that can be answered in one reply. Running seven phases for a 2-minute change wastes the person's time. Do the change directly.

Use the **small job fast path** (below) when the job fits all of these:

- 1 worker can finish it in one session.
- It produces at most 1 output (for example one 20-second vertical clip).
- No shared bottleneck (a shared render machine, a paid generation budget, a master timeline) is involved.

Use the full method for everything bigger.

## Standing rules for the lead

1. **The person talks only to you.** Workers and reviewers never ask the person anything; they ask you, and you decide or ask.
2. **Only you write the state files**: `.atelier/contract.md`, `.atelier/board.md`, every task card in `.atelier/tasks/`, and the brand lock. Workers write handoff notes; reviewers write gate reports.
3. **Read rejections first.** Before you propose anything, read `.atelier/rejections.md` and `~/.atelier/rejections.md`. Never propose again something the person already rejected.
4. **Log every rejection the moment it happens**: `python3 .atelier/bin/atelier.py reject "what the person rejected"`.
5. **Never trust a transcript or a report blindly.** A raw transcript gets names, numbers and prices wrong; a handoff note or a subagent's summary is a claim, not proof. The gate measures; the person has the final word.
6. **Files are the memory.** After a crash or in a new session, run `python3 .atelier/bin/atelier.py status` and continue from what the files say, not from what you remember.
7. **The hooks back you up.** SessionStart shows the board and recent rejections, Stop refuses to end the session while a task is marked done without a passing gate, and SubagentStop refuses to let a worker stop without a complete handoff note. Run `python3 .atelier/bin/atelier.py status --strict` before you say anything is finished.

## Step 0: set up

1. Find the CLI. Use `${CLAUDE_PLUGIN_ROOT}/scripts/atelier.py` if that path exists; otherwise use `../../scripts/atelier.py` relative to this `SKILL.md`. If neither is found, run:
   `find ~/.claude -path "*atelier-video*/scripts/atelier.py" | head -1`
2. Run it once from the project root: `python3 <resolved path to atelier.py> init`.
3. From now on, always call the project copy: `python3 .atelier/bin/atelier.py <command>`.
4. If `.atelier/` already exists, do not re-run init. Run `python3 .atelier/bin/atelier.py status` and resume (see "Resume after a crash").
5. Read `.atelier/rejections.md`, `~/.atelier/rejections.md`, `.atelier/lessons.md`, and `.atelier/shelf.md`.
6. Load the `profile-video` skill. It is always part of an atelier-video job: transcript first, the listen-only test, the brand lock, video quality bars and queues.

## The phases, in order

Do not skip or reorder phases. Each phase ends with a file on disk.

1. **Interrogate.** Use the `interrogate` skill with the `profile-video` defaults. Turn every recording into a transcript with word timestamps first, then research, then ask question rounds, each question with your recommended answer. End with a restatement of 5 lines or fewer and a yes from the person.
2. **Board.** Use the `board` skill. Map the whole video into segments (10 to 20 seconds by default; see `profile-video` for other formats) plus the hidden pieces (clean transcript, brand lock, assembly and mix, final render), with dependencies, parallel groups, queues and the listen-only test. Write `.atelier/board.md`.
3. **Contract and task cards.** Use the `contract` skill, with the `profile-video` constraints and bar defaults. Write `.atelier/contract.md` and the brand lock, then one task card per piece with `python3 .atelier/bin/atelier.py new-task T-01 "title"`. Fill all 7 card sections; write "none" in Fixed decisions or Left open on purpose when there is nothing. Every card must pass `python3 .atelier/bin/atelier.py check-card T-01`.
4. **Approval checkpoint.** Show the person the board and the contract in a short summary (at most 15 lines). Stop. No worker starts until the person says yes. If they reject a part, log it with `reject` and revise.
5. **Dispatch.** Use the `dispatch` skill. Dispatch each ready card to an `atelier-video:worker` subagent with a minimal brief. Respect the queues: one render, one paid generation, one mix at a time. Follow `draft-first`: segments and the assembled cut at 480p, the person's yes, then the full-resolution final.
6. **Gate.** Use the `gate` skill. Run the gate with the `atelier-video:reviewer` subagent named on the card; it measures the output against the quality bar and writes the gate report. Then run `python3 .atelier/bin/atelier.py gate T-01`. Failed work goes back to the worker; it never reaches assembly.
7. **Deliver.** When every card is done, run `python3 .atelier/bin/atelier.py status --strict`. It must exit 0. Show the person the final, each measurement against the contract's quality bar, and what it cost (renders, generated clips). Ask for the final yes. Shelve approved outputs with `python3 .atelier/bin/atelier.py shelve TAG PATH "what it is"`.

At any phase, when a mistake happens, use the `lessons` skill. The second time the same tag appears, the fix becomes a check in `.atelier/checks/`, not a note.

## Subagents

- Every worker is an `atelier-video:worker` subagent with one card. Start the ready ones in the same turn so they run in parallel.
- Every gate is run by an `atelier-video:reviewer` subagent that did not touch the work.
- Research before questions goes to an `atelier-video:researcher` subagent.

Keep parallel workers to what the board allows: 4 at most by default (the `dispatch` skill says when you may raise it). More workers rarely make a video faster; they mostly create re-cut work for you and fight over the render queue.

## Small job fast path

For a job that fits the three limits above:

1. Run `init` and load `profile-video` (Step 0).
2. Get the transcript if there is audio. Interrogate in 1 round of 3 to 5 questions, each with your recommended answer.
3. Write a board with a single row. Write a short contract and one card with `python3 .atelier/bin/atelier.py new-task T-01 "title"`. Set `owner: lead` and `reviewer: reviewer-1` on the card, fill all 7 sections ("none" where there is nothing), and run `python3 .atelier/bin/atelier.py check-card T-01`.
4. Get one yes from the person on the contract.
5. Make a low-res draft, get a yes, make the final, write the handoff note with `python3 .atelier/bin/atelier.py new-handoff T-01 --author lead`, and fill it.
6. Run the gate with the `atelier-video:reviewer` subagent, which signs as `reviewer-1`: `python3 .atelier/bin/atelier.py new-gate T-01 --reviewer reviewer-1`, fills it, then you run `python3 .atelier/bin/atelier.py gate T-01`.
7. Deliver.

The fast path removes paperwork, never the gate.

## Resume after a crash

1. Run `python3 .atelier/bin/atelier.py status`.
2. Read the contract, the board, and every card whose status is `in-progress`, `review`, or `blocked`.
3. A card in `in-progress` with no handoff note is not finished. Restart it from the card and the files it names, not from a remembered conversation.
4. A card in `review` needs a gate report. Run the gate with its `atelier-video:reviewer` subagent.
5. Check the queues: at most one render, one generation and one mix in progress.
6. Tell the person in at most 5 lines where the job stands and what happens next.

## Done means

- `status --strict` exits 0.
- Every card is `done` through `gate`, never set by hand.
- The person said yes to the final render.
