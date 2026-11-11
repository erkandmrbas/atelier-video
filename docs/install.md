# Install atelier-video

atelier-video is a Claude Code plugin. The repository is a plugin marketplace named `atelier-video` that holds one plugin, also named `atelier-video`, in `plugins/atelier-video/`.

## Requirements

- Claude Code.
- Python 3.9 or newer, available as `python3` on your PATH. The CLI (`scripts/atelier.py`) uses the standard library only; there is nothing to `pip install`.
- Your own video tools. The plugin names none: the workers use whatever speech-to-text, editing, image, audio and render tools your project already has.
- Git is optional. The method works without it; some checks you write later may use it.

Check Python:

```
python3 --version
```

On Windows, if `python3` is not found but `python` is, install Python from python.org with the "Add to PATH" option, or create a `python3` alias. The hooks and skills call `python3`.

## Install from inside Claude Code

```
/plugin marketplace add erkandmrbas/atelier-video
/plugin install atelier-video@atelier-video
```

The first command registers the repository as a marketplace named `atelier-video`. The second installs the plugin `atelier-video` from it. Restart Claude Code if it asks you to.

## Install from a shell

```
claude plugin marketplace add erkandmrbas/atelier-video
claude plugin install atelier-video@atelier-video
```

## Local development

To try a checkout without installing it, start Claude Code with the plugin folder:

```
git clone https://github.com/erkandmrbas/atelier-video.git
cd your-video-project
claude --plugin-dir /path/to/atelier-video/plugins/atelier-video
```

From the root of the atelier-video repository itself, `claude --plugin-dir ./plugins/atelier-video` works too. Changes to skills take effect in the next session.

## What you get

- 9 skills, called as `/atelier-video:<name>`: `start`, `interrogate`, `board`, `contract`, `dispatch`, `gate`, `draft-first`, `lessons`, `profile-video`. You normally run only `/atelier-video:start`; it always loads `profile-video` and calls the others in order.
- 3 subagents: `atelier-video:worker` (builds one task card, for example one segment), `atelier-video:reviewer` (measures it and writes the gate report), `atelier-video:researcher` (looks before anyone builds; writes no files).
- 3 hooks, active only in projects that have a `.atelier/` folder:
  - **SessionStart** prints the board summary, integrity problems and the 10 most recent rejections at the top of each session.
  - **Stop** blocks the session from ending while a task is marked `done` without a passing gate, or while a lesson has repeated without a check.
  - **SubagentStop** blocks a worker whose final message names a task that is `in-progress` or `review` and has no complete handoff note.

## Verify the install

1. Make an empty folder and open Claude Code there:

   ```
   mkdir atelier-try && cd atelier-try
   claude
   ```

2. Run `/atelier-video:start` and give it a small job, for example "cut a 20-second vertical clip with burned-in captions from input/talk.mp4".
3. The lead should run `init` and then start asking questions, each with a recommended answer.
4. In a shell in the same folder:

   ```
   ls .atelier
   python3 .atelier/bin/atelier.py status
   ```

   You should see `bin`, `board.md`, `checks`, `contract.md`, `gates`, `handoffs`, `lessons.md`, `rejections.md`, `shelf.md` and `tasks`, and `status` should print `No tasks yet.` followed by `Problems: none` until the lead writes the first card.

`/plugin` lists the installed plugin, and the skills appear as `/atelier-video:` in the command menu.

## Update

From inside Claude Code:

```
/plugin marketplace update atelier-video
```

From a shell:

```
claude plugin marketplace update atelier-video
```

Then reinstall or update `atelier-video@atelier-video` from `/plugin` if your version does not update installed plugins automatically.

Existing projects keep their own copy of the CLI in `.atelier/bin/`. To give a project the new CLI and templates, run `init` from the updated plugin inside that project:

```
python3 "$(find ~/.claude -path "*atelier-video*/scripts/atelier.py" | head -1)" init
```

Without `--force`, `init` refreshes `.atelier/bin/` and keeps your contract, board, lessons, rejections and shelf. `--force` overwrites those five files with blank templates; do not use it on a running job.

## Uninstall

From inside Claude Code:

```
/plugin uninstall atelier-video@atelier-video
/plugin marketplace remove atelier-video
```

From a shell:

```
claude plugin uninstall atelier-video@atelier-video
claude plugin marketplace remove atelier-video
```

Uninstalling never touches your projects. Each project's `.atelier/` folder and your global rejection log at `~/.atelier/rejections.md` stay where they are; delete them yourself if you no longer want them.
