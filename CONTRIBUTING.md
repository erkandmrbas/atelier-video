# Contributing to atelier-video

Thanks for helping. This repository uses its own method: changes are planned as a contract, split into pieces, and checked by someone other than the author before they merge. Small fixes can skip the paperwork; the checks below still apply.

## Proposing a change

1. **Open an issue first** for anything larger than a typo or a one-line fix. Say what problem you saw, in which Claude Code version and which kind of video job (explainer, voice-recording motion video, screen-recording edit, vertical clip), and what you expected. A proposal that changes the method itself (one of the 11 principles, a default number, a phase) needs an issue and a short discussion before code.
2. **Keep pull requests small.** One concern per pull request. As a guide, at most 400 changed lines and 15 files.
3. **Say how you measured it.** Describe the change against a bar: which test covers it, which command shows the difference, which skill line got shorter or clearer, which video default changed and why. "Improves the skill" is not a description; "cuts `dispatch` from 240 to 190 lines with no rule removed" is.
4. **Do not edit tests to make them pass.** If a test is wrong, say so in the pull request and fix it in a separate commit with the reason.

## Running the checks

From the repository root:

```
python3 -m unittest discover -s plugins/atelier-video/scripts/tests -v
python3 tools/lint_repo.py
claude plugin validate .
```

- The unit tests cover the CLI (`plugins/atelier-video/scripts/atelier.py`): every command, its exit codes, and the hooks.
- `tools/lint_repo.py` checks that every JSON manifest parses, that the marketplace and plugin manifests agree on the name `atelier-video`, that every skill has front matter with a `name` matching its folder and a description of at most 1,024 characters, that no skill exceeds 250 lines, and that no banned word appears anywhere in the repository.
- `claude plugin validate .` checks the marketplace and plugin manifests the way Claude Code reads them. It needs Claude Code installed.
- CI also runs `bash tools/smoke_test.sh`, an end-to-end run of the CLI in a temporary project.

All of them must pass before review. CI runs the tests and the lint on Python 3.9 and 3.12.

## Style rules for skills

Skills live in `plugins/atelier-video/skills/<name>/SKILL.md` and are called as `/atelier-video:<name>`. Subagents live in `plugins/atelier-video/agents/` and are called as `atelier-video:worker`, `atelier-video:reviewer` and `atelier-video:researcher`. This plugin is for Claude Code only: write skills that use its subagents and hooks directly, with no fallback paths.

- **Front matter.** Every `SKILL.md` starts with `---`, a `name` equal to the folder name, and a `description` that says what the skill does and when to use it, in at most 1,024 characters. The description is what the agent reads to decide whether to load the skill, so lead with the trigger.
- **At most 250 lines.** If a skill grows past that, it is doing two jobs; split it or cut it.
- **Numbers over adjectives.** Write "at most 4 workers", "drift at most 1 frame", "8 to 10 visual changes per 10 s", not "a few", "tight", "punchy". A default number the reader can tune beats a word every reader interprets differently.
- **No tool lock-in.** No product, model or paid service names in skills, agents, templates or docs. Write "speech-to-text", "a render", "a generated clip", "the editor". The CLI stays on the Python 3.9+ standard library.
- **Same words everywhere.** Use the glossary: lead, worker, reviewer, researcher, contract, board, task card, handoff note, gate report, check, lesson, rejection, shelf, queue, approval checkpoint. Statuses are `todo`, `in-progress`, `review`, `done`, `blocked`.
- **Exact commands.** Every command in a skill is written in full, as the agent will run it: `python3 .atelier/bin/atelier.py <command>`. Only the `start` skill refers to the plugin's own copy of the script, before `init`.
- **Plain, direct English.** Short sentences. Imperative steps. No hype.
- **Original text.** Do not cite or name any outside source, person, channel or brand as inspiration.
- **Consistent defaults.** If you change a default (questions per round, maximum parallel workers, draft cost), change it in every skill, agent and doc that mentions it, in the same pull request.

## The repository dogfoods the method

Work on atelier-video is run with atelier-video. For anything bigger than a small fix:

1. The lead of the change writes a contract and a board in `.atelier/` of their own checkout (`.atelier/` is in `.gitignore`, so it is not committed).
2. Each piece has a task card with a numeric quality bar, for example "skill under 250 lines, `lint_repo.py` 0 problems, 0 failing tests".
3. Every piece is checked by someone other than its author before it merges. A maintainer's review counts as the gate; a self-review does not.
4. A mistake that reaches review twice becomes an automated check: in `tools/lint_repo.py`, in the unit tests, or in CI.

If you are unsure how to size or describe a change, open an issue and ask. A recommended answer in your question helps.

## Licence

By contributing you agree that your contribution is released under the repository's licence (see `LICENSE`).
