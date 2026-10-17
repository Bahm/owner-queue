#!/usr/bin/env python3
"""Wake a Claude Code session when an Owner Queue is submitted: only with --unsafe-unattended-wake.

The owner's copy of the queue page, open in the Claude desktop app, writes the newest submit allowed to wake
into its localStorage as "owner-queue:<queue key>:submitted". The app keeps localStorage in a LevelDB database
on disk; this reads that database read-only, with no model and no network, and exits when a new submit appears.
A session runs it as a background task, so its exit starts the session's turn.

Only a mark written by the queue's own page counts: localStorage keys carry the origin of the page that wrote
them, https://<artifact id>.frame.claudeusercontent.com, and any other page's key with the same name is ignored.
A wake is only a doorbell: the session still re-reads the store and checks the live page before acting.

    queue_watch.py --key QUEUE_KEY --artifact-id ID [--state FILE] [--interval S] [--db DIR]
    queue_watch.py --key QUEUE_KEY --artifact-id ID --dump      what the queue's page has written, then exit
    queue_watch.py --list                                       every page with owner-queue keys, then exit
"""
import argparse, json, re, struct, sys, time
from pathlib import Path

CANDIDATES = [
    Path.home() / ".config/Claude/Local Storage/leveldb",
    Path.home() / "Library/Application Support/Claude/Local Storage/leveldb",
]
DB = next((p for p in CANDIDATES if p.exists()), CANDIDATES[0])
PREFIX = "owner-queue:"


def varint(b, i):
    n = shift = 0
    while True:
        c = b[i]; i += 1
        n |= (c & 0x7F) << shift; shift += 7
        if c < 0x80:
            return n, i


def snappy(b):
    _, i = varint(b, 0)
    out = bytearray()
    while i < len(b):
        tag = b[i]; i += 1
        kind = tag & 3
        if kind == 0:
            n = tag >> 2
            if n < 60:
                n += 1
            else:
                k = n - 59; n = int.from_bytes(b[i:i + k], "little") + 1; i += k
            out += b[i:i + n]; i += n
            continue
        if kind == 1:
            n = ((tag >> 2) & 7) + 4; off = ((tag >> 5) << 8) | b[i]; i += 1
        elif kind == 2:
            n = (tag >> 2) + 1; off = int.from_bytes(b[i:i + 2], "little"); i += 2
        else:
            n = (tag >> 2) + 1; off = int.from_bytes(b[i:i + 4], "little"); i += 4
        for _ in range(n):
            out.append(out[-off])
    return bytes(out)


def log_entries(data):
    """(sequence, key, value or None for a delete) from a LevelDB write-ahead log."""
    record, pos = b"", 0
    while pos + 7 <= len(data):
        if len(data) - pos < 7 or (pos % 32768) > 32768 - 7:
            pos = (pos // 32768 + 1) * 32768; continue
        length, kind = struct.unpack_from("<HB", data, pos + 4)
        if kind == 0 and length == 0:
            pos = (pos // 32768 + 1) * 32768; continue
        chunk = data[pos + 7:pos + 7 + length]; pos += 7 + length
        if kind in (1, 2):
            record = chunk
        elif kind in (3, 4):
            record += chunk
        if kind in (1, 4) and len(record) >= 12:
            seq, count = struct.unpack_from("<QI", record, 0)
            i = 12
            try:
                for n in range(count):
                    tag = record[i]; i += 1
                    kl, i = varint(record, i); key = record[i:i + kl]; i += kl
                    if tag == 1:
                        vl, i = varint(record, i); val = record[i:i + vl]; i += vl
                    else:
                        val = None
                    yield seq + n, key, val
            except IndexError:
                pass   # a record still being written
            record = b""


def block_entries(block):
    restarts = struct.unpack_from("<I", block, len(block) - 4)[0]
    end = len(block) - 4 - 4 * restarts
    i, key = 0, b""
    while i < end:
        shared, i = varint(block, i); unshared, i = varint(block, i); vlen, i = varint(block, i)
        key = key[:shared] + block[i:i + unshared]; i += unshared
        yield key, block[i:i + vlen]; i += vlen


def read_block(data, handle):
    off, i = varint(handle, 0); size, _ = varint(handle, i)
    raw, kind = data[off:off + size], data[off + size]
    return snappy(raw) if kind == 1 else raw


def table_entries(data):
    """(sequence, key, value or None) from a LevelDB table (.ldb)."""
    if len(data) < 48 or data[-8:] != bytes.fromhex("57fb808b247547db"):
        return
    footer = data[-48:]
    _, i = varint(footer, 0); _, i = varint(footer, i)     # skip the metaindex handle
    index = read_block(data, footer[i:])                    # the index handle follows it
    for _, handle in block_entries(index):
        for ikey, val in block_entries(read_block(data, handle)):
            tag = int.from_bytes(ikey[-8:], "little")
            yield tag >> 8, ikey[:-8], (val if tag & 0xFF == 1 else None)


def decode(b):
    if b is None or not b:
        return None
    return b[1:].decode("latin-1") if b[0] == 1 else b[1:].decode("utf-16-le", "replace")


def rows():
    """(sequence, origin, key name, value text) for every localStorage entry in the app's database."""
    for f in sorted(DB.glob("*.ldb")) + sorted(DB.glob("*.log")):
        try:
            data = f.read_bytes()
            entries = log_entries(data) if f.suffix == ".log" else table_entries(data)
            for seq, key, val in entries:
                at = key.find(b"\x00\x01")
                if not key.startswith(b"_") or at < 0:
                    continue
                yield seq, key[1:at].decode("latin-1"), key[at + 2:].decode("latin-1"), val
        except (OSError, IndexError, struct.error, ValueError):
            continue   # a file being rewritten: the next pass reads it


def origin_of(artifact_id):
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", artifact_id or ""):
        sys.exit("--artifact-id must be the artifact's id, as `Artifact read` prints it: 8-4-4-4-12 hex digits.")
    return f"https://{artifact_id}.frame.claudeusercontent.com/"


def read_keys(key_prefix, origin):
    """{key name: (sequence, text or None)} for the queue's own page only; the newest write wins."""
    found = {}
    for seq, org, name, val in rows():
        if not name.startswith(key_prefix) or not org.startswith(origin):
            continue
        if name not in found or seq > found[name][0]:
            found[name] = (seq, decode(val))
    return found


def main():
    global DB
    ap = argparse.ArgumentParser(description="Wake a session when an Owner Queue is submitted (unsafe: unattended).")
    ap.add_argument("--key", help="the queue's key, from config/page queueKey (queue.py status prints it)")
    ap.add_argument("--artifact-id", help="the artifact's id, as `Artifact read` prints it")
    ap.add_argument("--state", default=None, help="remembers the last submit handled")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--db", default=None, help="the app's Local Storage/leveldb folder")
    ap.add_argument("--dump", action="store_true", help="print what the queue's page has written, then exit")
    ap.add_argument("--list", action="store_true", help="print every page that wrote owner-queue keys, then exit")
    a = ap.parse_args()
    if a.db:
        DB = Path(a.db).expanduser()
    if not DB.exists():
        sys.exit(f"No Claude desktop storage at {DB}. Pass --db.")
    if a.list:
        seen = {}
        for seq, org, name, val in rows():
            if name.startswith(PREFIX):
                seen.setdefault(org, set()).add(name)
        for org, names in sorted(seen.items()):
            print(org, " ".join(sorted(names)))
        return
    if not a.key or not re.fullmatch(r"[A-Za-z0-9_.-]{4,80}", a.key):
        sys.exit("--key must be the queue's key (letters, digits, - _ .).")
    origin = origin_of(a.artifact_id)
    key_prefix = f"{PREFIX}{a.key}:"
    if a.dump:
        for name, (seq, text) in sorted(read_keys(key_prefix, origin).items()):
            print(seq, name, (text or "")[:160])
        return
    state = Path(a.state or Path.home() / ".cache" / "owner-queue" / "wake" / f"{a.key}.handled")
    state.parent.mkdir(parents=True, exist_ok=True)
    handled = state.read_text().strip() if state.exists() else ""
    want = key_prefix + "submitted"
    while True:
        seq, text = read_keys(key_prefix, origin).get(want, (0, None))
        try:
            mark = json.loads(text) if text else {}
        except ValueError:
            mark = {}
        at = mark.get("at") if isinstance(mark, dict) else None
        if isinstance(mark, dict) and mark.get("ready") and isinstance(at, str) and at != handled:
            state.write_text(at)
            print(f"Owner Queue {a.key}: a submit at {at} by {mark.get('by') or 'unknown'}. This is only a doorbell. "
                  f"Re-arm this watcher first, then check the live page and read the store before acting (SKILL.md, Wake).")
            return
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
