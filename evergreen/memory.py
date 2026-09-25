"""P3 (Nakul): the agent's memory.

Every event is written to runs/events.jsonl immediately (never lost).
If RAWTREE=1 and RAWTREE_API_KEY is set, events are also batch-inserted into RawTree
over HTTP every 2 seconds in the background, so logging never slows the demo.
"""
import dataclasses
import json
import os
import pathlib
import queue
import threading
import time

import requests

RUN_DIR = pathlib.Path(os.environ.get("EVERGREEN_RUN_DIR", "runs"))
RUN_DIR.mkdir(exist_ok=True)
LOCAL_LOG = RUN_DIR / "events.jsonl"
RULES_FILE = RUN_DIR / "rules.json"
API = "https://api.rawtree.com/v1"


def _db():
    return os.environ.get("RAWTREE_DATABASE", "evergreen")


def _headers():
    return {"Authorization": f"Bearer {os.environ.get('RAWTREE_API_KEY', '')}"}


def rawtree_on():
    # Read at call time, so env loaded by the entry point after import still counts.
    return os.environ.get("RAWTREE") == "1" and bool(os.environ.get("RAWTREE_API_KEY"))

_q = queue.Queue()
_lock = threading.Lock()


def log(table, row):
    row = {**row, "at": row.get("at", int(time.time()))}   # epoch seconds, per the brief
    with LOCAL_LOG.open("a") as f:
        f.write(json.dumps({"_table": table, **row}) + "\n")
    if rawtree_on():
        _start_flusher()
        _q.put((table, row))


def flush():
    """Send everything queued to RawTree. Call once at the end of a run too.
    Failed batches are re-queued, so a network blip never loses an event."""
    with _lock:
        batch = {}
        while not _q.empty():
            t, r = _q.get()
            batch.setdefault(t, []).append(r)
        for t, rows in batch.items():
            try:
                resp = requests.post(f"{API}/tables/{t}", params={"database": _db()},
                                     json=rows, headers=_headers(), timeout=10)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[memory] RawTree insert into {t} failed ({e}); will retry")
                for r in rows:
                    _q.put((t, r))


_flusher_started = False


def _flusher():
    while True:
        time.sleep(2)
        flush()


def _start_flusher():
    global _flusher_started
    if not _flusher_started:
        _flusher_started = True
        threading.Thread(target=_flusher, daemon=True).start()


def query(sql):
    """Read-only SQL against RawTree. Returns [] if RawTree is off or the query fails
    (e.g. a table that doesn't exist until its first insert)."""
    if not rawtree_on():
        return []
    try:
        resp = requests.post(f"{API}/query", params={"database": _db()}, json={"sql": sql},
                             headers=_headers(), timeout=20)
        return resp.json().get("data", []) if resp.ok else []
    except (requests.RequestException, ValueError):
        return []


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
