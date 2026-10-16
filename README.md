# Owner Queue

A Claude Code skill that gives each workstream one claude.ai page where you answer everything Claude needs from you: decisions, each choice argued with pros and cons; steps only you can take; and results to review. Items run most important first, and each says what waiting on it costs. Your answers save as you click. When you tell a session you've answered, it reads them and acts.

## Requirements

- Claude Code signed in to claude.ai, with the Artifact and ArtifactData tools. A queue is a private artifact with a data store, so without those tools the skill can't publish one.
- `python3`, standard library only, to render the page.

## Install

In a terminal Claude Code session:

```
/plugin install owner-queue --marketplace xbahm/owner-queue
```

Answer `y` to add the marketplace, then pick a scope. The desktop app's Code tab doesn't offer `/plugin`, but a plugin installed at user scope from a terminal loads there too.

From a shell, `claude plugin install owner-queue --marketplace xbahm/owner-queue` does the same at user scope. If your Claude Code doesn't recognize `--marketplace`, add the marketplace first: `/plugin marketplace add xbahm/owner-queue`, then `/plugin install owner-queue@owner-queue`.

## Use

- `/owner-queue new "Website Launch"` publishes a new queue for that workstream.
- `/owner-queue <queue URL or title>` attaches a session to an existing queue and acts on your current answers.

If another command already uses the name, run it as `/owner-queue:owner-queue`.

While a session works from a queue, it puts anything that needs you on the queue rather than asking in chat. Open the page, pick an answer, add a note if it needs one, then tell the session.

## How it works

- `skills/owner-queue/scripts/render_page.py` fills the queue's title into `skills/owner-queue/assets/owner-queue.html` and writes the page under `${XDG_CACHE_HOME:-~/.cache}/owner-queue/`. Claude publishes that file as the artifact.
- The artifact's store holds `items`, written by Claude; `answers`, written by the page; and `config/page`, settings the page applies live. `skills/owner-queue/SKILL.md` documents every field.
- Editing the template changes only queues published afterwards. SKILL.md describes how to move an existing queue onto it.

## License

MIT
