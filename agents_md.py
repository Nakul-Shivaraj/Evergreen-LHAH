"""P3 (Nakul): writes verified rules into AGENTS.md.

Only touches the text between the evergreen markers; anything humans wrote is left alone.
Accepts Rule dataclasses or plain dicts.
"""
import pathlib

START, END = "<!-- evergreen:start -->", "<!-- evergreen:end -->"


def _get(r, key, default=None):
    return r.get(key, default) if isinstance(r, dict) else getattr(r, key, default)


def confidence(r):
    return (_get(r, "succeeded", 1) + 1) / (_get(r, "applied", 1) + 2)


def render_block(rules, retired=(), needs_human=(), library="pandas"):
    lines = [START, "## Library rules (verified by Evergreen)", "", f"### {library}"]
    for r in rules:
        proven = ", ".join(_get(r, "proven_on") or []) or "unknown version"
        proof = _get(r, "proof") or []
        proof_txt = ""
        if proof:
            proof_txt = f" by `{proof[0]}`" + (f" (+{len(proof) - 1} more)" if len(proof) > 1 else "")
        source = _get(r, "source_url") or "unsourced"
        lines.append(f"- **{_get(r, 'rule_id')} · `{_get(r, 'signature')}`.** "
                     f"Use `{_get(r, 'replacement')}` instead of `{_get(r, 'pattern')}`.")
        lines.append(f"  Proven on {proven}{proof_txt} · confidence {confidence(r):.2f} · source: {source}")
    if retired:
        lines += ["", "## Retired rules"]
        for r in retired:
            lines.append(f"- ~~{_get(r, 'replacement')}~~")
            lines.append(f"  {_get(r, 'reason', 'No longer holds')} · source: {_get(r, 'source_url') or 'unsourced'}")
    if needs_human:
        lines += ["", "## Needs a human"]
        lines += [f"- {item}" for item in needs_human]
    lines.append(END)
    return "\n".join(lines)


def write_agents_md(repo, rules, retired=(), needs_human=(), library="pandas"):
    path = pathlib.Path(repo) / "AGENTS.md"
    text = path.read_text() if path.exists() else "# AGENTS.md\n"
    block = render_block(rules, retired, needs_human, library)
    if START in text and END in text:
        before = text.split(START, 1)[0]
        after = text.split(END, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text)
    return path
