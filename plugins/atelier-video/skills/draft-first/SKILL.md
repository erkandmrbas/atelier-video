---
name: draft-first
description: Makes a cheap draft first and spends on the expensive final only after the person approves it at a checkpoint, revises in place instead of rebuilding, tags every output and shelves approved ones for reuse. Use before any slow, costly, or hard-to-undo step: full-resolution renders, paid clip or image generation, the final mix, or picking a look.
---

# Draft first

A 480p draft costs a fraction of the final render and catches a wrong direction while it is still cheap to change.

## Look at the shelf first

Before you make anything new:

1. Open `.atelier/shelf.md`.
2. Look for an approved output with a matching tag: the brand lock, a cleaned transcript, a generated clip, a still, a music bed, an end card, a caption style.
3. If one fits, start from it. Reuse beats regeneration: it is faster, cheaper, and already approved.
4. Read `.atelier/rejections.md` and `~/.atelier/rejections.md` too, so the draft does not repeat what the person already turned down.

## The loop

1. **Draft cheap.** Spend no more than about 10% of the final's cost or time on the draft.
2. **Show it at the approval checkpoint.** Stop and ask the person. Do not start the final while you wait.
3. **Revise in place.** Change only what the person asked to change.
4. **Approve.** The person says yes in their own words. A worker or reviewer saying "looks good" is not approval.
5. **Make the final** from the approved draft, with the same choices.
6. **Gate the final** (see the `gate` skill).
7. **Shelve** the approved final. Every output, draft or final, already carries a tag from the moment it was made.

## What a cheap draft looks like

| Output | Cheap draft | Expensive final |
| --- | --- | --- |
| Explainer or motion video | storyboard of 1 still per segment, then the whole cut at 480p with placeholders for missing clips | full-length render at 1080p or 4K |
| Screen-recording edit | cut list as text with timestamps, then a 480p cut | 1080p render with zooms, callouts and chapters |
| Vertical clips | 1 clip of the set at 480p | all clips at 1080x1920 |
| Generated clip | 1 short generation at low resolution, or a still keyframe | the full-length, full-resolution clip |
| Look and style | 2-3 directions as single frames side by side | one direction across the whole video |
| Captions | caption text file with timings, checked against the transcript | captions burned into the final |
| Music and mix | 15-second sketch of the bed under the voice | full mix at the target loudness |

## Offer directions, not one guess

When the person's taste matters and is not yet clear:

1. Make 2-3 distinct directions. Not 1 (no choice), not 10 (no focus).
2. Make each one clearly different, so the choice teaches you something.
3. Recommend one and say why in one sentence.
4. After the person picks, drop the others. Do not blend all three unless asked.
5. Log what they turned down with `python3 .atelier/bin/atelier.py reject "..."` (see the `lessons` skill).

## Revise in place

When the person asks for one change:

1. Change that one thing.
2. Keep everything already approved exactly as it was.
3. Do not regenerate the whole output to fix one part. A full rebuild can break 9 approved parts while fixing 1.
4. If the generator cannot edit in part (some only produce whole clips), say so, and keep the seed, prompt and settings the same except for the asked-for part.
5. Show the change next to the previous version so the person can compare.

## Approval checkpoints

Put the checkpoint on the task card's Approval checkpoint section, and in the contract's Approval checkpoints list. The usual three:

1. Plan (board and contract).
2. Cheap draft: the 480p cut.
3. Final: the full-resolution render.

At each one, stop. Show the output and what it cost (render minutes, generated clips used out of the budget). Ask a yes or no question with your recommended answer.

## Tag and shelve

Every generated output gets a tag the moment it is made, in its file name or metadata (for example `invoice-paid-clip-draft2.mp4`). Only approved outputs go on the shelf with `shelve`, so the next task starts from them:

```
python3 .atelier/bin/atelier.py shelve invoice-paid-clip assets/clips/invoice-paid-v3.mp4 "approved 4 s clip, invoice slides to Paid"
```

1. Use a short, stable tag that a later search would find (`invoice-paid-clip`, `transcript-clean`, `end-card`, `music-bed-calm`).
2. Point to the real path of the approved file, not a draft.
3. Describe what it is in under 15 words.
4. Shelve only what the person approved. Drafts and rejected directions stay off the shelf.

## Checklist

- [ ] Shelf and rejections read before starting.
- [ ] Draft cost about 10% of the final or less, and was rendered at draft resolution.
- [ ] The person approved the draft in their own words before the final began.
- [ ] Revisions changed only what was asked.
- [ ] Final passed the gate.
- [ ] Every output tagged when made; the approved final shelved.
