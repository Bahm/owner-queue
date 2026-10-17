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
- **Scheduled**, **Anything else** (free text, as long as you like), **For information** (Claude's status, 48 hours of it), and **Done**.
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

## License

MIT
