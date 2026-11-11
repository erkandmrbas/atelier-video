# Example: a 90-second explainer from a voice recording

A condensed session. The person has a 92-second voice recording explaining their invoicing app, a folder of app screenshots, and a logo. They want a 90-second explainer video. The example names no tool: use whatever speech-to-text, editing, image and render tools your project already has. Lines starting with `$` are commands the lead ran; the output under them is what the CLI printed in a real run of this job's commands, with the paths shortened to `~` for reading. Long passages are cut where marked `[...]`.

## 1. The request

> **Person:** /atelier-video:start Turn my voice memo into a 90-second explainer for the website. Files are in `input/`.

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/atelier.py" init
atelier ready in ~/projects/explainer/.atelier
Created: contract.md, board.md, lessons.md, rejections.md, shelf.md
Next: the lead fills contract.md and board.md, then: python3 .atelier/bin/atelier.py new-task T-01 "title"
```

`start` loads `profile-video`, as it does for every job.

## 2. Transcript first, then questions

Agents cannot read audio reliably, so the first thing the lead does is research by turning the recording into text. A speech-to-text pass with word-level timestamps gives a raw transcript of 231 words. The lead reads it next to `input/notes.txt` and finds one mismatch: the transcript says "fourteen dollars a month", the notes say "$40". The transcript is not trusted blindly; it goes into the questions.

`~/.atelier/rejections.md` holds one line from an earlier project: "no stock-photo people shaking hands". The lead will not propose that look.

> **Lead:** Before I plan, 7 questions. Each has my recommendation; reply "go with your recommendations" or correct by number.
> 1. **Goal**: One 90-second video for the website home page, landscape? *Recommended: yes, 16:9, plus nothing else for now.*
> 2. **Audience**: Who watches? *Recommended: owners of small agencies, often with the sound off, so captions burned in.*
> 3. **Price**: The recording sounds like "fourteen", your notes say $40. Which is right? *Recommended: $40 per month, from your notes.*
> 4. **Never**: What must never happen? *Recommended: never show a price or number that is not in the cleaned transcript; never use colours outside your logo palette; no stock-photo people.*
> 5. **Good in numbers**: *Recommended: 90 s within 0.5 s; audio and picture drift at most 1 frame; 8 to 10 visual changes per 10 s; -14 LUFS.*
> 6. **Budget**: How many generated motion clips? *Recommended: at most 4 clips of 2 to 5 s; everything else is screenshots and stills with pans and zooms.*
> 7. **Approval points**: *Recommended: the plan, a 480p draft of the whole video, and the 1080p final.*

> **Person:** 3: yes, $40, the transcript is wrong. Everything else as you recommend.

> **Lead:** Here is what I understood:
> 1. One 90-second 16:9 explainer from your recording, captions burned in, for agency owners.
> 2. Never show a number not in the cleaned transcript (price is $40/month); only logo palette colours; no stock people.
> 3. 90 s ±0.5 s, drift at most 1 frame, 8 to 10 changes per 10 s, -14 LUFS, at most 4 generated clips.
> 4. You see the plan, a 480p draft, and the 1080p final. Is that right?

> **Person:** Yes.

## 3. The brand lock

Before any generation, the lead writes `assets/brand-lock.md` and shelves it. Workers read it; only the lead may change it.

```markdown
# Brand lock
- Background #F7F5F0; text #1D2433; accent #2F6FED; success #1E9E6A; muted #8A93A6. No other colours.
- Typeface: the logo face for titles (weight 700), the app UI face for captions (weight 500).
- Captions: 56 px at 1920 px width, at most 2 lines, at most 32 characters per line, bottom safe margin 6%.
- App screens: the 12 screenshots in input/screens/, never redrawn.
- Never: neon, glow or lens flare; gradients on text; stock-photo people; more than 2 typefaces; camera shake.
```

```
$ python3 .atelier/bin/atelier.py shelve brand-lock assets/brand-lock.md "fixed colours, type, caption rules and never-list"
Shelved assets/brand-lock.md as 'brand-lock'.
```

## 4. The board, with the listen-only test

The lead splits 90 seconds into 6 segments of 15 seconds. For each one it reads only the transcript lines and asks: would a viewer understand this by audio alone? Where the answer is no, the board says exactly what must be on screen and when.

```markdown
## Pieces
| Task | Title | Depends on | Parallel group | Bottleneck queue | Owner | Reviewer | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-01 | Clean transcript with word timestamps | - | A | - | worker-1 | reviewer-1 | todo |
| T-02 | Hook, 0:00-0:15 | T-01 | B | - | worker-1 | reviewer-1 | todo |
| T-03 | Problem, 0:15-0:30 | T-01 | B | - | worker-2 | reviewer-1 | todo |
| T-04 | How it works, 0:30-0:45 | T-01 | B | generate | worker-3 | reviewer-2 | todo |
| T-05 | Numbers, 0:45-1:00 | T-01 | B | - | worker-4 | reviewer-2 | todo |
| T-06 | Price, 1:00-1:15 | T-01 | B | generate | worker-1 | reviewer-2 | todo |
| T-07 | Call to action, 1:15-1:30 | T-01 | B | - | worker-2 | reviewer-1 | todo |
| T-08 | Assemble and mix, 480p draft | T-02 ... T-07 | C | render | worker-3 | reviewer-1 | todo |
| T-09 | Final render, 1080p | T-08 | D | render | worker-3 | reviewer-2 | todo |

## Listen-only test
| Task | Passes by audio alone? | Must be on screen |
| --- | --- | --- |
| T-02 | yes | none |
| T-03 | yes | none |
| T-04 | no | the 3 steps "Track, Invoice, Get paid" as text, 0:33-0:41 |
| T-05 | no | "3 hours saved per week" as text and a bar chart, 0:48-0:55 |
| T-06 | no | "$40 per month" as text, 1:03-1:08, at least 96 px |
| T-07 | no | the web address as text, 1:22-1:30 |

## Shared bottlenecks
- generate: paid clip generation, one at a time, at most 2 clips per task.
- render: full-length renders share one machine; T-08 and T-09 run one after the other.
- mix: the full audio mix happens once, inside T-08.
- brand-lock: only the lead edits assets/brand-lock.md.

## Order of work
- A: T-01 alone. B: 6 segments, at most 4 workers at once; T-06 waits for T-04 in the generate queue.
- C: T-08 when all 6 segments pass their gates. D: T-09 after the person approves the 480p draft.
```

## 5. A segment card

The lead writes 9 cards, each passing `python3 .atelier/bin/atelier.py check-card T-NN`. T-05 in full:

```markdown
---
id: T-05
title: Numbers, 0:45-1:00
status: todo
owner: worker-4
reviewer: reviewer-2
depends_on: [T-01]
queue:
---

## Goal
A 15-second segment (0:45-1:00) that makes "3 hours saved per week" impossible to miss while the voice says it.

## Constraints
- Never use a colour, typeface or look outside assets/brand-lock.md.
- Never generate a clip; use stills and screenshots with moves.
- Never render above 480p.

## Quality bar
- Duration 15.0 s within 0.5 s.
- Every caption starts within 1 frame (at 30 fps) of its first word's timestamp.
- 12 to 15 visual changes in the 15 s; no still held longer than 3 s.
- "3 hours saved per week" and the bar chart on screen 0:48-0:55, text at least 80 px.
- 5 sampled frames hold only brand-lock colours, within 3 per channel.

## Examples and references
- assets/brand-lock.md; transcript/clean.md lines 18-24; input/screens/reports.png.

## Approval checkpoint
none; the person sees it inside the 480p draft of T-08.

## Fixed decisions
- Chart: 2 bars, "before" #8A93A6 and "after" #2F6FED, labelled in hours.

## Left open on purpose
- Order and style of moves, how the chart builds, which screenshot crops to use.
```

## 6. Dispatch

T-01 goes first. worker-1 cleans the transcript (names, the $40 price, filler words removed, word timestamps kept), the gate passes, and the lead shelves it so every segment reads text, never audio:

```
$ python3 .atelier/bin/atelier.py gate T-01
[...]
Gate T-01: PASS. Status set to done.
$ python3 .atelier/bin/atelier.py shelve transcript-clean transcript/clean.md "cleaned transcript, 224 words, word timestamps"
Shelved transcript/clean.md as 'transcript-clean'.
```

Six segments are ready; the cap is 4 workers. The lead dispatches T-02 to T-05, each to its own `atelier-video:worker` subagent, with the three-line brief (card path, contract path, "write your handoff note and mention the task id"). T-06 is in the same `generate` queue as T-04 and waits, even after T-02 frees a slot; T-07 takes that slot instead.

```
$ python3 .atelier/bin/atelier.py status
id    title                                  status       handoff  gate
----  -------------------------------------  -----------  -------  ----
T-01  Clean transcript with word timestamps  done         yes      pass
T-02  Hook, 0:00-0:15                        review       yes      none
T-03  Problem, 0:15-0:30                     in-progress  no       none
T-04  How it works, 0:30-0:45                in-progress  no       none
T-05  Numbers, 0:45-1:00                     in-progress  no       none
T-06  Price, 1:00-1:15                       todo         no       none
T-07  Call to action, 1:15-1:30              in-progress  no       none
T-08  Assemble and mix, 480p draft           todo         no       none
T-09  Final render, 1080p                    todo         no       none

Problems: none
```

## 7. Shelf reuse

T-04 generates one 4-second clip of the invoice screen sliding into a "Paid" state. The person later approves it inside the draft, and it goes on the shelf as `invoice-paid-clip`. When worker-2 starts T-07 (call to action), it reads the shelf first, finds that clip, and ends the video on it instead of generating a new one. One paid generation saved, and the last shot matches one the person has already seen.

## 8. The sync gate fails, then passes

reviewer-2, an `atelier-video:reviewer` subagent, checks T-05. It reads frame times from the 480p preview and compares them with the word timestamps in `transcript/clean.md`, instead of trusting "in sync" from the handoff note. `.atelier/gates/T-05.md`:

```markdown
---
task: T-05
reviewer: reviewer-2
result: fail
---

## Measurements
- Duration: 15.03 s. PASS
- Caption sync: 7 captions; caption 4 starts at 52.53 s, word "three" at 52.40 s = 4 frames late; caption 6 is 2 frames late. FAIL
- Visual changes: 13 in 15 s; longest still 2.1 s. PASS
- "3 hours saved per week" and chart: on screen 0:48.1-0:55.0, text 88 px. PASS
- Colours: 5 frames sampled, all within 2 per channel of brand-lock values. PASS

## Findings
- Captions are timed from sentence starts, not word starts. Re-time all 7 from the word timestamps.
```

```
$ python3 .atelier/bin/atelier.py gate T-05
[...]
FAIL gate result is pass (found 'fail') (reviewer: fix it in .atelier/gates/T-05.md)
[...]
Gate T-05: FAIL. The work does not move on until every line passes.
$ python3 .atelier/bin/atelier.py set-status T-05 in-progress
Archived the gate report to .atelier/gates/archive/T-05-20261111-125451.md. The work is reopened, so a new review is needed (new-gate).
T-05 status: in-progress
$ python3 .atelier/bin/atelier.py lesson sync-drift "T-05 captions timed from sentence starts, up to 4 frames late"
Lesson logged: sync-drift (seen 1 time).
```

worker-4 re-times the captions from word timestamps and updates the handoff note. The lead runs `check-handoff T-05` and `set-status T-05 review`. reviewer-2, a fresh `atelier-video:reviewer` subagent, starts a new report with `new-gate T-05 --reviewer reviewer-2` and measures again: largest offset 1 frame, every other line unchanged.

```
$ python3 .atelier/bin/atelier.py gate T-05
[...]
Gate T-05: PASS. Status set to done.
```

The failed version never reached T-08. Nothing downstream built on it.

## 9. The 480p draft, a rejection, and the final

With all 6 segments `done`, T-08 joins them in the `render` queue, mixes the voice with a music bed 18 dB under speech, and renders the whole video at 480p. It passes its gate (90.2 s, -14.2 LUFS, true peak -1.4 dBTP). The lead shows the person the draft and what it cost: 2 generated clips out of a budget of 4, 6 minutes of render time.

> **Person:** Good. One thing: the price bouncing in at 1:03 feels cheap. Just fade it in.

```
$ python3 .atelier/bin/atelier.py reject "price text bounce-in at 1:03 in the 480p draft: 'feels cheap, just fade it in'"
Rejection recorded (2026-11-11 12:54, explainer) in: ~/projects/explainer/.atelier/rejections.md, ~/.atelier/rejections.md
```

The lead adds "Never use bounce or elastic moves on text" to the contract and reopens T-06 with that one change (`set-status T-06 in-progress`, which archives T-06's old gate report). worker-1 revises in place: the price now fades in over 0.4 s; every other frame of the segment stays as approved. reviewer-2 writes a new gate report, T-06 passes its gate again, T-08 re-renders the 480p draft, and the person compares the two versions side by side.

> **Person:** Approved. Make the final.

T-09 renders at 1080p in the `render` queue. reviewer-2 gates the final against the contract: 1920x1080, 90.2 s, -14.1 LUFS, true peak -1.3 dBTP, music at least 15 dB under voice during speech, drift at most 1 frame across all 41 captions, only brand-lock colours in 20 sampled frames.

```
$ python3 .atelier/bin/atelier.py gate T-09
[...]
Gate T-09: PASS. Status set to done.
$ python3 .atelier/bin/atelier.py status --strict
id    title                                  status  handoff  gate
----  -------------------------------------  ------  -------  ----
T-01  Clean transcript with word timestamps  done    yes      pass
[...]
T-09  Final render, 1080p                    done    yes      pass

Problems: none
$ python3 .atelier/bin/atelier.py shelve explainer-final out/explainer-1080p.mp4 "approved 90 s explainer, 1080p, captions burned in"
Shelved out/explainer-1080p.mp4 as 'explainer-final'.
```

> **Lead:** The 1080p final is in `out/`. All 9 tasks passed their gates; 1 rejection logged (the price bounce), 1 lesson logged (sync-drift, once, so no check yet). If captions drift again in this project, the lesson becomes a check that blocks every gate. Do you approve the final?

> **Person:** Yes.
