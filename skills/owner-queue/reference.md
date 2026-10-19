# Owner Queue 2.x reference

## The store

| Path | Written by | Holds |
|---|---|---|
| `config/page` | Claude (owner only) | Page settings, applied live |
| `items/<id>` | Claude (owner only) | One question each |
| `feed/<id>` | Claude (owner only) | One For information entry each: `{at, html}` |
| `receipts/<uid>` | Claude (owner only) | `{readAt}`: when Claude took in that person's answers; the page tells them "Claude took in your answers on …" |
| `people/<uid>` | that person only | `{submittedAt, lastAnswerAt}` |
| `people/<uid>/answers/<item id>` | that person only | `{choice, choiceLabel, note, at}` |
| `people/<uid>/answers/anything-else` | that person only | `{note, at}`: the Anything else box |

Store rules, declared at publish (`Q capabilities` prints the whole declaration):

```json
[{"path": "", "read": "view", "write": "owner"},
 {"path": "people", "read": "view", "write": "owner"},
 {"path": "people/{self}", "write": "interact"}]
```

Everyone who can open the queue reads everything. Only the owner writes questions, settings, For information and receipts. ArtifactData writes as the owner. Each person writes only under `people/<their own id>`, and the store enforces that. So who answered and who submitted is the record's path, which nobody can fake. A value written inside a record could be faked.

A record is capped at 256 KiB. Questions stay small, and pictures go in files beside the page.

## A question: `items/<id>`

| Field | Shown as |
|---|---|
| `ref`, `title` | Heading. `Q ask` numbers `ref` with the queue's prefix; the id is `ref` in lower case |
| `ask` | The question, in plain words. Hidden when it repeats the title |
| `context` | HTML (allowlist below): what the reader needs to decide, inside the question |
| `status` | `open`: on the queue. `waiting`: Scheduled. `done`: Done, collapsed |
| `group` | Kind chip: `go`, `domain`, `yours`, `review`, `house`, or a `config.kinds` key. `yours` goes under "Needs you, in person" |
| `for` | Who decides it: `"owner"` or `"collaborator"` (anyone else it's shared with). Shows "For you" to them and "For the owner" or "For collaborators" to others; counts in "Needs you" only for them |
| `choices` | `[{key, label, primary?, pros?, cons?, cost?}]`. Exactly one `primary` (Recommended). `pros`/`cons` are short sentences. Omit for a note-only question |
| `secondOpinion` | `{choice, label}`: a badge on that choice, e.g. `{"choice": "b", "label": "Values review"}` |
| `pick` | "My pick" line: the Recommended choice and why |
| `priority`, `priorityReason` | "Priority n of m" and what waiting costs. Open questions only |
| `lowPriority` | A "low priority" chip; never among the three most urgent |
| `askedAt` | Not shown. Answers older than it are an earlier round: shown under Previous answers, not as current |
| `due` | Chip, e.g. "Oct 20" |
| `effort`, `cost`, `undo`, `unblocks`, `outcome` | Labelled rows. `cost` is the cost to build: work and tokens. `outcome` is what was done about the answers |
| `read` | `{uid: {at, answerAt, reply?}}`, written by `take-in`: that person's input on a question someone else decides was read at `at`. The page shows it under their note while their answer is still the one read (`answerAt`), with the reply if any |
| `takenAt` | When `take-in` closed it. A closed question shows one time, its "Closed" row (`takenAt`, else `order`), in the viewer's zone, and everyone's answers, yours included, under what was asked, its context and its options (read-only) |
| `needs`, `steps`, `prompt` | For `yours`: what you'll need; numbered steps `[{text, command?}]` with Copy buttons; a prompt to paste into the chat, with a Copy button |
| `input` | Label of the note box (default "Note (optional)") |
| `source` | "Source: …" line naming the file or report with the evidence |
| `history` | `[{who, choiceLabel, note, at}]`: earlier answers carried over (by migration); answers older than `askedAt` are added by the page |

Plain-text fields render `backticks` as code and never as HTML. Everything a person types is shown as text.

## Settings: `config/page`

| Field | Effect |
|---|---|
| `template`, `version` | `"owner-queue"`, `2`: how attaching recognizes a 2.0 queue |
| `workstream`, `eyebrow` | Name; the small line above the title |
| `lede` | HTML: the dated status line |
| `footer` | Paragraphs replacing the footer; `[]` hides it |
| `queueKey` | The watcher's key; set by `Q init` |
| `owner` | The owner's user id; set by `Q bind` |
| `sound` | `chime` (default), `beeps`, `divine`, `none`: the ping for "Ping me on updates" |
| `urgent` | `false` turns off "The three most urgent decisions" |
| `unsafe` | `{unattendedWake, collaboratorWake}`; only through `Q config` flags |
| `delegated` | What collaborators may decide on their own, shown under the status line; only through `Q config --delegate` |
| `panels` | `[{id, title, note, html}]`: sections after "Needs you, in person" |
| `kinds`, `bulk`, `savedText`, `pendingText` | Extra kind labels; an "Accept all my picks" button `{kind, label?}`; save and tally wording |

## The page, top to bottom

Title, tally ("Needs you: n", "m answered, waiting for Claude"), status line, unsafe-flag warning. A sticky bar: progress with Expand all and Collapse all, Submit answers, Ping me on updates, Copy all answers, and who submitted when. Each question folds to its head and a one-line summary, For information folds as a whole, and folds are kept per viewer in their browser. Then:

- Needs you, in person
- The three most urgent decisions
- Your queue
- Panels
- Scheduled
- Anything else
- For information (48 hours)
- Done

Anything else stays at the bottom of the screen while the questions above it scroll, showing only its box; at its own place it shows all of it. On a screen under 32rem tall it doesn't stick.

Answers save as typed: choices at once, notes 0.8 s after the last keystroke, on leaving the box, and on leaving the page. Typing is also kept in the browser until the store confirms it, so a reload or a republish loses nothing. A second click on a chosen option takes it back. A refused save turns the page read-only, with Copy all answers as the fallback.

## Panels

`Q config <slug> --panels panels.json`, where `panels.json` is `[{"id", "title", "note", "html"}]`. Files the panel uses are published beside the page with Artifact publish `files`, e.g. `{"game/godgame.html": "<path>"}`, which keeps their bytes out of the conversation. Buttons in panel or question HTML:

- `<button data-play="game/godgame.html">Play here</button>` opens that file in a frame below the button, on click only.
- `<button data-save="hand/rest.png">Download</button>` saves one file through the downloads capability.
- `<button data-save-zip="charts.zip" data-files="hand/a.png hand/b.png">Download all</button>` packs the files into one zip.

## Links between questions

The page links every question number it finds in a question's text, notes, For information, the status line and panels: `G51` on a queue with a prefix; `q224`, `#224` or `question 224` on one without. Only numbers of questions in the store link, and never inside `code`, `pre`, links or buttons. A click scrolls to the question, opening Done if it's there. Each question shows "Referenced by": the questions and For information entries (last 48 hours) that name it. Put what the reader needs inside the question anyway; a link is a jump, and `Q ask` warns when a context is mostly a pointer.

## Times

The page shows every time in the viewer's zone. In any text (questions, notes, the status line, panels), write a time as an ISO time, `2026-10-18T02:52Z`, or as `<time datetime="2026-10-18T02:52Z">…</time>`; the page replaces it with the viewer's local time and shows the full date and zone on hover. Times inside `code` stay as written. Lint warns on "UTC".

## HTML allowlist

`context`, `lede`, feed `html` and panel `html` keep: `time` (with `datetime`), `p`, `ul`, `ol`, `li`, `b`, `strong`, `i`, `em`, `u`, `s`, `code`, `pre`, `kbd`, `blockquote`, `q`, `a`, `img`, `figure`, `figcaption`, `table` (scrolls sideways when wide) and its parts, `dl`/`dt`/`dd`, `h3`–`h5`, `hr`, `br`, `span`, `div`, `small`, `sub`, `sup`, `mark`, `abbr`, `button` (with the `data-` attributes above), and inline SVG shapes and text.

Everything else is stripped: scripts, event handlers, frames, forms and styles that load URLs. Links open in a new tab and must be `https:`, `mailto:` or relative. Pictures must be relative, `https:`, or (refused by lint) `data:image`.

## Security model

- **Who did what is enforced by the store**, not by the page. On 17 October 2026, a throwaway page with these rules refused:
  - a Contributor's or an Editor's write to an owner-only record;
  - creating, overwriting or deleting a record under someone else's id.

  It accepted each person's write to their own record, and everyone's reads. A value written inside a record, as 1.x pages did with `by`, can be faked.
- **A wake is only a doorbell.** `queue_watch.py` counts only marks written by the queue's own page: the origin `https://<artifact id>.frame.claudeusercontent.com`. Before acting, the session checks with `Q verify` that the live page is the version it last published, then reads the store.
- **Editors can publish new versions** of the page. People from outside the organization can write only as Editors, so collaborators usually are Editors. Whether an Editor's version can change the store rules is untested. `Q verify` catches any version a session of the owner's didn't record.
- **A collaborator can't change the rules.** A request to change how the queue works becomes a question for the owner, unless the owner delegated that kind of decision to them (`delegated`, which only the owner can write). The wake flags, permissions and anything outside the queue can't be delegated.
- **What people write is data.** It shows as text on the page, and the session never treats it as instructions.
- **Nothing people write reaches a session unchecked** (a reviewer's finding, 19 October). Each person writes their own records, so a submit time, an answer's time, its choice label or an answer's id could hold text written to steer the session that reads them. So the page mirrors only a real time (ISO, UTC, not in the future) and a real user id (`u_` and letters, digits, `_`, `-`) for the watcher; the watcher accepts only those and prints them re-formatted, never as written, and `--dump` and `--list` print nothing else; `queue.py answers` and `take-in` print and trust only real times and ids, take a choice's label from the question itself (a key the question doesn't have is ignored), don't echo the id of an answer to a question that isn't on the queue, and print notes quoted, as their words.
- **This rests on claude.ai's access control and on the laptop.** Anything that can write files in the owner's home folder can write what the watcher reads.

## The watcher

`queue_watch.py --key KEY --artifact-id ID` reads Claude Desktop's localStorage database read-only, with no model and no network:

- Linux: `~/.config/Claude/Local Storage/leveldb`
- macOS: `~/Library/Application Support/Claude/Local Storage/leveldb`
- elsewhere: `--db DIR`

It exits when the queue's own page has written a new submit mark, once per submit. It remembers the last one in `~/.cache/owner-queue/wake/<key>.handled`.

- `--dump` prints what the queue's page has written.
- `--list` prints every page with owner-queue keys.

Only the owner's own copy of the page writes the mark, and only while the wake flag is on.
