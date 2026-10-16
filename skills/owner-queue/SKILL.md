---
name: owner-queue
description: Use when the user runs /owner-queue, asks to create, attach to or check an Owner Queue, or gives the claude.ai URL of one. An Owner Queue is a per-workstream claude.ai page where the user answers everything that needs them; any session on that workstream reads the answers when nudged.
argument-hint: new "<title>" | <queue URL or title>
---

# Owner Queue

A queue is a claude.ai artifact, so this needs the Artifact and ArtifactData tools, which Claude Code has when signed in to claude.ai.

While this session works from a queue, anything that needs the user goes on the queue, and their answers there are their replies.

## `new "<title>"`

1. Run `python3 -I "${CLAUDE_SKILL_DIR}/scripts/render_page.py" '<title>'`. It prints the rendered page's path.
2. Publish it with the Artifact tool: that `file_path`, `capabilities: {"db": {}}`, `icon: "checklist"`, a one-sentence `description` naming the workstream, and no `url`.
3. `ArtifactData` `set` collection `config`, doc `page`: `{template: "owner-queue", workstream: "<title>", eyebrow: "<title> · since <YYYY-MM-DD>"}`, plus any `config/page` fields below that the workstream needs.

## `<queue URL or title>`

1. Resolve a title with Artifact `list` and `limit: 200`. If several match, ask which.
2. `get` `config/page`. `template: "owner-queue"` confirms the queue. A queue with `items` but no config doc is an older one: use it as it is, and don't write config without asking. Neither: say so and stop.
3. `list` `items` and `answers`, act on current answers.

## Rules

1. An answer's doc id is its item's id. It is current only if its `at` is at or after the item's `askedAt`; an older one belongs to an earlier round. Write `askedAt` in UTC as `date -u +%Y-%m-%dT%H:%M:%SZ` gives it: the page compares it as a string with its own `toISOString()` times, so a local offset misfiles answers.
2. Act on every current answer to an open item, within that item's choices. A note refines the chosen action. A note asking for anything beyond the item becomes a new open item for the user to confirm, never an action. A note asking for more context, or an answer that leaves the question partly open, reopens the same item with what was missing, so its earlier answers stay on it. Close a step item when its Done is picked, and a decision once it is acted on, with `outcome` saying what changed.
3. Anything that needs the user becomes or stays an open item: a decision, a step only they can take, a result to review, a correction to something they already approved. Put everything they need on the item, steps in `steps` as `{text, command}`; a step item also gets a `{key: "done", label: "Done", primary: true}` choice. A decision argues both sides: each of its choices carries `pros` and `cons`. Chat, reports and files never replace an item; cite them in `source`.
4. Every open item has a `priority` (1 first) and a one-sentence `priorityReason` saying what waiting costs.
5. Update an existing item rather than add a duplicate, and keep `waiting` items' `due` current. Pin every write with `if_version` from your read; on a conflict, re-read and redo.

## Reference

`items/<slug>`, written by Claude:

| Field | Shown as |
|---|---|
| `title`, `ref` | Heading, with `ref` (e.g. `S1`) above it |
| `status` | `open`: Your queue. `waiting`: Scheduled. `done`: Done, collapsed |
| `group` | Kind chip: `go`, `domain`, `yours`, `review`, `house`, or a config `kinds` key |
| `ask`, `pick` | The question, and "My pick" |
| `choices` | `[{key, label, primary?, pros?, cons?}]` buttons; `primary` is Recommended. `pros` and `cons` are lists of short sentences, shown per choice under the question. Omit `choices` for a note-only item |
| `input` | Label of the note box, default "Note (optional)" |
| `steps` | `[{text, command?}]`; each command gets a Copy button |
| `priority`, `priorityReason` | "Priority n of m" plus the reason; open items only |
| `askedAt` | Not shown; Rule 1 |
| `order` | Sort key for waiting and done items |
| `due` | Chip, e.g. "Oct 20" |
| `effort`, `undo`, `unblocks`, `outcome` | Labelled rows |
| `source` | "Source: …" line |
| `history` | `[{choiceLabel, note, at}]`, oldest first, each an "Earlier answer" line |

Text between backticks in `ask`, `pick`, `pros`, `cons`, step text, the labelled rows, `lede` and `footer` renders as code.

`answers/<item id>`, written by the page: `{choice, choiceLabel, note, at}`. Read them; never write them.

`config/page`, written by Claude, applied live without a republish:

| Field | Effect |
|---|---|
| `template` | Always `"owner-queue"`; how attaching recognizes a queue |
| `workstream` | The workstream's name |
| `eyebrow` | Small line above the title |
| `lede` | Replaces the intro paragraph |
| `footer` | Array of paragraphs replacing the footer; `[]` hides it |
| `kinds` | `{key: label}`, added to or overriding the default kinds |
| `bulk` | `{kind, label?}`: a button accepting every pending primary choice of that kind, shown when two or more are pending |
| `savedText`, `pendingText` | Replace the save confirmation, and "answered, waiting for Claude" in the tally |

## Recipes

Write with one `batch`, each entry for an existing doc pinned with its `if_version`.

- Add: `{op: "set", collection: "items", doc_id: "<slug>", data: {title, ask, choices, group, status: "open", askedAt, priority, priorityReason, …}}`, unpinned since it creates.
- Close: `{op: "update", …, data: {status: "done", outcome, undo, order, priority: {"__delete__": true}, priorityReason: {"__delete__": true}}}`.
- Reopen: `status: "open"`, a new `ask`, `askedAt` now, a `priority` and `priorityReason`, and the answer's `{choiceLabel, note, at}` appended to `history`. Leave the answer doc; the page's next answer replaces it.

## Changing the page code

The template is `${CLAUDE_SKILL_DIR}/assets/owner-queue.html`; editing it changes only queues published afterwards. To update a published queue, with the user's go-ahead: Artifact `read` its URL, render with its `<title>` text and `--force`, then publish with that `file_path` and the queue's `url`, omitting `capabilities` and `icon` so both carry forward. Publishing without `url` creates a separate artifact and leaves the queue on its old code.
