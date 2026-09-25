"""P2: live evidence from the web for an error we haven't seen (Nimble Search).

One search call, restricted to the library's official docs, with page content included
(~7s). Falls back to an unrestricted search's descriptions. Results are cached on disk
per signature, so re-runs and the recorded demo don't pay for the same lookup twice.
"""
import json
import os
import re
import time
from pathlib import Path

import requests

from .types import Evidence, Failure

API = "https://sdk.nimbleway.com/v2/search"
OFFICIAL = {"pandas": ["pandas.pydata.org"]}
CACHE = Path(os.environ.get("EVIDENCE_CACHE", ".evidence_cache.json"))
WINDOW = 500   # characters of context kept around the API name
HINTS = re.compile(r"deprecat|removed|instead|renamed|use\s+`", re.I)


def _search(body: dict) -> list[dict]:
    resp = requests.post(API, json=body, timeout=30,
                         headers={"Authorization": f"Bearer {os.environ['NIMBLE_API_KEY']}"})
    resp.raise_for_status()
    return resp.json().get("results", [])


def clean(markdown: str) -> str:
    text = markdown.replace("\\_", "_").replace("\\*", "*")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)     # [label](url) -> label
    return re.sub(r"\s+", " ", text)


def snippet_around(text: str, api: str) -> str | None:
    """Centered on a deprecation/replacement sentence near `api`, else on the last mention
    (the first mentions are usually the page's navigation menu)."""
    near = WINDOW // 2
    hits = [m.start() for m in re.finditer(re.escape(api), text, re.I)]
    if not hits:
        return None
    center = next((h.start() for h in HINTS.finditer(text)
                   if any(abs(h.start() - a) <= near for a in hits)), hits[-1])
    return text[max(0, center - near // 2): center + WINDOW - near // 2]


def api_of(f: Failure) -> str:
    """'AttributeError: DataFrame.append' -> 'append'; keyword errors use the keyword."""
    kw = re.search(r"keyword argument '(\w+)'", f.message)
    return kw[1] if kw else re.split(r"[.:\s]", f.signature.strip())[-1]


def get_evidence(f: Failure, library: str = "pandas", version: str = "2") -> Evidence | None:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if f.signature in cache:
        return Evidence(**{**cache[f.signature], "latency_s": 0.0})
    t0, api = time.time(), api_of(f)
    query = f"{library} {version} {f.exc_type} {f.message}"[:200]
    ev = None
    try:
        for r in _search({"query": query, "max_results": 3, "search_depth": "lite", "full_content": True,
                          "include_domains": OFFICIAL.get(library, [])}):
            snip = snippet_around(clean(r.get("content") or ""), api)
            if snip:
                ev = Evidence(r["url"], snip.strip(), 0.0)
                break
        if not ev:   # nothing official mentions it: take the best general result's description
            top = _search({"query": query, "max_results": 3, "search_depth": "lite"})
            if top:
                ev = Evidence(top[0]["url"], top[0].get("description", ""), 0.0)
    except requests.RequestException:
        return None
    if ev:
        ev.latency_s = round(time.time() - t0, 2)
        CACHE.write_text(json.dumps({**cache, f.signature: {"url": ev.url, "snippet": ev.snippet}}, indent=1))
    return ev


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    assert snippet_around(clean("x line\\_terminator y"), "line_terminator")          # markdown escapes
    assert "removed" in (snippet_around("append here. " + "z" * 600 + " append was removed", "append") or "")
    assert "instead" in (snippet_around("nav append nav " + "z" * 600 + " Deprecated: use concat() instead of append", "append") or "")
    cases = [("AttributeError", "'DataFrame' object has no attribute 'append'", "AttributeError: DataFrame.append"),
             ("TypeError", "to_csv() got an unexpected keyword argument 'line_terminator'", "TypeError: DataFrame.to_csv"),
             ("AttributeError", "'Index' object has no attribute 'is_monotonic'", "AttributeError: Index.is_monotonic")]
    for exc, msg, sig in cases:
        ev = get_evidence(Failure("t::x", "src/a.py", exc, msg, 1, None, sig))
        assert ev and ev.url.startswith("http") and ev.snippet, sig
        print(f"{ev.latency_s:5.1f}s  {sig}\n       {ev.url}\n       {ev.snippet[:220]}")
