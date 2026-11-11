---
name: profile-video
description: Video defaults for every atelier-video job, independent of any tool - formats, transcript first, the listen-only test, the brand lock, constraints, quality bars, render/generate/mix queues, cost control, a sample segment card and lesson tags. The start skill always loads it; use it with interrogate, board, contract and gate so the lead maps segments and sets measurable bars instead of vague taste words.
---

# Profile: video and motion

This profile adds video defaults to the core skills. `start` always loads it; use it together with `interrogate`, `board`, `contract` and `gate`; it does not replace them. It names no tool and no generator: pick whatever the project already uses. Every number below is a default to tune.

## Rule zero: describe with numbers, not adjectives

"Warm", "punchy" and "clean" mean something different to every agent. Write instead:

- Colours as hex codes: background `#F4EFE6`, accent `#1F6F5C`.
- Counts: 3 product shots, 2 text cards, 1 logo end card.
- Durations: hook 0:00 to 0:03, each text card on screen at least 1.5 s.
- Sizes: captions 64 px at 1080 px width, safe margin 5% on every side.
- Rates: 8 to 10 visual changes per 10 seconds (a default; tune it per brand).

## Formats

Pick the row that fits, then tune it during `interrogate`.

| Format | Typical length | Frame | Segments | Usual first task |
| --- | --- | --- | --- | --- |
| Explainer | 60 to 120 s | 16:9, 1920x1080 | 6 to 8 of 10 to 20 s | clean transcript or script |
| Motion video from a voice recording | 30 to 180 s | 16:9 or 1:1 | 10 to 20 s each | clean transcript with word timestamps |
| Screen-recording edit | 3 to 15 min | 16:9, the capture's resolution | one chapter of 1 to 3 min each | transcript and cut list |
| Short vertical clips | 15 to 60 s each | 9:16, 1080x1920 | one clip per worker | transcript and chosen passages |

## Step 1: turn audio into text first

Most agents cannot read audio reliably; treat it as unreadable until it is text. Every voice track, interview or reference video is useless to them until it is text.

1. Run speech-to-text on every audio source, with word-level timestamps.
2. Clean the transcript: fix names and product terms, remove filler words, mark speaker changes, keep timestamps.
3. Save it as a file and put it on the shelf. Every later task reads the transcript, not the audio.
4. Never trust the raw transcript for names, numbers or prices; the lead checks those against the person's notes.

## Step 2: map the board in segments

Split any video longer than 30 seconds into segments of 10 to 20 seconds; a screen-recording edit splits into chapters of 1 to 3 minutes, and a set of vertical clips into one clip each. One worker owns one segment.

For each segment, run the **listen-only test**: read only the transcript lines for that segment and ask, "Would a viewer understand this by audio alone?"

- Yes: the picture supports, so motion and b-roll are free choices.
- No: write on the board exactly what must be on screen (a number, a chart, a product close-up, a name) and when.

Board row example:

| Task | Segment | Time | Listen-only test | Must be on screen |
| --- | --- | --- | --- | --- |
| T-02 | Hook | 0:00-0:12 | pass | none |
| T-03 | Price | 0:12-0:27 | fail | "$29 per month" as text, 0:15-0:19 |

## Brand lock

Write one fixed reference file before any generation, put it on the shelf and attach it to every task card under Examples and references. Workers never change it.

The brand lock holds:

- A character or product sheet: the same subject from at least 4 angles (front, back, side, three-quarter), on a plain background.
- Exact colours as hex codes, with what each is used for. At most 5 brand colours.
- Typefaces, weights and minimum sizes.
- A never-list: looks that are banned.

Never-list example (an illustration only; each brand writes its own):

- no neon colours
- no glow, lens flare or bloom
- no stock emoji or clip art
- no gradients on text
- no more than 2 typefaces
- no camera shake on product shots

## Constraints to copy into the contract

- Never change the brand lock file during the job; only the lead edits it after the person approves.
- Never render at full resolution before the low-res draft is approved.
- Never generate a clip or image without first checking the shelf for one that fits.
- Never ship a segment that failed the sync gate.
- Never put text on screen that is not in the cleaned transcript or the card.
- Never let music cover the voice.

## Quality bar defaults

Every line holds a number or a pass/fail test. These are defaults to tune.

| Bar | Default | How the reviewer measures it |
| --- | --- | --- |
| Audio and picture sync | drift at most 1 frame | Compare voice timestamps with cut and caption frames |
| Motion density | 8 to 10 visual changes per 10 s (tune per brand) | Count cuts, moves and new elements per 10 s window |
| Static hold | no frame held still for more than 3 s | Scan the timeline |
| Loudness | -14 LUFS integrated, true peak at most -1 dBTP | Loudness meter on the full mix |
| Music under voice | music at least 15 dB below voice while speaking | Meter the music stem during speech |
| Captions | 100% of spoken words, at most 2 lines, at most 32 characters per line | Compare with cleaned transcript |
| Text on screen | each card readable for at least 1.5 s | Frame count |
| Colours | only hex codes from the brand lock | Sample frames, compare values within a tolerance of 3 per channel |
| Duration | within 0.5 s of the target | Read file length |
| Resolution | draft 480p, final 1080p or as set in the contract | Read file metadata |

## Bottleneck queues

- **render**: all final renders go through one queue, one at a time. Renders are slow and fight for the same machine.
- **generate**: paid image or clip generation, one queue, with a budget per task.
- **mix**: the final audio mix of the whole video, done once, after every segment passes.
- **brand-lock**: the reference file; only the lead edits it.

Run segment workers in parallel, at most 4 at a time by default; see `dispatch` for when to raise it. The joining of segments is one task that waits on all of them.

## Cheap draft first

1. Low-res draft at 480p, with placeholder frames where a generated clip is still missing.
2. The person reviews the draft at the approval checkpoint.
3. Only then render the full-resolution final through the render queue.

## Control cost: mix images and clips

- Use still images with simple moves (pan, zoom, slide) for most of the runtime.
- Save generated motion clips for the 2 to 4 moments that need real movement.
- Default ratio: about 70% stills with motion, 30% short clips of 2 to 5 s.

## Tag and shelve every output

Every generated clip, image, transcript and music bed gets a tag the moment it is made, in its file name or metadata (for example `price-bg-draft1.png`). Only approved outputs go on the shelf with `shelve`; drafts keep their tag but stay off the shelf. Search the shelf before generating anything new.

```
python3 .atelier/bin/atelier.py shelve product-front-4k assets/product_front.png "Product front view, plain #F4EFE6 background"
```

## Light-touch audio

- Target -14 LUFS integrated for the final mix; tune per platform.
- Keep music at least 15 dB under the voice while someone speaks.
- Fade music in and out over 0.5 to 1 s; no hard cuts in the music bed.
- Remove breaths and clicks only where they distract; do not over-process the voice.

## Gates

The lead runs every gate with the `atelier-video:reviewer` subagent named on the card, never the worker. On every segment it:

1. Reads the card, the brand lock and the handoff note.
2. Reads frame timestamps and the transcript timestamps; it never trusts "in sync" in a handoff note.
3. Rejects any segment whose audio and picture drift more than 1 frame.
4. Counts visual changes per 10 seconds and compares with the bar.
5. Samples at least 5 frames per segment for brand colours and the never-list.
6. Checks every "must be on screen" item from the board is present at its time.
7. Writes one line per bar into `.atelier/gates/T-NN.md`; the lead runs `python3 .atelier/bin/atelier.py gate T-NN`.

## Sample task card: a 15-second clip

```markdown
---
id: T-04
title: Price segment, 15 s
status: todo
owner: worker-1
reviewer: reviewer-1
depends_on: [T-01]
queue: render
---

# T-04: Price segment, 15 s

## Goal
A 15-second segment (0:12-0:27) that shows the price and the 3 plan features while the voice reads them.

## Constraints
- Never change the brand lock or use a colour not in it.
- Never generate a new product shot; use the shelf entry product-front-4k.
- Never render above 480p before the draft is approved.

## Quality bar
- Duration 15.0 s, within 0.5 s.
- Audio and picture drift at most 1 frame.
- 12 to 15 visual changes in the 15 s.
- "$29 per month" on screen from 0:15 to 0:19, at least 72 px.
- At most 1 generated clip, at most 4 s long.

## Examples and references
- Brand lock: assets/brand-lock.md
- Transcript lines 14-19 of transcript/clean.md

## Approval checkpoint
480p draft goes to the person before the final render.

## Fixed decisions
- Background #F4EFE6, price text #1F6F5C.

## Left open on purpose
- Order and style of the moves between stills.
```

## Common lesson tags

| Tag | What went wrong | Example check |
| --- | --- | --- |
| sync-drift | Captions or cuts drifted from the voice | Fail if any caption start differs from its word timestamp by more than 1 frame |
| off-brand-colour | A colour not in the brand lock appeared | Fail if sampled frames hold a colour outside the brand list |
| never-list | A banned look slipped in | Grep the card and generation notes for never-list words |
| untagged-output | A generated file has no tag | Fail if a file in assets/ has no tag in its name or metadata |
| unshelved-asset | An approved clip was not shelved | Fail if an approved file in assets/final/ has no shelf row |
| regenerated-duplicate | A new clip was made when one existed | Fail if a new generation has a tag already on the shelf |
| loud-music | Music covered the voice | Fail if music is less than 15 dB under voice during speech |
| static-hold | Picture held still too long | Fail if any hold exceeds 3 s |
