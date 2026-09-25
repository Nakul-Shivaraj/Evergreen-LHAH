"""P2 (stretch): live release notes via Nimble, and which rules they put in doubt."""
import os
import re
from pathlib import Path

import requests

from .types import Rule

RELEASE_NOTES = {"pandas": "https://pandas.pydata.org/docs/whatsnew/v{version}.html"}
CACHE_DIR = Path(os.environ.get("CHANGELOG_CACHE", ".changelog_cache"))


def fetch_changelog(library: str, version: str) -> str:
    """Release notes as markdown. The pandas page is ~250K chars and takes Nimble ~40s,
    so it is cached on disk: fetch it once before the demo."""
    cached = CACHE_DIR / f"{library}-{version}.md"
    if cached.exists():
        return cached.read_text()
    url = RELEASE_NOTES[library].format(version=version)
    resp = requests.post("https://sdk.nimbleway.com/v2/extract", timeout=120,
                         headers={"Authorization": f"Bearer {os.environ['NIMBLE_API_KEY']}"},
                         json={"url": url, "formats": ["markdown"]})
    resp.raise_for_status()
    text = (resp.json().get("data", {}).get("markdown") or "").replace("\\_", "_")
    CACHE_DIR.mkdir(exist_ok=True)
    cached.write_text(text)
    return text


def affected_rules(changelog: str, rules: list[Rule]) -> list[Rule]:
    """Rules whose API (or replacement API) the release notes mention: these get re-tested."""
    def names(rule: Rule) -> set[str]:
        found = re.findall(r"\.?([A-Za-z_]\w{3,})\s*\(|\.([A-Za-z_]\w{3,})\b|(\w{4,})=",
                           f"{rule.signature} {rule.pattern} {rule.replacement}")
        return {n for group in found for n in group if n} - {"AttributeError", "TypeError", "DataFrame", "Series"}
    return [r for r in rules if r.status != "retired" and any(
        re.search(rf"\b{re.escape(n)}\b", changelog) for n in names(r))]


if __name__ == "__main__":
    notes = "Removed DataFrame.select_dtypes object behavior for strings; `Index.is_monotonic` gone."
    R1 = Rule("R1", "AttributeError: DataFrame.append", "df.append(o)", "pd.concat([df, o])")
    R5 = Rule("R5", "select text columns", 'df.select_dtypes(include="object")', 'df.select_dtypes(include="string")')
    R6 = Rule("R6", "AttributeError: Index.is_monotonic", ".is_monotonic", ".is_monotonic_increasing")
    assert [r.rule_id for r in affected_rules(notes, [R1, R5, R6])] == ["R5", "R6"]
    print("changelog.affected_rules: all checks pass")
