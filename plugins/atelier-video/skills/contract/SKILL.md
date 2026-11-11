---
name: contract
description: Turns the person's short request into a measurable contract in .atelier/contract.md, then writes one task card per board piece with goal, never-constraints, a numeric quality bar, examples, an approval checkpoint, fixed decisions, and what is left open. Use after board and before dispatch; every card must pass check-card before it goes to a worker.
---

# Contract: from a short request to measurable cards

The person gives you a sentence and a recording. Workers and reviewers need lines they can check. This skill turns the first into the second, twice: once for the whole job (the contract) and once per piece (the task cards). You are the lead; only you write these files.

## Step 1: write the contract

Fill `.atelier/contract.md`, section by section:

1. **Request**: the person's words, quoted exactly.
2. **Goal**: what exists when the job is done, in 1 or 2 sentences.
3. **Constraints**: what must never happen, each line starting with "Never" or "Must not".
4. **Quality bar**: how you will know it is good. Every line holds a number or a pass/fail test.
5. **Examples and references**: the brand lock, the cleaned transcript, earlier videos the person likes, clips to match. Check `.atelier/shelf.md` first.
6. **Approval checkpoints**: at least plan, 480p draft, and final.
7. **Fixed decisions**: everything the person approved during `interrogate`. Workers do not reopen these.
8. **Left open on purpose**: choices you trust the workers to make.

Every line in the contract must be something a reviewer can check without asking you.

## Step 2: turn vague words into numbers

A quality bar without numbers cannot be gated. For every vague word, offer the person a number and get it confirmed.

| The person says | The bar says |
| --- | --- |
| "punchy" | 8 to 10 visual changes per 10 seconds; hook ends by 0:03 |
| "not boring" | no frame held still for more than 3 s |
| "short" | 90 s within 0.5 s, or 30 to 45 s per vertical clip |
| "in sync" | every caption and cut within 1 frame of its word timestamp |
| "readable captions" | 56 px at 1920 px width, at most 2 lines, at most 32 characters per line |
| "on brand" | only the 5 brand-lock hex codes, within 3 per channel in sampled frames |
| "music not too loud" | music at least 15 dB under the voice while someone speaks |
| "loud enough" | -14 LUFS integrated, true peak at most -1 dBTP |
| "works on phones" | 9:16 at 1080x1920; all text inside a 6% safe margin |

How to find the number:

1. Measure what exists now. "Tighter" means fewer seconds than today's cut, measured.
2. Propose a number in your recommendation and let the person correct it.
3. When no number fits, write a pass/fail test: "with the sound off, a viewer can name the price after one watch".

## Step 3: phrase constraints as "never"

Constraints say what must never happen, not what should happen.

- Weak: "Be careful with the numbers." Strong: "Never show a number or price that is not in the cleaned transcript."
- Weak: "Keep the style consistent." Strong: "Never add a typeface or a colour outside the brand lock."
- Weak: "Watch the budget." Strong: "Must not generate more than 2 clips in this segment; check the shelf first."

Every rejection logged in `.atelier/rejections.md` that applies to this job becomes a "never" line.

## Step 4: one task card per piece

For every row on the board:

1. Create the card: `python3 .atelier/bin/atelier.py new-task T-03 "Problem, 0:15-0:30"`.
2. Fill the front matter: `owner`, `reviewer`, `depends_on`, `queue`, matching the board. Owner and reviewer are distinct names such as `worker-1` and `reviewer-1`.
3. Fill all 7 sections: Goal, Constraints, Quality bar, Examples and references, Approval checkpoint, Fixed decisions, Left open on purpose. No section may be empty: write "none" in Fixed decisions or Left open on purpose when there is nothing. `check-card` checks all 7.
4. Copy the contract lines that apply to this piece, and narrow them. A card's bar must be checkable on this piece alone.
5. Run `python3 .atelier/bin/atelier.py check-card T-03`. It must pass before the card is dispatched. Fix and re-run until it does.

## The minimal brief rule

A worker gets three things: the **fixed decisions**, the **quality bar**, and **what is left open on purpose**. It does not get a shot-by-shot recipe.

- A recipe caps quality at the level of the person who wrote it, and the worker stops thinking.
- A recipe hides the goal. When a step does not fit reality, the worker cannot adapt.
- A card longer than about 60 lines is usually a recipe in disguise. Cut it.

Give numbers instead of instructions. "12 to 15 visual changes in 15 s, no still longer than 3 s" leaves the worker free to find the best cut; "zoom in on every sentence" does not, and may be wrong.

## Bad card vs good card

Bad:

```markdown
## Goal
Make the problem segment engaging.

## Constraints
Stay on brand.

## Quality bar
Should feel punchy and in sync.

## Examples and references
-

## Approval checkpoint
-

## Fixed decisions
1. Open on the inbox screenshot. 2. Zoom in 20%. 3. Cut to the spreadsheet.
4. Add a red arrow. 5. Fade to white at the end.

## Left open on purpose
-
```

Problems: no number in the bar, a constraint that cannot fail, a shot list where fixed decisions belong, nothing left open, no checkpoint. `check-card` rejects it.

Good:

```markdown
## Goal
A 15-second segment (0:15-0:30) that shows the cost of chasing late invoices while the voice describes it.

## Constraints
- Never use a colour, typeface or look outside assets/brand-lock.md.
- Never put a number on screen that is not in transcript/clean.md.
- Never generate a clip; use stills and screenshots with moves.
- Must not render above 480p.

## Quality bar
- Duration 15.0 s within 0.5 s.
- Every caption starts within 1 frame (at 30 fps) of its first word's timestamp.
- 12 to 15 visual changes in the 15 s; no still held longer than 3 s.
- 5 sampled frames hold only brand-lock colours, within 3 per channel.

## Examples and references
- assets/brand-lock.md; transcript/clean.md lines 7-12; input/screens/inbox.png.

## Approval checkpoint
None; the person sees it inside the 480p draft.

## Fixed decisions
- Captions in the brand-lock caption style, burned in.

## Left open on purpose
- Order and style of moves, which screenshot crops to use.
```

## Before you move on

1. Every card passes `check-card`.
2. The board and the cards agree: run `python3 .atelier/bin/atelier.py status`.
3. Show the person the contract and the board at the approval checkpoint. No dispatch before their yes.
