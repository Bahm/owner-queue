# Owner Queue

A Claude Code skill that gives each workstream one claude.ai page where you, and anyone you share it with, answer everything Claude needs: decisions with each option argued for and against, steps only you can take, and results to review. Questions run most important first, and each says what waiting on it costs. Answers save as you type. Claude takes them in and acts on them, and its status reports land on the same page.

This is version 2.0, maintained at [Bahm/owner-queue](https://github.com/Bahm/owner-queue) and forked from [xbahm/owner-queue](https://github.com/xbahm/owner-queue) 1.0.

## Requirements

- Claude Code signed in to claude.ai, with the Artifact and ArtifactData tools. A queue is a private artifact with a data store, so without those tools the skill can't publish one.
- `python3`, standard library only.

## Install

In a terminal Claude Code session:

```
/plugin install owner-queue --marketplace Bahm/owner-queue
```

Answer `y` to add the marketplace, then pick a scope. The desktop app's Code tab doesn't offer `/plugin`, but a plugin installed at user scope from a terminal loads there too.

From a shell, `claude plugin install owner-queue --marketplace Bahm/owner-queue` does the same at user scope.

## Use

- `/owner-queue new "Website Launch"` publishes a new queue.
- `/owner-queue <queue URL or title>` attaches a session to a queue and acts on the current answers.
- `/owner-queue migrate <queue URL>` moves a 1.x queue onto 2.0, at the same address.

If another command already uses the name, run it as `/owner-queue:owner-queue`.

## The page

- **Needs you, in person:** steps only you can take, shown only once they're ready. Each has what you'll need, numbered steps with Copy buttons, and a prompt to paste into the chat.
- **The three most urgent decisions**, then **Your queue**, each question with "Priority n of m" and why. Every option shows its pros and cons and its cost to build. One is marked Recommended, and a second opinion that disagrees can carry its own badge.
- **Panels:** for example a playable test build, or a zip of reference files to download.
- **Scheduled**, **Anything else** (free text, as long as you like; it stays at the bottom of the screen while you read the questions), **For information** (Claude's status, 48 hours of it), and **Done**.
- **A sticky bar** with progress, Submit answers, Ping me on updates (each queue can have its own sound), and Copy all answers.
- **Other people:** answers from people you share the queue with show beside yours, under their claude.ai names. A question can say who decides it: you, or collaborators.
- **Asking again:** when Claude re-asks a question, the earlier answers move under Previous answers.

## Submit and waking a session

By default, Submit marks your answers as done and wakes nothing: you tell a session. Two flags, set per queue, change that:

- `--unsafe-unattended-wake`: your submit wakes the session with nobody at the laptop.
- `--unsafe-collaborator-wake`, together with the first: anyone's submit wakes it.

The waking is done by `queue_watch.py`, which reads the copy of the queue open in Claude Desktop on your laptop. It counts only marks from the queue's own page. Before acting, the session checks that the live page is still the version it published.

## How it works

- `skills/owner-queue/scripts/queue.py` is the session's tool. It writes each change to the store as files and prints the ArtifactData `batch` that sends them, so the queue's content stays out of the conversation. It checks every question against the rules in SKILL.md (one Recommended, both sides argued, a priority and a reason, real timestamps, no pasted-in pictures) and lists the checks it can't make.
- `skills/owner-queue/assets/owner-queue.html` is the page. Content lives in the artifact's store: one record per question and one per For information entry, plus settings, receipts, and each person's answers under their own id. Changing a question never republishes the page.
- `skills/owner-queue/reference.md` documents every field, the store's access rules and the security model.
- `tests/` has the page tests (Playwright, against a stand-in store) and the script tests: `python3 -m unittest discover tests`.

## Changes in 2.0

- Your answers live under your own id, which the store enforces, so who answered can't be faked. Collaborators answer beside you.
- New sections: Needs you in person, The three most urgent decisions, Anything else, For information, and panels.
- Submit answers, receipts, and the two unsafe wake flags.
- Multi-line notes kept in the browser until saved, Copy all answers, Previous answers, and a ping on updates.
- Pictures and builds are files beside the page, never data pasted in.
- `queue.py` replaces `render_page.py`, and adds lint and migration from 1.x.

## Changes in 2.1

- A collaborator's request to change how the queue works goes to you as a question, unless you gave collaborators a standing permission for that kind of decision (`queue.py config --delegate`, shown on the page). The wake flags, permissions and anything outside the queue can't be delegated.
- Questions are for `"owner"` or `"collaborator"`; people show under their claude.ai names. `--person` and its role labels are gone.

## Changes in 2.2

- A question's number anywhere on the page (G51; on a queue without a prefix, q224, #224 or "question 224") links to that question, opening it under Done if it's there. Each question lists the questions and For information entries that name it, under "Referenced by". Numbers in code don't count.
- Lint warns when a question's context is mostly a pointer to another question: the reader needs what they decide on inside the question.
- You answer on the queue, even when you asked in chat: a request for options or pros and cons becomes questions there (2.1.4).

## Changes in 2.3

- Each question folds to its number, title and a one-line summary (your answer, or its outcome once done); click the arrow or the title. For information folds as a whole. Expand all and Collapse all sit by the progress bar, and also open or close Done. Open questions start unfolded, done ones folded, and each viewer's folds are kept in their own browser.
- "Previous answers" starts closed, showing how many there are, and someone else's long note (a pasted report) shows its first six lines with "Show all" (2.3.2; the B4B collaborator asked).
- A note alone answers a question with choices (2.3.3).

## Changes in 2.4

- `queue.py take-in` is the housekeeping batch, run first when answers arrive: it closes every answered question, writes receipts, saves and clears Anything else (pinned, so nothing typed since is lost) and adds a For information line. The wake message names it as the step before acting (the owner's O11).
- A closed question shows everyone's answers, yours included, with the time it was closed; `take-in --outcome REF=TEXT` puts what Claude will do in its outcome instead of copying the answer there (2.5.0, the owner's O12).
- Only the session that owns a queue publishes it (the owner). `queue.py answers` and `status` say when a newer page is available for it (2.5.1).
- Done lists the most recently closed question first (2.5.2; the B4B collaborator asked).
- `take-in --pins` pins each write to the version the listing showed; the store refuses an unpinned write to an existing record (2.5.3; the roc-ui session's report).
- Answered questions show only under Done, with one time each, when they were closed; For information is for news that isn't about a question. `take-in` writes a line there only for a cleared Anything else (2.6.0, the owner's O14).
- For information stays, for news only. `take-in` writes nothing there; the receipt reads "Claude took in your answers on <date, time>" (2.6.1, the owner's O15).
- Every time on the page is the viewer's own: an ISO time (`2026-10-18T02:52Z`) or `<time datetime>` in any text is shown in each viewer's zone, and lint warns on "UTC" (2.7.0).
- A collaborator's note on a question someone else decides shows as read once `take-in` has read it, with an optional reply under it (`take-in --reply REF=TEXT`; 2.8.0, the owner's O16).
- Security (2.8.1, a reviewer's finding): only a real time and user id pass from the store to a session. The page mirrors and the watcher accepts and prints only those, and `queue.py answers` and `take-in` use the question's own labels and quote notes as their words. A submit time, a label or an answer id written to steer the session never reaches it.
- Anything else stays at the bottom of the screen while you read the questions, as a box to type in; at its own place it shows all of it (2.9.0, the owner).
- A question number inside an option's pros and cons links too, and Claude's own `#item-…` links stay in the tab. A closed question keeps what was asked, its context and its options (read-only), and drops its note box; nothing the page hides shows any more, such as "Previous answers (0)" (2.9.1, the owner).
- Re-asking a closed question puts it back on the queue: `queue.py ask --reask` writes `status: "open"` (unless the item file sets a status) and removes what closing wrote, `takenAt` and `order`, and `outcome` and `undo` unless the file sets them. Before, it stayed under Done, read-only, so nobody could answer the new round (2.9.2, a bug report and a reviewer's finding).
- `queue.py ask --version N` without `--reask` warns when the item file carries a status: it would send it as it is, and an "open" on a closed question puts it back with its old outcome (2.9.3, xbahm's finding; the owner's O19).
- `queue.py ask` refuses an open question with fewer than two choices: every open point is a decision with options. Only a step only you can take (`group: "yours"`) goes without (2.10.0, the owner).
- `queue.py ask` refuses `pros` or `cons` that aren't a list of sentences, or that hold an empty one: the page showed nothing for a single text, and lint let it through (a number or `true` crashed it). The time lint no longer warns on an ISO time with seconds, such as `2026-10-19T08:19:42Z`, and still warns on a bare `08:19:42Z` (2.10.1, xbahm's finding; Bahm's review).
- Lint catches what the page would silently drop: a field name the page doesn't read (it suggests the one meant, e.g. `options` for `choices`), and `choices`, `steps` or `history` that aren't lists of objects, which crashed lint before. The page shows ISO times with up to six decimals in each viewer's zone, as Python writes them (2.11.0, the owner's O21; the B4B session's B305).
- Lint checks each plain field on its own, so a `<` in one field and a `>` in a later one no longer hide the text between them from the time check, and `queue.py answers` prints titles and choice labels whole (2.11.1, xbahm's finding; the owner's O22).
- A session reads the answers only when the owner says they're ready, or when the watcher wakes it. It no longer checks on its own after a resume or now and then: a session that compacted every few minutes read the queue after almost every compaction, 82 times in a day, and wrote "No new answers" about 60 times (2.12.0, xbahm).
- `queue.py answers` and `take-in` wait for a collaborator's Submit: an answer they saved since their last Submit is still being written, so it's listed as "still writing", its question stays open, and their Anything else isn't cleared. Your own answers count without Submit, and `--unsubmitted <uid>` takes one in when you ask (2.13.0, the owner's O26).
- A panel download that fails says why, with the platform's code (e.g. `extension_not_enabled`), instead of "Downloading isn't available here" for every failure, and a file that doesn't load says so (2.13.1, the God Game session's report).
- A link to a question lands on it when the host sizes the queue's frame to the page: a link into Done grew the page after scrolling, and the host's resize undid the scroll. For two seconds after a link, the page scrolls to it again when the frame resizes, until you scroll yourself (2.13.2, the owner on God Game's G111).

## License

MIT
