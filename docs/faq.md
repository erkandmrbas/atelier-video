# FAQ

### What kinds of video is it for?

Any video job too big for one pass: explainers from a script or a voice recording, motion videos built to a voice track, screen-recording edits into tutorials, and short vertical clips cut from a longer talk. The `profile-video` skill, which `start` always loads, carries default numbers for all of them; the lead tunes them with you during the questions. See "Adapting it to your own videos" in [method.md](method.md).

### Does it make the video itself?

No. atelier-video runs the job: questions, the board, the cards, the workers, the gates, the drafts and the shelf. The workers use whatever speech-to-text, editing, image, audio and render tools your project already has. The skills name no product, model or paid service; they say "speech-to-text", "render", "generated clip".

### Does it need Claude Code?

Yes. atelier-video is a Claude Code plugin: it runs workers and reviewers as Claude Code subagents (`atelier-video:worker`, `atelier-video:reviewer`, `atelier-video:researcher`) and uses three Claude Code hooks (SessionStart, Stop, SubagentStop). The CLI is a single Python 3.9+ script with no dependencies. See [install.md](install.md).

### Why does it start with a transcript?

Because agents cannot read audio reliably, and every later decision (segment boundaries, caption timing, what must be on screen) depends on the words and their timestamps. The first task in most video jobs is a cleaned transcript with word timestamps, checked by the lead against your notes for names, numbers and prices. Every segment worker reads the transcript, never the audio.

### What is the brand lock?

One file, written by the lead before any generation, that fixes the look: up to 5 colours as hex codes with their use, typefaces and minimum sizes, caption rules, and a never-list of banned looks. It goes on the shelf and onto every card under Examples and references. Workers read it and never change it; reviewers sample frames against it. It is what keeps six segments made by four workers looking like one video.

### How many agents should I run?

As many as the widest parallel group on the board, capped at 4 by default. The `dispatch` skill allows more, up to 8 in a single dispatch, only when the segments share no file and no queue, each can be checked on its own, and your rate limits allow it. More agents is not faster: every extra worker adds a brief, a handoff note, a gate and a chance of collision, and renders, paid generations and the final mix still run one at a time in their queues.

### What if a worker says "done" but there is no handoff note?

Then it is not done. Run `python3 .atelier/bin/atelier.py check-handoff T-03`. If the note is missing, has no author, or has an empty section, the command fails and the worker goes back to finish it. The SubagentStop hook catches this automatically: a worker whose final message names a task that is `in-progress` or `review` without a complete handoff note is blocked from stopping and told which command to run.

### Can a task be marked done by hand?

No. `set-status T-03 done` is refused unless the full gate passes, and `gate T-03` is the command that sets `done`. If someone edits the card's front matter directly, `status` lists it as a problem ("marked done but its gate does not pass"), `status --strict` exits 1, and the Stop hook will not let the session end until it is fixed.

### What happens to a gate report when the segment changes?

It goes stale. `new-gate` records a hash of the card's quality bar and of the handoff note in the report (`card_hash`, `handoff_hash`). If either changes after the review, `gate` fails with "the card's quality bar changed after this review" or "the handoff note changed after this review", and the reviewer must measure again and run `python3 .atelier/bin/atelier.py new-gate T-03 --reviewer NAME --force`; `--force` moves the old report to `.atelier/gates/archive/`. Reopening a task with `set-status T-03 in-progress` (or `todo`) archives its gate report on the spot, so a re-cut segment always gets a fresh review.

### Can a segment start before the transcript is done?

Not by accident. `set-status T-03 in-progress` is refused while any task in the card's `depends_on` is not `done`, and the message names each one with its status. The lead can pass `--force` to override it; the CLI then prints a warning. `status` also lists any task in progress before its dependencies are done, and any board row whose Status no longer matches the card.

### Does it cost more tokens?

Per job, usually somewhat more on planning and checking, and less on rework. The questions, the board, the cards and the gates all cost tokens. What they save is the expensive part: a full-resolution render in the wrong direction, paid clips generated twice, four segments re-cut because they do not match, and the same caption mistake made five times. The brief rule helps too: workers get a card path and three lines, not a page of instructions. For tiny jobs the overhead is not worth it; see the next question.

### Can I use it for one short clip?

Yes, with the small job fast path in the `start` skill. It applies when one worker can finish in one session, the job produces at most 1 output, and there is no shared bottleneck such as a shared render machine or a paid generation budget. You get one round of 3 to 5 questions, a short contract, one card and one gate. The fast path removes paperwork, never the gate. For trimming a clip or fixing one caption, skip the method entirely.

### Where is the state kept? Can I commit it?

Everything for a project lives in `.atelier/` at the project root: contract, board, task cards, handoff notes, gate reports, checks, lessons, rejections, shelf, and the project's own copy of the CLI in `.atelier/bin/`. Your rejection log also has a global copy at `~/.atelier/rejections.md`, so it follows you between projects. The media itself (recordings, clips, renders) stays in your own folders; the shelf only points to it.

Committing `.atelier/` is your choice. Commit it if you want the plan, the gate reports and the checks reviewed and versioned with the project, or shared with collaborators; the checks in particular are worth keeping. Add it to `.gitignore` if you consider it scratch state. Either way, never put secrets in it.

### How do I write a check?

When `lesson TAG "..."` exits with code 3, the same kind of mistake has happened twice. Write a small script in `.atelier/checks/`:

1. A `.py` or `.sh` file, or any executable file.
2. The line `lesson: TAG` in its first 5 lines, usually as a comment.
3. Exit 0 when the project is clean; exit non-zero and print the file and line of each hit when the mistake is present.
4. Keep it fast (under 1 second on a normal project) and to one pattern.

Then run `python3 .atelier/bin/atelier.py run-checks` and confirm it fails on the current mistake and passes after the fix. From then on every `gate` runs it. Good first checks for video read text files: caption files with lines over 32 characters, files in `assets/` without a tag in their name, shelf rows that point at a missing file. The `lessons` skill has a full example, and `profile-video` lists the common video lesson tags.

### What does the person actually have to do?

Answer the question rounds (or reply "go with your recommendations"), confirm the 5-line restatement, say yes or no at each approval checkpoint (by default: plan, 480p draft, final), and say what they dislike when they dislike it. Everything else is the lead's job. The person talks only to the lead, never to workers or reviewers.

### What happens after a crash or a usage limit?

Start a new session in the same project. The SessionStart hook prints the board summary and recent rejections; run `/atelier-video:start` to pick the job up. The lead resumes from the files: cards `in-progress` without a complete handoff note are restarted from the card, cards in `review` get a gate, and queues are re-checked so only one render runs at a time. Nothing depends on remembering the old chat.

### Can the reviewer be the same agent as the worker?

No. `gate` fails if the gate report's `reviewer` matches the handoff note's `author` or the card's `owner`, and it also fails unless the reviewer is the one named on the card's `reviewer:` line. The lead runs every gate with the `atelier-video:reviewer` subagent, which has no memory of the work. Give each worker and reviewer a distinct name so the check can tell them apart.

### Does atelier-video depend on any paid service or model?

No. The CLI uses the Python standard library only, and the skills name no product, model or paid service. Paid generation, if your project uses it, goes through the `generate` queue with a budget per task, so the plugin helps you spend less on it, not more.
