"""End-to-end check of everything except the Liquid patcher, against the real demo repo.

usage: python check_integration.py ../sales-report
Needs NIMBLE_API_KEY and (for the RawTree part) RAWTREE=1 + RAWTREE_API_KEY in .env/.env.local.
Also pre-warms the Nimble evidence cache for every real failure, so the demo lookups are instant.
"""
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

from evergreen import agents_md, memory  # noqa: E402  (after env is loaded)
from evergreen.evidence import get_evidence  # noqa: E402
from evergreen.golden import golden_ok  # noqa: E402
from evergreen.liquid import match_rule  # noqa: E402
from evergreen.types import Failure, Rule  # noqa: E402

repo = Path(sys.argv[1] if len(sys.argv) > 1 else "../sales-report").resolve()
OLD, NEW = repo / ".venv-old", repo / ".venv-new"
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def failures(venv) -> tuple[set, list[Failure]]:
    """Minimal JUnit triage (the real runner is P1's): one Failure per failing test."""
    xml = repo / "report.xml"
    subprocess.run([f"{venv}/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    f"--junitxml={xml}"], cwd=repo, capture_output=True)
    passing, failing = set(), []
    for tc in ET.parse(xml).getroot().iter("testcase"):
        tid = f"{tc.get('classname')}::{tc.get('name')}"
        bad = tc.find("failure")
        if bad is None:
            bad = tc.find("error")
        if bad is None:
            passing.add(tid)
            continue
        text = bad.text or ""
        msg = bad.get("message", "")
        exc, _, detail = msg.partition(": ")
        frames = re.findall(r"^(src/[\w/]+\.py):(\d+):", text, re.M)
        src, line_no = frames[-1] if frames else ("", 0)
        attr = re.search(r"'(\w+)' object has no attribute '(\w+)'", detail)
        kw = re.search(r"keyword argument '(\w+)'", detail)
        api = f"{attr[1]}.{attr[2]}" if attr else f"{src.split('/')[-1][:-3]}.{kw[1]}" if kw else detail[:40]
        failing.append(Failure(tid, src, exc.split(".")[-1], detail, int(line_no), None, f"{exc.split('.')[-1]}: {api}"))
    xml.unlink(missing_ok=True)
    return passing, failing


# 1. Demo repo behaves as planned.
p_old, f_old = failures(OLD)
p_new, f_new = failures(NEW)
check("pandas 1.5.3: all tests pass", not f_old, f"{len(p_old)} passed")
check("pandas 2.2.3: planned failures", len(f_new) == 14 and len(p_new) == 5, f"{len(f_new)} failed, {len(p_new)} passed")

# 2. Golden check.
check("golden check passes on the old env", golden_ok(repo, OLD))
check("golden check does not reject the unfixed new env", golden_ok(repo, NEW))

# 3. Nimble evidence for every distinct real failure (pre-warms the cache).
sigs = {}
for f in f_new:
    sigs.setdefault(f.signature, f)
print(f"\n{len(sigs)} distinct failure signatures:")
for sig, f in sigs.items():
    ev = get_evidence(f)
    good = ev is not None and ev.url.startswith("http")
    check(f"evidence  {sig}", good, f"{ev.latency_s}s {ev.url}" if good else "no evidence")
    if good:
        memory.log("evidence", {"run_id": "selftest", "signature": sig, "url": ev.url,
                                "latency_s": ev.latency_s, "cached": ev.latency_s == 0})

# 4. Rule matching on real signatures.
first = next(iter(sigs.values()))
rule = Rule("R1", first.signature, "old", "new")
check("match_rule finds a rule for the same failure", match_rule(first, [rule]) is rule)
others = [f for s, f in sigs.items() if s.split(":")[-1].split(".")[-1] != first.signature.split(".")[-1]]
check("match_rule ignores unrelated failures", all(match_rule(f, [rule]) is None for f in others))

# 5. AGENTS.md writer keeps human rules and replaces only its block.
with tempfile.TemporaryDirectory() as d:
    Path(d, "AGENTS.md").write_text("# AGENTS.md\n\nHuman rule: use black.\n")
    agents_md.write_agents_md(d, [rule])
    agents_md.write_agents_md(d, [rule, Rule("R2", "AttributeError: Series.iteritems", ".iteritems()", ".items()")])
    text = Path(d, "AGENTS.md").read_text()
    check("AGENTS.md keeps human text, one Evergreen block, both rules",
          "Human rule: use black." in text and text.count("evergreen:start") == 1 and "R2" in text)

# 6. RawTree round trip through memory.py (HTTP).
if memory.rawtree_on():
    memory.log("test_runs", {"run_id": "selftest", "mode": "selftest", "passing": len(p_new),
                             "failing": len(f_new), "total": len(p_new) + len(f_new)})
    memory.flush()
    time.sleep(1)
    rows = memory.query("SELECT count() AS n FROM test_runs WHERE run_id = 'selftest'")
    check("RawTree insert + query via memory.py", rows and int(rows[0]["n"]) >= 1, f"rows={rows}")
    ev_rows = memory.query("SELECT count() AS n FROM evidence WHERE run_id = 'selftest'")
    check("RawTree evidence rows landed", ev_rows and int(ev_rows[0]["n"]) >= 1, f"rows={ev_rows}")
else:
    check("RawTree enabled (RAWTREE=1 and RAWTREE_API_KEY)", False)

print("\nALL CHECKS PASS" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)
