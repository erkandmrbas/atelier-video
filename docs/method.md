# The atelier-video method

This document explains the method behind atelier-video for the people who use it: what each rule is, why it works for video, what breaks without it, and exactly where the plugin enforces it. The skills tell Claude Code what to do. This page tells you why.

## Why the method exists

Two problems show up as soon as you hand an AI agent a video bigger than a single clip.

**Agents default to average work.** Given "make an explainer from my voice memo", an agent fills every gap with the most common choice: stock-looking stills, a generic font, captions wherever they fit, a music bed at whatever level. The result is plausible, tidy, and generic: the median of every explainer it has seen, not what you had in mind. The agent did not misunderstand you. It never had enough to understand. Nothing in the request said what "good" meant, so it aimed for "typical".

**More agents without structure break each other's work.** The obvious fix for a 90-second video is to give each segment to its own agent. Without a plan, they pick four different looks, time captions in four different ways, all start full renders on the same machine, and each report "done" on a segment that does not join the next one. You spend the time you saved re-cutting what they made. Four agents that step on each other finish later than one that works alone.

A workshop solves both problems with roles and files. One lead agent talks to you and owns the plan. The plan is written down in measurable terms before anyone starts: durations, frame offsets, hex colours, loudness. Workers get one segment each. A different agent measures every segment against numbers before it moves on. Mistakes that repeat turn into code that blocks them. The 11 principles below are the rules that make this work.

### The roles

| Role | Does | Writes |
| --- | --- | --- |
| lead | Talks to the person, plans, dispatches, closes gates | `.atelier/contract.md`, `.atelier/board.md`, `.atelier/tasks/T-NN.md` |
| worker | Carries out one task card, for example one segment | the work, and `.atelier/handoffs/T-NN.md` |
| reviewer | Measures one finished task against its card | `.atelier/gates/T-NN.md` |
| researcher | Gathers facts before the contract | nothing; it reports to the lead |

In Claude Code, the lead is your main session. Workers run as `atelier-video:worker` subagents, reviewers as `atelier-video:reviewer` subagents, and research as `atelier-video:researcher` subagents.

### The flow

```
interrogate -> board -> contract + task cards -> approval -> dispatch -> gate -> 480p draft -> approval -> final
                                                               ^          |
                                                               +-- fail --+
```

Each phase ends with a file on disk. The `start` skill walks the phases in this order and does not let the lead skip one.

## The 11 principles

### 1. Research first, then interrogate

**The rule.** Before any work starts, the lead researches what it can find on its own, then questions the person in short rounds. For video, research starts by turning every recording into a transcript with word timestamps, because agents cannot read audio reliably. Every question carries a recommended answer. The phase ends when the person confirms a restatement of 5 lines or fewer.

**Why it works.** Research removes the questions the person should never have to answer ("how long is the recording?", "what frame rate are the screen captures?"). Recommended answers turn a questionnaire into a review: the person can reply "go with your recommendations" and correct only what is wrong. Most people are far better at correcting a concrete proposal than at writing a brief from nothing.

**What goes wrong without it.** The agent guesses the aspect ratio, the audience and the length, builds on the guess, and you find out at the first render. Or it asks 15 open questions at once, you answer 4, and it guesses the other 11 anyway.

**How atelier-video enforces it.** The `profile-video` skill, always loaded by `start`, puts the transcript first. The `interrogate` skill: research first (rejections, shelf, the recording and assets, similar videos, the 3 to 5 biggest risks), through the `atelier-video:researcher` subagent; then rounds of at most 7 numbered questions (3 to 5 for a small job), one decision per question, each with a recommendation; then the restatement. The `start` skill does not move to the board until the person says yes.

### 2. Map the whole job first

**The rule.** Before any segment starts, the lead draws the board: every segment and every hidden piece (transcript, brand lock, assembly, mix, final render), their dependencies, which run in parallel, and which shared bottlenecks they touch.

**Why it works.** A map shows the problems that are invisible one segment at a time: two segments that both want the only generated clip budget, a piece nobody owns (usually assembly and the audio mix), a render everything waits on. The board also carries the listen-only test: for each segment, would a viewer understand it by audio alone? Where the answer is no, the board says exactly what must be on screen, and when. Fixing these on paper costs minutes. Fixing them after four segments are cut costs a re-edit.

**What goes wrong without it.** Work starts on the hook, the plan grows as it goes, and halfway through you learn that the price is never shown on screen and two segments both end on the logo. A map drawn after half the work only explains why the pieces do not fit.

**How atelier-video enforces it.** The `board` skill writes `.atelier/board.md` with three sections: Pieces (a table with depends on, parallel group, bottleneck queue, owner, reviewer, status), Shared bottlenecks, and Order of work; `profile-video` adds the listen-only table. Segments are 10 to 20 seconds each by default (chapters of 1 to 3 minutes for a screen-recording edit), one owner per file, checkable in under 30 minutes. A typical video has 3 to 12 pieces. `python3 .atelier/bin/atelier.py set-status T-03 in-progress` is refused while any task in the card's `depends_on` is not `done` (`--force` overrides it with a warning), and `status` flags any task in progress while a dependency is not `done`. `status` also flags a board row whose Status differs from the card's status, because the card is the source of truth.

### 3. One lead

**The rule.** The person talks only to the lead. The lead turns the short request into a measurable contract and hands segments to parallel workers. Workers and reviewers never ask the person anything; they ask the lead.

**Why it works.** One voice keeps one picture of the video. Every decision (the price is $40, the accent colour is `#2F6FED`, no stock people) passes through one place, so it is recorded once and applied in every segment. The person is not interrupted by six agents with six half-informed questions.

**What goes wrong without it.** Each agent builds its own idea of the look. Two of them ask you about the caption style and get different answers on different days. Nobody owns the whole video, so nobody notices the jump between segments.

**How atelier-video enforces it.** The `start` skill makes the main session the lead and states the standing rules. Only the lead writes the contract, the board, the task cards and the brand lock; the `atelier-video:worker` and `atelier-video:reviewer` subagents are told never to edit them. The contract (`.atelier/contract.md`) quotes the request word for word and then turns it into lines a reviewer can check without asking anyone.

### 4. Every task card has four parts and a checkpoint

**The rule.** Every task card carries a goal, constraints (what must never happen), a quality bar with numbers, and examples or references, plus an approval checkpoint ("none" is a valid answer).

**Why it works.** Each part closes one kind of gap. The goal says what exists at the end: "a 15-second segment that makes '3 hours saved per week' impossible to miss". Constraints say what must never happen, which is where most real damage comes from: a colour outside the brand lock, a number the speaker never said. The quality bar makes "good" checkable by someone other than the author. Examples (the brand lock, the transcript lines, an approved clip on the shelf) carry taste that words cannot. The checkpoint says where the work stops for the person.

**What goes wrong without it.** "Make the hook punchy" cannot fail a review, so it never does. A worker with no constraints puts a rounded number on screen because it looks cleaner. A reviewer with no bar falls back on "looks fine to me".

**How atelier-video enforces it.** `python3 .atelier/bin/atelier.py new-task T-01 "title"` creates the card from the template with these sections, plus Fixed decisions and Left open on purpose. `python3 .atelier/bin/atelier.py check-card T-01` fails if any of the 7 sections is empty (Goal, Constraints, Quality bar, Examples and references, Approval checkpoint, Fixed decisions, Left open on purpose; "none" counts as filled), or if the quality bar holds no number. The `contract` and `dispatch` skills require `check-card` to pass before a card goes out, and `gate` runs the same checks again.

### 5. Do not over-brief workers

**The rule.** A worker gets three things: the fixed decisions, the quality bar, and what is deliberately left open. Not a shot-by-shot recipe. Give numbers whenever you can.

**Why it works.** A shot list caps quality at the level of whoever wrote it, and the worker stops thinking. A number leaves the route open: "12 to 15 visual changes in 15 s, no still held longer than 3 s" lets the worker find the best cut; "zoom in on every sentence" does not, and may be wrong. Saying out loud what is left open (order of moves, which crops, how the chart builds) tells the worker where its judgment is wanted.

**What goes wrong without it.** Long briefs bury the goal. When a planned shot does not fit the voice, the worker follows the brief anyway or stalls. A brief full of adjectives ("clean", "modern", "dynamic") is read differently by every agent, and four segments come back in four styles.

**How atelier-video enforces it.** The `dispatch` skill limits the brief to three items: the card path, the contract path, and the instruction to write a handoff note. The `contract` skill shows how to turn vague words into numbers, and treats a card longer than about 60 lines as a recipe in disguise. The `profile-video` skill gives default numbers (sync, motion density, loudness, caption size, duration) so the lead does not start from a blank page.

### 6. Shared state lives in files

**The rule.** The contract, the board and the task cards are files, and only the lead writes them. A worker writes a handoff note when it finishes. No handoff note means the task is not finished.

**Why it works.** Files outlive sessions. After a crash, a usage limit or a new day, any session can run `status` and pick up from what the files say instead of from what someone remembers. A handoff note also turns "segment done" into something checkable: what changed, how it measured against the bar, what is still open, how to verify.

**What goes wrong without it.** State lives in chat history and dies with it. Two agents edit the plan and the last write wins. A worker says "finished" in chat, the lead believes it, and the missing caption is found by the person.

**How atelier-video enforces it.** Everything lives in `.atelier/`. `python3 .atelier/bin/atelier.py new-handoff T-01 --author NAME` creates the note; `python3 .atelier/bin/atelier.py check-handoff T-01` fails if it is missing, has no author, or has an empty section. The SubagentStop hook blocks a worker that names a task in its final message while that task's handoff note is incomplete. `status` lists any task in `review` without a handoff note.

### 7. Gates at every station exit

**The rule.** One agent does the work; a different agent checks it against the quality bar. Work that fails a gate does not move on: a segment that fails the sync gate never reaches assembly, and a draft that fails never goes to the final render.

**Why it works.** An author checking its own segment sees what it meant to cut, not what it cut. A separate reviewer with only the card and the output has nothing to defend. Measuring every line (frame times against word timestamps, sampled colours against hex codes, the file's real duration), instead of watching once and nodding, catches the gaps a confident handoff note hides.

**What goes wrong without it.** "In sync" turns out to mean "in sync with the sentence starts", 4 frames late on every caption. Failed work moves to assembly "to save time", the full mix is built on it, and one bad segment costs a re-render of the whole video.

**How atelier-video enforces it.** The `gate` skill and the `atelier-video:reviewer` subagent: the reviewer re-measures every quality-bar line itself, runs `run-checks`, and writes `.atelier/gates/T-01.md` with `result: pass` or `result: fail`. Then the lead runs `python3 .atelier/bin/atelier.py gate T-01`, which passes only if the card is complete, the handoff note is complete, the reviewer is neither the handoff author nor the card owner and is the reviewer named on the card, the report is not stale, the result is `pass`, every check passes, and no lesson repeats without a check. `new-gate` records a hash of the card's quality bar (`card_hash`) and of the handoff note (`handoff_hash`) in the report; if either changes after the review, the report is stale and the gate fails until the reviewer re-measures and runs `new-gate T-01 --reviewer NAME --force`, which moves the old report to `.atelier/gates/archive/`. Reopening a task (`set-status T-01 in-progress` or `todo`) archives its gate report the same way, so a re-cut segment always gets a new review. Only a passing gate sets `done`; `set-status T-01 done` is refused otherwise. The Stop hook blocks the session from ending while a task is marked `done` without a passing gate.

### 8. The same mistake twice becomes code

**The rule.** The first time a mistake happens, log it. The second time, write an automated check that blocks progress until the mistake is gone.

**Why it works.** A note depends on someone reading it at the right moment. A check runs every time, for every agent, and cannot be skipped. The cost of writing a small script (caption lines over 32 characters, an untagged file in `assets/`, a shelf row pointing at a missing file) is paid once; the mistake never costs you again.

**What goes wrong without it.** The lessons file grows, nobody reads it, and the third segment worker times its captions from sentence starts like the first two. Each fix is local; the cause stays.

**How atelier-video enforces it.** `python3 .atelier/bin/atelier.py lesson TAG "what went wrong"` adds a dated row to `.atelier/lessons.md`. On the second row with the same tag, it exits with code 3 and tells the lead to write a check unless one already exists. A check is any `.py`, `.sh` or executable file in `.atelier/checks/` with `lesson: TAG` in its first 5 lines; it exits 0 when the project is clean. `gate` runs every check and fails while a repeated tag has none, and `status` lists the missing check as a problem. The `lessons` skill has a worked example, and `profile-video` lists the common video tags (`sync-drift`, `off-brand-colour`, `loud-music`, `static-hold` and more).

### 9. Cheap draft first, expensive final after approval

**The rule.** Make a cheap draft, show it at an approval checkpoint, and spend on the final only after the person says yes. For video that means a 480p draft of the whole cut, with placeholders where a generated clip is still missing, before any full-resolution render. Tag every output when it is made, put approved ones on the shelf, and start new work from the shelf.

**Why it works.** A 480p draft costs a fraction of the final and catches a wrong direction while it is still cheap to change. The shelf turns approved work into a starting point: an approved clip, a cleaned transcript or a music bed is faster, cheaper and already approved, and it comes back the same every time.

**What goes wrong without it.** A 4K render runs for an hour in a direction the person rejects in the first 10 seconds. Approved clips are regenerated from scratch and come back slightly different each time, so the last shot no longer matches the first.

**How atelier-video enforces it.** The `draft-first` skill: spend about 10% of the final's cost on the draft, offer 2 to 3 directions when the look is unclear, revise in place, and get the person's yes in their own words. The contract template lists three approval checkpoints by default: plan, cheap draft, final. `python3 .atelier/bin/atelier.py shelve TAG PATH "what it is"` adds the approved output to `.atelier/shelf.md` and refuses a path that does not exist. The `interrogate` and `draft-first` skills read the shelf before anything new is made or generated.

### 10. Parallelism is limited

**The rule.** More agents is not faster. Run as many segment workers as the board's widest parallel group allows, capped at 4 by default. Shared bottlenecks go through one queue, one piece at a time: `render` (full renders share one machine), `generate` (paid image or clip generation, with a budget), `mix` (the full audio mix, done once), `brand-lock` (the reference file, lead only).

**Why it works.** Every extra worker adds a brief to write, a handoff to read, a gate to run, and a chance of collision. The lead and the reviewers become the bottleneck long before the workers do. Queues turn collisions into a short wait.

**What goes wrong without it.** Two renders on one machine finish slower than two in a row. Six workers each generate "just one" clip and the budget for four is gone. Two workers both write the master timeline and one segment disappears. A crash costs ten half-finished segments instead of four.

**How atelier-video enforces it.** The `board` skill caps a parallel group at 4 and puts every bottleneck in a named queue on the card's `queue` field. The `dispatch` skill keeps at most 1 `in-progress` card per queue and allows more than 4 workers only when the pieces share no file and no queue, each can be checked alone, and the limits allow it. `profile-video` names the usual queues.

### 11. Record every rejection; the person has the final word

**The rule.** Every time the person turns something down, log it with the date, in their words. Never trust a transcript or an agent's report blindly. The person, not a reviewer and not the lead, gives approval.

**Why it works.** A dated rejection log stops the most annoying failure of all: being shown the same rejected look again next week. Because the log also goes to your home folder, it follows you to the next video. Treating transcripts and reports as claims keeps the lead checking files instead of repeating summaries.

**What goes wrong without it.** The agent proposes the bouncing text you rejected on Monday, again on Thursday. A transcript turns "forty" into "fourteen" and the price on screen is wrong. A worker reports "in sync" with no frame times behind it, and the lead passes it on.

**How atelier-video enforces it.** `python3 .atelier/bin/atelier.py reject "what the person rejected"` writes a dated row to `.atelier/rejections.md` and `~/.atelier/rejections.md`. The `start`, `interrogate`, `draft-first` and `lessons` skills read both files before any proposal, and the contract turns relevant rejections into "never" lines. The SessionStart hook shows the 10 most recent rejections at the top of every session. `profile-video` tells the lead to check every name, number and price in the transcript against the person's notes, and the `gate` skill tells the reviewer to treat every number in a handoff note as a claim to re-measure.

## One task's life

The principles meet in the life of a single task card, for example one 15-second segment. Every card goes through the same stations, and each station leaves a file behind.

1. **Card.** The lead runs `python3 .atelier/bin/atelier.py new-task T-03 "title"`, fills the card from the board row, the listen-only test and the contract, and runs `check-card T-03` until it passes. Status: `todo`.
2. **Dispatch.** When every task in `depends_on` is `done` (usually the cleaned transcript) and its queue is free, the lead runs `set-status T-03 in-progress` (refused while a dependency is not `done`) and sends an `atelier-video:worker` subagent the three-line brief.
3. **Work.** The worker reads the card, the contract, the brand lock, the shelf, the lessons and the rejections, cuts the segment at draft resolution, and measures itself against every bar line as it goes.
4. **Handoff.** The worker runs `new-handoff T-03 --author NAME`, fills every section, and runs `check-handoff T-03`. The lead confirms `check-handoff` passes, then moves the card to `review`. Workers never run `set-status`.
5. **Gate.** The reviewer named on the card, never the worker, runs `new-gate T-03 --reviewer NAME`, reads frame times against the transcript, samples frames for colours, runs `run-checks`, and sets `result`. The lead runs `gate T-03`.
6. **Pass or back.** On a pass, the task is `done` and the next card in its queue can start. On a fail, the lead runs `set-status T-03 in-progress`, which moves the gate report to `.atelier/gates/archive/`, sends the worker that report, and logs a lesson. After 3 failed rounds the lead rewrites or splits the card.
7. **Shelf.** If the output is something the person approved, the lead shelves it so the next task starts from it.

Nothing in this cycle depends on memory. A new session, after a crash or the next morning, runs `status` and sees exactly which station every card has reached.

## What the plugin enforces, and what it cannot

The CLI and hooks enforce the parts of the method that can be checked mechanically: a complete card, a complete handoff note, a reviewer who is neither the owner nor the author and is the reviewer named on the card, a gate report that is not stale (the quality bar and the handoff note are unchanged since the review), a passing result, passing checks, no repeated lesson without a check, no task set in progress before its dependencies are done (unless the lead forces it, with a warning), and a board that agrees with the cards (`status` flags drift). They cannot read a frame, hear a mix, or judge whether a quality bar is the right one, whether a reviewer measured honestly, or whether the person really approved. Those stay with the reviewer's own measurements, the lead and the person. The skills tell them how to do it well; the files make it visible when it was skipped.

## The files at a glance

| File | Written by | Holds |
| --- | --- | --- |
| `.atelier/contract.md` | lead | request, goal, constraints, quality bar, references, checkpoints, fixed decisions, left open |
| `.atelier/board.md` | lead | pieces, listen-only test, shared bottlenecks, order of work |
| `.atelier/tasks/T-01.md` | lead | one task card |
| `.atelier/handoffs/T-01.md` | worker | what was done, against the bar, open issues, how to verify |
| `.atelier/gates/T-01.md` | reviewer | measurements, findings, pass or fail, and the hashes of the bar and handoff it reviewed |
| `.atelier/gates/archive/` | the CLI | old gate reports, moved there on a reopen or `new-gate --force` |
| `.atelier/checks/*` | lead | automated checks from repeated lessons |
| `.atelier/lessons.md` | lead | dated mistakes by tag |
| `.atelier/rejections.md` | lead | dated rejections by the person |
| `.atelier/shelf.md` | lead | approved clips, stills, transcripts, music beds and renders to reuse |
| `.atelier/bin/atelier.py` | `init` | the project's copy of the CLI and templates |

The brand lock (for example `assets/brand-lock.md`) lives with your assets, not in `.atelier/`. The lead writes it, shelves it, and attaches it to every card.

Task statuses:

| Status | Means | Set by |
| --- | --- | --- |
| `todo` | card written, not started | `new-task`; `set-status` (archives any gate report) |
| `in-progress` | a worker holds it, or it came back from a failed gate | `set-status` (refused while a dependency is not `done`; archives any gate report) |
| `review` | handoff note complete, waiting for a gate | `set-status`, by the lead after `check-handoff` passes |
| `done` | gate passed | `gate` only; `set-status` refuses `done` without a passing gate |
| `blocked` | waiting on the person or another task; the reason is on the board | `set-status` |

## When not to use it

The method has a cost: questions, files, a second agent for every check. For trimming 2 seconds off a clip, swapping one caption or a quick question, that cost is waste, and the `start` skill says to skip the method entirely. For a job that one worker can finish in one session, producing at most 1 output with no shared render, for example a single 20-second vertical clip, the `start` skill has a small job fast path: one round of 3 to 5 questions, one card, one gate. The fast path removes paperwork, never the gate.

## Adapting it to your own videos

`profile-video` carries defaults for explainers, motion videos from a voice recording, screen-recording edits and short vertical clips. Every number in it is meant to be tuned. To fit it to your channel, client or house style:

1. **Find your numbers.** Write down the 5 to 10 things you actually check when you judge a finished video, and put a number on each: length, cuts per 10 seconds, caption size and line length, loudness, music level under the voice, colour values, safe margins. These are your default quality bar.
2. **Name your bottlenecks.** What can only one process touch at a time? The render machine, a paid generation budget, the master timeline, the final mix, a client's review slot. Each becomes a queue.
3. **Define your cheap draft.** What is the 10% version that shows the direction? A storyboard of stills, a 480p cut with placeholders, one 5-second test clip, captions as a text file before burn-in.
4. **Write your never-list.** The 3 to 7 looks that must never appear in your videos. They go into the brand lock and become constraints on every card.
5. **Seed the shelf.** Put your approved logo animation, end card, music beds and lower thirds on the shelf before the first job, so workers start from them.
6. **Let the checks grow.** Do not write checks up front for mistakes you have not seen. Log lessons, and let the second occurrence tell you which checks you need.
7. **Keep a house brand lock.** If you produce the same kind of video often, keep one brand lock file and shelve it in every project, so the lead never rediscovers your colours and type.

Keep the core intact: transcript and research before questions, the whole map before work, one lead, measurable cards, light briefs, state in files, an independent gate, checks for repeats, drafts before finals, few workers and real queues, and the person's word as final. Change everything else.
