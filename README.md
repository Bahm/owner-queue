# Owner Queue

A Claude Code skill that gives each workstream one claude.ai page where you, and anyone you share it with, answer everything Claude needs: decisions with each option argued for and against, steps only you can take, and results to review. Questions run most important first, and each says what waiting on it costs. Answers save as you type. A session doesn't check the page on its own: once you've answered, tell it so, and it takes your answers in and acts on them. Its status reports land on the same page.

Maintained at [Bahm/owner-queue](https://github.com/Bahm/owner-queue), forked from [xbahm/owner-queue](https://github.com/xbahm/owner-queue) 1.0. Each release's commit message starts with its version (`2.24.3: …`), so `git log` is the change history.

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

To update, run `claude plugin marketplace update owner-queue`, then `claude plugin update owner-queue@owner-queue`, and restart the sessions that use it. A session that owns a queue republishes it to bring its page up to date.

## Use

- `/owner-queue new "Website Launch"` publishes a new queue.
- `/owner-queue <queue URL or title>` attaches a session to a queue and acts on the current answers.
- `/owner-queue migrate <queue URL>` moves a 1.x queue onto 2.0, at the same address.

If another command already uses the name, run it as `/owner-queue:owner-queue`.

## The page

- **Needs you, in person:** steps only you can take, shown only once they're ready. Each has what you'll need, numbered steps with Copy buttons, and a prompt to paste into the chat.
- **The three most urgent decisions**, then **Other open questions**, each question with "Priority n of m" and why. A question marked Blocking, because work waits on its answer, comes first; one marked Low priority comes after the rest.
- **Each question** shows what you need to decide: the question, the context that decides it, and its options. Every option shows its pros and cons and its cost to build. One is marked Recommended, and a second opinion that disagrees can carry its own badge. What a careful reader might check, such as how a number was found or the sources, folds under "More detail".
- **Panels:** for example a playable test build, or files to download, one by one or as a zip.
- **Scheduled**, **Anything else** (free text, as long as you like; it stays at the bottom of the screen while you read the questions), **For information** (Claude's news, 48 hours of it), and **Done**.
- **A sticky bar** with progress, Expand all and Collapse all, Submit answers, Ping me on updates (each queue can have its own sound), and Copy all answers.
- **Links:** a question's number anywhere on the page (G51) links to it. On a phone or tablet, a tap opens a preview of that question under the link.
- **Other people:** answers from people you share the queue with show beside yours, under their claude.ai names. A question can say who decides it: you, or collaborators. A question for someone else is yellow where your own are green.
- **Asking again:** when Claude re-asks a question, the earlier answers move under Previous answers. A question asked again after your note opens with your note and Claude's reply to it.
- **Times** show in each viewer's own time zone.

## Submit and waking a session

Answers count once their writer presses Submit, yours included: until then Claude treats them as still being written and leaves them, unless you ask it to take them in anyway.

By default, Submit wakes nothing: you tell a session. Two flags, set per queue, change that:

- `--unsafe-unattended-wake`: your submit wakes the session with nobody at the laptop.
- `--unsafe-collaborator-wake`, together with the first: anyone's submit wakes it.

The waking is done by `queue_watch.py`, which reads the copy of the queue open in Claude Desktop on your laptop. It counts only marks from the queue's own page. Before acting, the session checks that the live page is still the version it published.

## How it works

- `skills/owner-queue/scripts/queue.py` is the session's tool. It writes each change to the store as files and prints the ArtifactData `batch` that sends them, so the queue's content stays out of the conversation. It checks every question against the rules in SKILL.md (one Recommended, both sides argued, a priority and a reason, real timestamps, no pasted-in pictures, only fields the page shows), counts the words a question shows, and lists the checks it can't make.
- `skills/owner-queue/assets/owner-queue.html` is the page. Content lives in the artifact's store: one record per question and one per For information entry, plus settings, receipts, and each person's answers under their own id. Changing a question never republishes the page.
- `skills/owner-queue/reference.md` documents every field, the store's access rules and the security model.
- `tests/` has the page tests (Playwright with Chromium, against a stand-in store) and the script tests: `python3 -m unittest discover tests`. The page tests need `pip install playwright` and `playwright install chromium`; without them, the page tests fail to import and the script tests still run.

## License

MIT
