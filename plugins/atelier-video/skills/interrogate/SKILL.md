---
name: interrogate
description: Researches the job first, then questions the person in short rounds, each question with a recommended answer, until intent is clear and the person confirms a restatement of 5 lines or fewer. Use right after start, before any board, contract, or work, and again whenever a worker's question shows the intent was not clear.
---

# Interrogate: research, then ask

Work started on a wrong guess is the most expensive mistake in a video job: it shows up at the first render. This phase makes the intent clear before anything is built. You are the lead; only you talk to the person.

## Step 1: research before you ask

Never ask the person something you could find out yourself. Spend the first part of this phase looking, not asking.

0. **Transcript and profile.** Turn every recording into text first, with word timestamps (see `profile-video`, which `start` always loads). Use the profile's defaults as extra questions and recommended answers. Compare names, numbers and prices in the transcript with the person's notes; every mismatch becomes a question.
1. **Rejections.** Read `.atelier/rejections.md` and `~/.atelier/rejections.md`. Do not recommend anything listed there.
2. **The shelf.** Read `.atelier/shelf.md`. An approved output that already does 80% of the job beats new work.
3. **What exists.** Look at the recordings, screenshots, logos, earlier renders, fonts and notes the job will use. Note lengths, frame rates, resolutions, aspect ratios, and anything missing or low quality.
4. **Similar work.** Look for how this kind of video is usually made: common structures (hook, problem, how it works, call to action), typical lengths and pacing, known traps.
5. **Risks.** List the 3 to 5 things most likely to go wrong (a misheard number, a slow render, a paid generation budget, a shared timeline, an unclear audience or platform).

Hand steps 3 to 5 to an `atelier-video:researcher` subagent with a brief of what to find and a limit of one page of findings, at most 40 lines.

Write the findings down in your own notes (a few lines each). They feed the recommended answers.

## Step 2: size the job

- **Small job** (one worker, one session, at most 1 output, for example one vertical clip): 1 round of 3 to 5 questions.
- **Big job**: rounds of at most 7 questions each. Keep going until you could write the contract without guessing. Most big jobs need 2 or 3 rounds; stop at the first round where every answer matches your recommendation.

## Step 3: ask in rounds

Rules for every question:

1. **Carry a recommended answer.** Write it right after the question, based on your research. The person must be able to reply "go with your recommendations" and get a sensible job.
2. **One decision per question.** No "and also".
3. **Ask about outcomes, not steps.** The person decides what "good" is; you and the workers decide which cuts, moves and crops get there.
4. **Number the questions** so the person can answer "3: no, use B".
5. **Do not re-ask** what research already answered. State it as an assumption instead.

Over all rounds, cover these 7 topics (a small job may merge several into one question):

1. **Goal**: what exists when this is done: format, length, aspect ratio, where it will be shown.
2. **Audience**: who watches, on what screen, with sound on or off.
3. **What must never happen**: the hard limits. These become the "never" lines of the contract.
4. **What "good" means in numbers**: duration, sync, visual changes per 10 seconds, caption size, loudness, resolution. Offer a number in your recommendation.
5. **References they like**: earlier videos, a logo, a palette, a clip to match or avoid.
6. **Budget, time, and limits**: how many generated clips, render time, deadline, tools that may or may not be used.
7. **Approval points**: where the person wants to look before work goes on. Recommend at least: plan, 480p draft, final.

## Example round

Request: "Cut 3 vertical clips from my 40-minute talk recording." Research found the recording is 16:9 at 30 fps and the transcript has 3 strong passages.

> Before I plan this, 6 questions. Each has my recommendation; reply "go with your recommendations" or correct by number.
>
> 1. **Goal**: Which 3 passages? *Recommended: the ones at 6:10, 18:40 and 31:05; each makes one point on its own.*
> 2. **Audience**: Who watches, and with sound? *Recommended: phone viewers scrolling with the sound off, so captions burned in.*
> 3. **Never**: What must never happen? *Recommended: never cut a sentence mid-word; never put words on screen you did not say; never crop your face out of the 9:16 frame.*
> 4. **Good in numbers**: How long and how busy? *Recommended: 30 to 45 s each, 9:16 at 1080x1920, captions 64 px with at most 2 lines, no frame held still longer than 3 s.*
> 5. **References**: Is there a clip whose look you like? *Recommended: match the caption style of the clip you posted last month.*
> 6. **Approval points**: Where do you want to look? *Recommended: the 3 chosen passages as text, one 480p draft clip, then all 3 finals.*

## Step 4: handle the answers

1. When the person accepts a recommendation, it becomes a fixed decision.
2. When the person rejects something, log it at once: `python3 .atelier/bin/atelier.py reject "what the person rejected"`.
3. When an answer is vague ("fast", "clean", "not too long"), ask one follow-up that offers a number. The `contract` skill shows how.
4. When an answer opens a new question, put it in the next round, not in a long reply.

## Step 5: restate and get a yes

End with a restatement of **5 lines or fewer**:

> Here is what I understood:
> 1. Three 9:16 clips, 30 to 45 s each, from the talk passages at 6:10, 18:40 and 31:05.
> 2. Never cut mid-word, never show words you did not say, never crop your face out.
> 3. 1080x1920, captions 64 px, at most 2 lines, no still longer than 3 s, caption style of last month's clip.
> 4. You see the passages as text, one 480p draft clip, then the 3 finals.
> Is that right?

Do not move to the `board` skill until the person says yes. If they correct a line, fix it and restate again.

## Anti-patterns

- Asking 15 questions at once. The person answers 4 and skips the rest.
- Questions without a recommendation. They push your work onto the person.
- Asking about craft details (which transition, which crop, which file). Those are yours to decide.
- Starting the board "while waiting" for answers. A wrong guess costs more than the wait.
