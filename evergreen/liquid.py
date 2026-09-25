"""P2: decide whether a failure is one we've already solved (rule) or a new one (None).

Deterministic first: exact signature, then same exception type + same API attribute.
If LIQUID_URL points at a llama-server running LFM2.5, the model confirms loose
candidates with a yes/no grammar. Tested on LFM2.5-1.2B: it finds real matches but
says "yes" too easily, so it only ever confirms candidates code already narrowed down,
never picks from the full rulebook.
"""
import os
import re

import requests

from .types import Failure, Rule

LIQUID_URL = os.environ.get("LIQUID_URL")          # e.g. http://<teammate-laptop>:8080
USABLE = ("verified", "trusted")


def api_name(signature: str) -> str:
    """'AttributeError: DataFrame.append' -> 'append'."""
    return re.split(r"[.:\s]", signature.strip())[-1].lower()


def ask_liquid(f: Failure, rule: Rule) -> bool:
    prompt = (f"Error: {f.signature}\nMessage: {f.message}\nCode: {f.line or ''}\n\n"
              f"Known fix: {rule.signature}: {rule.pattern} -> {rule.replacement}\n\n"
              "Is this error caused by the same removed feature, so the known fix applies? Answer yes or no.")
    resp = requests.post(f"{LIQUID_URL}/v1/chat/completions", timeout=10, json={
        "messages": [{"role": "user", "content": prompt}],
        "grammar": 'root ::= "yes" | "no"', "max_tokens": 2, "temperature": 0})
    return resp.json()["choices"][0]["message"]["content"].strip() == "yes"


def match_rule(f: Failure, rules: list[Rule]) -> Rule | None:
    usable = [r for r in rules if r.status in USABLE]
    exact = [r for r in usable if r.signature == f.signature]
    if exact:
        return max(exact, key=lambda r: r.succeeded)
    # Same exception type AND same attribute: e.g. Series.append vs DataFrame.append.
    loose = [r for r in usable if r.signature.split(":")[0] == f.exc_type
             and api_name(r.signature) == api_name(f.signature)]
    for rule in loose:
        if not LIQUID_URL:
            return rule
        try:
            if ask_liquid(f, rule):
                return rule
        except requests.RequestException:
            return rule   # Liquid down: the deterministic gate already held
    return None


if __name__ == "__main__":
    def fail(sig, msg="", line=""):
        return Failure("t::x", "src/a.py", sig.split(":")[0], msg, 1, line, sig)

    R1 = Rule("R1", "AttributeError: DataFrame.append", "df.append(o)", "pd.concat([df, o])")
    R2 = Rule("R2", "AttributeError: Series.iteritems", ".iteritems()", ".items()")
    R3 = Rule("R3", "TypeError: DataFrame.mean", "mean()", "mean(numeric_only=True)")
    R4 = Rule("R4", "AttributeError: Index.is_monotonic", ".is_monotonic", ".is_monotonic_increasing", status="demoted")
    rules = [R1, R2, R3, R4]
    assert match_rule(fail("AttributeError: DataFrame.append"), rules) is R1
    assert match_rule(fail("AttributeError: Series.append"), rules) is R1          # same API, other class
    assert match_rule(fail("AttributeError: DataFrame.iteritems"), rules) is R2
    assert match_rule(fail("AttributeError: Index.is_monotonic"), rules) is None    # demoted rules never fire
    assert match_rule(fail("TypeError: to_csv.line_terminator"), rules) is None     # new error
    assert match_rule(fail("AttributeError: deque.append_left"), rules) is None     # near-miss name
    assert match_rule(fail("TypeError: DataFrame.append"), rules) is None           # exception type must match
    print("liquid.match_rule: all checks pass")
