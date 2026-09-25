"""P3 (Nakul): the agent's memory.

Every event is written to runs/events.jsonl immediately (never lost).
If RAWTREE=1 and the rtree CLI is installed, events are also batch-inserted
into RawTree every 2 seconds in the background, so logging never slows the demo.
"""
import dataclasses
import json
import os
import pathlib
import queue
import shutil
import subprocess
import threading
import time

RUN_DIR = pathlib.Path(os.environ.get("EVERGREEN_RUN_DIR", "runs"))
RUN_DIR.mkdir(exist_ok=True)
LOCAL_LOG = RUN_DIR / "events.jsonl"
RULES_FILE = RUN_DIR / "rules.json"
USE_RAWTREE = os.environ.get("RAWTREE") == "1" and shutil.which("rtree") is not None

_q = queue.Queue()
_lock = threading.Lock()


def log(table, row):
    row = {**row, "at": row.get("at", int(time.time()))}   # epoch seconds, per the brief
    with LOCAL_LOG.open("a") as f:
        f.write(json.dumps({"_table": table, **row}) + "\n")
    if USE_RAWTREE:
        _q.put((table, row))


def flush():
    """Send everything queued to RawTree. Call once at the end of a run too."""
    with _lock:
        batch = {}
        while not _q.empty():
            t, r = _q.get()
            batch.setdefault(t, []).append(r)
        for t, rows in batch.items():
            # verify flags against RawTree's CLI docs
            subprocess.run(["rtree", "insert", "--table", t, "--data", json.dumps(rows), "--json"],
                           capture_output=True)


def _flusher():
    while True:
        time.sleep(2)
        flush()


if USE_RAWTREE:
    threading.Thread(target=_flusher, daemon=True).start()


def query(sql):
    """Read-only SQL against RawTree. Returns [] if RawTree is off."""
    if not USE_RAWTREE:
        return []
    out = subprocess.run(["rtree", "query", "--json", sql], capture_output=True, text=True)
    return json.loads(out.stdout or "[]")


def local_rows(table):
    """Fallback for charts if RawTree has trouble: same rows, from the local JSONL."""
    if not LOCAL_LOG.exists():
        return []
    rows = [json.loads(line) for line in LOCAL_LOG.read_text().splitlines() if line.strip()]
    return [{k: v for k, v in r.items() if k != "_table"} for r in rows if r["_table"] == table]


def load_rules():
    """Returns a list of dicts. Convert with Rule(**d)."""
    return json.loads(RULES_FILE.read_text()) if RULES_FILE.exists() else []


def save_rules(rules):
    RULES_FILE.write_text(json.dumps(
        [dataclasses.asdict(r) if dataclasses.is_dataclass(r) else r for r in rules], indent=2))


def save_rule_event(run_id, rule_id, event, **fields):
    """event: proposed | verified | applied | succeeded | failed | demoted | retired"""
    log("rule_events", {"run_id": run_id, "rule_id": rule_id, "event": event, **fields})
