#!/usr/bin/env python3
"""queue.py and queue_watch.py. Run: python3 -m unittest tests/test_scripts.py"""
import contextlib, importlib.util, io, json, os, re, subprocess, sys, tempfile, unittest
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills/owner-queue/scripts"
QUEUE = SCRIPTS / "queue.py"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iso(minutes_ago=0.0):
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


GOOD = {"title": "Height level", "ask": "What I'm asking: how many metres is one level?", "group": "domain",
        "priority": 1, "priorityReason": "Rocks come next, and they'd need tuning again.", "pick": "16 m.", "cost": "an hour",
        "choices": [{"key": "16", "label": "16 m", "primary": True, "pros": ["Mountains read."], "cons": ["Steeper."]},
                    {"key": "8", "label": "8 m", "pros": ["Gentle."], "cons": ["Flat-looking."]}]}


class QueueScript(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "XDG_CACHE_HOME": str(self.tmp)}

    def run_q(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(QUEUE), *map(str, args)], env=self.env, capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def writes(self, r):
        lines = [l for l in r.stdout.splitlines() if l.startswith("[{")]
        return [w for l in lines for w in json.loads(l)]

    def item_file(self, body):
        f = self.tmp / f"item-{len(list(self.tmp.glob('item-*')))}.json"
        f.write_text(json.dumps(body))
        return f

    def init(self, prefix="G"):
        self.run_q("init", "Test <Queue>", "--slug", "t", "--prefix", prefix)
        self.run_q("bind", "t", "--url", "https://claude.ai/artifact/X", "--artifact-id",
                   "11111111-2222-3333-4444-555555555555", "--owner", "u_owner", "--version", "v1")

    def test_init_renders_and_escapes_title(self):
        self.init()
        page = (self.tmp / "owner-queue/t/page.html").read_text()
        self.assertIn("<title>Test &lt;Queue&gt;</title>", page)
        self.assertNotIn("__QUEUE_TITLE__", page)
        state = json.loads((self.tmp / "owner-queue/t/state.json").read_text())
        self.assertFalse(state["config"]["unsafe"]["unattendedWake"])
        self.assertTrue(re.fullmatch(r"t-[0-9a-f]{8}", state["queueKey"]))

    def test_ask_numbers_and_stamps(self):
        self.init()
        r = self.run_q("ask", "t", self.item_file(GOOD))
        w = self.writes(r)[0]
        self.assertEqual((w["op"], w["collection"], w["doc_id"]), ("set", "items", "g1"))
        body = json.loads(Path(w["file_path"]).read_text())
        self.assertEqual(body["ref"], "G1")
        self.assertRegex(body["askedAt"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        r = self.run_q("ask", "t", self.item_file(GOOD))
        self.assertEqual(self.writes(r)[0]["doc_id"], "g2")
        r = self.run_q("ask", "t", self.item_file({**GOOD, "ref": "G1"}), "--version", "4")
        w = self.writes(r)[0]
        self.assertEqual((w["op"], w["if_version"]), ("update", 4))
        self.assertNotIn("askedAt", json.loads(Path(w["file_path"]).read_text()), "an edit keeps the question's answers")
        r = self.run_q("ask", "t", self.item_file({**GOOD, "ref": "G1"}), "--version", "5", "--reask")
        self.assertIn("askedAt", json.loads(Path(self.writes(r)[0]["file_path"]).read_text()))

    def test_lint_errors_block_the_write(self):
        self.init()
        bad = {**GOOD, "context": '<img src="data:image/png;base64,AAAA">',
               "choices": [{**GOOD["choices"][0]}, {**GOOD["choices"][1], "primary": True}]}
        bad.pop("priorityReason")
        r = self.run_q("ask", "t", self.item_file(bad), ok=False)
        self.assertNotEqual(r.returncode, 0)
        for text in ("data: URI", "2 Recommended", "priorityReason"):
            self.assertIn(text, r.stdout)
        self.assertEqual(self.writes(r), [])
        future = {**GOOD, "askedAt": iso(-30)}
        r = self.run_q("lint", self.item_file(future), ok=False)
        self.assertIn("in the future", r.stdout)
        warn = {**GOOD, "choices": [GOOD["choices"][0], {"key": "8", "label": "8 m"}]}
        r = self.run_q("lint", self.item_file(warn))
        self.assertIn("argue both sides", r.stdout)
        self.assertIn("Lint can't check these", r.stdout)
        yours = {"title": "Plug in the phone", "ask": "Plug it in?", "group": "yours", "priority": 2,
                 "priorityReason": "x", "steps": [{"text": "Run", "command": "./phone.sh"}]}
        r = self.run_q("lint", self.item_file(yours))
        self.assertIn("relative path", r.stdout)

    def test_flags(self):
        self.init()
        r = self.run_q("config", "t", "--unsafe-collaborator-wake", ok=False)
        self.assertIn("needs --unsafe-unattended-wake", r.stderr)
        r = self.run_q("config", "t", "--unsafe-unattended-wake", "--unsafe-collaborator-wake", "--version", "2")
        cfg = json.loads(Path(self.writes(r)[0]["file_path"]).read_text())
        self.assertEqual(cfg["unsafe"], {"unattendedWake": True, "collaboratorWake": True})
        self.assertIn("queue_watch.py --key t-", r.stdout)
        r = self.run_q("config", "t", "--safe", "--version", "3")
        cfg = json.loads(Path(self.writes(r)[0]["file_path"]).read_text())
        self.assertEqual(cfg["unsafe"], {"unattendedWake": False, "collaboratorWake": False})

    def test_delegate(self):
        self.init()
        r = self.run_q("config", "t", "--delegate", "how their own questions are worded", "--version", "2")
        cfg = json.loads(Path(self.writes(r)[0]["file_path"]).read_text())
        self.assertEqual(cfg["delegated"], "how their own questions are worded")
        for scope in ("turning on unattended wake", "downloads from the queue", "pushing to main", "anything the owner decides"):
            r = self.run_q("config", "t", "--delegate", scope, "--version", "3", ok=False)
            self.assertIn("can't be delegated", r.stderr, scope)
        r = self.run_q("config", "t", "--undelegate", "--version", "3")
        self.assertNotIn("delegated", json.loads(Path(self.writes(r)[0]["file_path"]).read_text()))

    def test_verify(self):
        self.init()
        self.assertIn("OK", self.run_q("verify", "t", "v1").stdout)
        r = self.run_q("verify", "t", "v9", ok=False)
        self.assertIn("STOP", r.stderr)
        self.run_q("published", "t", "v2")
        r = self.run_q("verify", "t", "v1", ok=False)
        self.assertIn("older version", r.stderr)

    def test_fyi_and_prune(self):
        self.init()
        r = self.run_q("fyi", "t", "<b>Merged</b>")
        w = self.writes(r)[0]
        self.assertEqual(w["collection"], "feed")
        self.assertRegex(json.loads(Path(w["file_path"]).read_text())["at"], r"Z$")
        r = self.run_q("fyi", "t", '<img src="data:image/png;base64,AA">', ok=False)
        self.assertIn("data: URI", r.stdout)
        self.assertIn('"where": [["at", "<"', self.run_q("prune", "t").stdout)
        w = self.writes(self.run_q("prune", "t", "f1=3", "f2=1"))
        self.assertEqual([(x["op"], x["doc_id"], x["if_version"]) for x in w], [("delete", "f1", 3), ("delete", "f2", 1)])

    def test_answers_summary(self):
        self.init()
        d = self.tmp / "dump"
        def put(path, body):
            p = d / f"{path}.json"; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(body))
        put("items/g1", {**GOOD, "ref": "G1", "status": "open", "askedAt": iso(60)})
        put("items/g2", {**GOOD, "ref": "G2", "title": "Second", "status": "open", "askedAt": iso(10)})
        put("people/u_des", {"submittedAt": iso(5)})
        put("people/u_des/answers/g1", {"choice": "16", "choiceLabel": "16 m", "note": "go", "at": iso(30)})
        put("people/u_des/answers/g2", {"choice": "8", "choiceLabel": "8 m", "note": "", "at": iso(20)})
        put("people/u_des/answers/anything-else", {"note": "A long report " * 100, "at": iso(5)})
        out = self.run_q("answers", "t", d).stdout
        self.assertIn("a collaborator (u_des): SUBMITTED, not yet read", out)
        self.assertIn("can't wake a session", out)
        self.assertIn("G1 Height level: 16 m", out)
        self.assertNotIn("G2", out, "an answer older than the question isn't current")
        self.assertIn("save it before clearing", out)
        self.assertIn("people/u_owner/answers", out, "it says what else to list")

    def test_receipt_and_clear_free(self):
        self.init()
        w = self.writes(self.run_q("receipt", "t", "u_des"))[0]
        self.assertEqual((w["op"], w["collection"], w["doc_id"]), ("set", "receipts", "u_des"))
        w = self.writes(self.run_q("clear-free", "t", "u_des", "--version", "7"))[0]
        self.assertEqual((w["collection"], w["doc_id"], w["if_version"]), ("people/u_des/answers", "anything-else", 7))

    def test_migrate_content_page(self):
        self.init()
        src = {"v": "x", "lede": "<b>16 October:</b> one decision.", "needs": "<p>Charts</p>",
               "sections": [{"id": "urgent", "title": "The three most urgent decisions", "items": [
                   {"id": "g58", "tag": "G58 · the farthest zoom", "title": "5.8 or 5.5 million?", "ctx": "<p>Measured.</p>",
                    "opts": [["55", "5.5 million", True], ["58", "Keep 5.8"]], "prev": [{"at": iso(500), "choice": "Simplify sooner", "note": "ok"}]}]},
                   {"id": "open", "title": "Open invitations (low priority)", "items": [
                    {"id": "g65", "tag": "G65 · time", "title": "Which features?", "ctx": "", "opts": [["ideas", "In the note"]]}]}],
               "fyi": [{"at": iso(10).replace(".000", ""), "html": "recent"}, {"at": iso(60 * 50), "html": "old"}]}
        f = self.tmp / "content.json"; f.write_text(json.dumps(src))
        ans = self.tmp / "old"; (ans / "answers").mkdir(parents=True)
        (ans / "answers/g58.json").write_text(json.dumps({"choice": "55", "note": "", "at": iso(30), "by": "u_des"}))
        r = self.run_q("migrate", "t", f, "--answers", ans)
        w = self.writes(r)
        items = {x["doc_id"]: json.loads(Path(x["file_path"]).read_text()) for x in w if x["collection"] == "items"}
        self.assertEqual(sorted(items), ["g58", "g65"])
        g58 = items["g58"]
        self.assertEqual((g58["ref"], g58["title"], g58["ask"]), ("G58", "The farthest zoom", "5.8 or 5.5 million?"))
        self.assertEqual(g58["choices"][0], {"key": "55", "label": "5.5 million", "primary": True})
        self.assertEqual([h["choiceLabel"] for h in g58["history"]], ["Simplify sooner", "5.5 million"])
        self.assertTrue(items["g65"]["lowPriority"])
        self.assertEqual(sum(1 for x in w if x["collection"] == "feed"), 1, "only the last 48 hours")
        self.assertIn("not taken in yet: G58", r.stdout)
        self.assertIn("panel", r.stdout)
        self.assertIn('"nextRef": "G66"', self.run_q("status", "t").stdout)
        (ans / "answers/free.json").write_text(json.dumps({"note": "Two things to consider.", "at": iso(600)}))
        w = self.writes(self.run_q("migrate", "t", f, "--answers", ans))
        carried = [x for x in w if x["collection"] == "people/u_owner/answers"]
        self.assertEqual([x["doc_id"] for x in carried], ["anything-else"], "the old Anything else is carried over")

    def test_migrate_page_html(self):
        self.init(prefix="")
        html_src = ('<p class="lede"><b>17 October:</b> two open.</p><script>\nconst FYI = [\n  {"at": "%s", "html": "x"},\n];\n'
                    'const SECTIONS = [{"id": "s", "title": "Protocol", "note": "", "items": [{"id": "q205", "tag": "6.8 · dev tools", '
                    '"title": "Check the tools by their answers?", "ctx": "<p>c</p>", "opts": [["ans", "By answers", true], ["all", "Everything"]]}]}];\n'
                    'const PC = {"q205": {"ans": "+ fewer false alarms. − timings unchecked.", "all": "+ complete. − flaky."}};\n'
                    'const VR = {"q205": "all"};   // the values review\n</script>') % iso(5).replace(".000", "")
        f = self.tmp / "page.html"; f.write_text(html_src)
        r = self.run_q("migrate", "t", f)
        items = {x["doc_id"]: json.loads(Path(x["file_path"]).read_text()) for x in self.writes(r) if x["collection"] == "items"}
        q = items["q205"]
        self.assertEqual(q["ref"], "205")
        self.assertEqual(q["choices"][0]["pros"], ["fewer false alarms."])
        self.assertEqual(q["choices"][0]["cons"], ["timings unchecked."])
        self.assertEqual(q["secondOpinion"], {"choice": "all", "label": "Values review"})
        self.assertIn('"nextRef": "206"', self.run_q("status", "t").stdout)


class Watcher(unittest.TestCase):
    ID = "796451f2-a470-4c13-93b9-96e12af2fd55"

    def setUp(self):
        self.w = load("queue_watch")
        self.origin = f"https://{self.ID}.frame.claudeusercontent.com/^0https://claude.ai"
        self.rows = []
        self.w.rows = lambda: iter(self.rows)

    def mark(self, seq, origin, ready, at, by="u_owner"):
        text = json.dumps({"ready": ready, "at": at, "by": by})
        self.rows.append((seq, origin, "owner-queue:k-1234:submitted", b"\x01" + text.encode("latin-1")))

    def test_only_the_queue_page_counts(self):
        self.mark(1, self.origin, False, None)
        self.mark(2, "https://00000000-0000-0000-0000-000000000000.frame.claudeusercontent.com/^0https://claude.ai", True, "2026-10-17T07:00:00.000Z")
        found = self.w.read_keys("owner-queue:k-1234:", self.w.origin_of(self.ID))
        self.assertFalse(json.loads(found["owner-queue:k-1234:submitted"][1])["ready"], "another page's mark is ignored")

    def test_wakes_once_per_submit(self):
        self.mark(3, self.origin, True, "2026-10-17T08:00:00.000Z")
        state = Path(tempfile.mkdtemp()) / "k.handled"
        argv = ["queue_watch.py", "--key", "k-1234", "--artifact-id", self.ID, "--state", str(state), "--db", tempfile.mkdtemp()]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sys.argv = argv
            self.w.main()
        self.assertIn("only a doorbell", out.getvalue())
        self.assertEqual(state.read_text(), "2026-10-17T08:00:00.000Z")

    def test_rejects_a_bad_artifact_id(self):
        with self.assertRaises(SystemExit):
            self.w.origin_of("not-an-id")


if __name__ == "__main__":
    unittest.main()
