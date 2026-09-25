# Evergreen: Project Brief

**The AGENTS.md that writes, tests, and expires itself.**

Its engine is *the ratchet*: a coding agent that fixes one file at a time, never lets a passing test fail, and turns every verified fix into a rule.

Long Horizon Agents Hackathon · Friday, September 25, 2026 · AWS Builder Loft, San Francisco
Team: 3 people · **Submission deadline: 4:00 PM** (we submit by 3:45) · Code freeze: 3:00 PM

> **How to use this file.** This is the complete plan: what we're building, why, how it works, how we prove it, how we demo it, and who does what. Items marked **(verify)** have not been confirmed and must be checked before they go on a slide or into code.

---

## Contents

1. TL;DR
2. The event
3. The problem
4. What Evergreen does
5. How it fits the challenge and the criteria
6. Architecture
7. The loop, step by step
8. The rulebook
9. Safety: stopping hallucinated fixes
10. Why the prompt never grows
11. Data model (RawTree)
12. Evergreen features (on top of the ratchet loop)
13. The demo repo
14. Sponsors: roles, pain points, lines for judges
15. Proof: what we measure
16. The 3-minute demo
17. Pitch lines and claims
18. Judge Q&A
19. Team split: 3 people
20. Interfaces between people
21. Schedule and checkpoints (submit by 3:45; deadline 4:00)
22. Repo layout
23. Setup and code snippets
24. Fallbacks and risks
25. Verify list
26. Submission checklist

---

## 1. TL;DR

- **Problem.** Coding agents start every session knowing nothing about your codebase. Teams patch this with hand-written rules files (AGENTS.md, CLAUDE.md, Cursor rules). Those files fail in two ways: nobody keeps them updated, so every session repeats yesterday's mistakes; and they silently go stale, so when a library changes, the agent follows a rule that is now wrong.
- **What Evergreen does.** It watches a coding agent work and turns its experience into a living rules file. A lesson enters the file **only after tests prove it**, gets a **confidence score** from how it performs, and is **tied to a library version and source** so it can be re-tested and retired when upstream changes. It writes all of this into a real AGENTS.md and opens a PR.
- **The demo vehicle.** The agent upgrades a small repo from pandas 1.5 to 2.2 (about 20 tests, most red). It fixes one file at a time; a fix is kept only if no previously passing test breaks (the ratchet). Every kept fix becomes a rule. By the later files, trusted rules fix errors instantly with zero LLM tokens.
- **Why it fits the theme.** Memory that preserves only what's proven and discards what stopped being true. The prompt for file 50 is the same size as for file 1; history lives in RawTree and is queried, never carried.
- **Sponsors (4).** AWS Bedrock writes patches and proposes rules. Liquid (on the laptop) triages and matches every failure. Nimble fetches live migration notes, GitHub issues, and release notes. Tinybird/RawTree stores the rulebook and every outcome.
- **Pitch line.** "Every coding agent reads a rules file. Nobody keeps it true. Evergreen writes only lessons that tests have proven, scores them by outcome, and retires them when the library moves on."

**Simple version (for anyone new):**

1. A library update broke our code in many places.
2. Evergreen's agent fixes it one file at a time and checks every fix with the tests.
3. If a fix breaks something that worked, it throws the fix away and tries again.
4. Every fix that works becomes a note in the rulebook, with a score and a link to where it came from. The same problem is then solved instantly next time.
5. The rulebook is written into AGENTS.md, so the next coding session (any agent) starts smart.
6. When the library releases a new version, Evergreen re-tests its notes and crosses out the ones that stopped being true.

It's like a student doing a long worksheet who writes a cheat sheet as they go, only keeps notes that the answer key confirmed, and crosses notes out when the textbook gets a new edition.

---

## 2. The event

### 2.1 Challenge slide (verbatim)

> **Build agents that preserve what matters.**
> Ship long horizon agents that plan, act, observe, and self-correct across a full build cycle (spec, implementation, testing, iteration) without drowning in their own history. Use 3+ sponsor tools.

Event description: build agents that stay reliable over long tasks. Explore persistent state, memory, and context management, and show a working project at the end of the day.

### 2.2 Judging criteria

| Criterion | What the slide asks |
|---|---|
| **Autonomy** | How well does the agent act on the web using real-time data without manual intervention? |
| **Idea** | Does the solution have the potential to solve a meaningful problem or demonstrate real-world value? |
| **Technical Implementation** | How well is the architecture built and how well was the solution implemented? |
| **Tool Use** | Did the solution effectively use at least 3 sponsor tools? |
| **Presentation (Demo)** | Demonstration of the solution in 3 minutes |

### 2.3 Sponsors

OpenAI · AWS · Nimble · Liquid · Broccoli · Tinybird · Black Forest Labs

We use **4**: AWS (Bedrock), Liquid, Nimble, Tinybird/RawTree. We do not use OpenAI (we picked Bedrock), Broccoli (voice agents for home services), or Black Forest Labs (image/video). Don't force them in: judges punish token integrations.

### 2.4 Prize tracks we qualify for

| Track | Prize | Our angle |
|---|---|---|
| **Best use of Tinybird** | $2,000 / $1,000 / $500 Amazon gift cards | The agent's entire memory lives there; all charts come from SQL |
| **Best use of Nimble** | $1,000 + 10,000 credits / $500 + 5,000 credits | Live migration notes and GitHub issues; every URL on screen and in the PR |
| **Liquid AI** | Edge AI Kit + $250 | Matches every failure on the laptop; the big model only writes patches |

**Tinybird vs. RawTree (verify with the Tinybird rep, 1 minute).** The organizers' Tinybird resources link to RawTree docs as "Start here" (rawtree.com/tokensand). Default to RawTree. If the rep says classic Tinybird counts, the events stay the same; only the insert and query calls change.

### 2.5 Judges (likely focus is our guess)

| Judge | Role | Likely focus |
|---|---|---|
| Saptarshi Banerjee | Applied AI Specialist Architect, OpenAI | Architecture rigor, fair baselines |
| Viviana Márquez | Developer Relations, Liquid AI | Meaningful on-device use of Liquid, clear demo |
| Tianshu Yu | MTS, ML Engineer, Liquid AI | Small-model accuracy and latency, honest measurement |
| Yaniv Markovski | Head of Ecosystem Engineering, Nimble | Web data that is load-bearing |
| Mogana Kumaran S. | Senior Staff Data Engineer, Gap Inc | Realistic data and scenario |
| Amit Panda | Staff Software Engineer, LinkedIn | Engineering soundness, reliability |
| Tulika Manek | Tech Lead, Razorpay | Production thinking, failure handling |
| Pedro S. Lopez | Software Engineering, Airbyte | Data movement, context as infrastructure |

---

## 3. The problem

### 3.1 Plain explanation

Your code depends on libraries other people write. When a library ships a major version, it often removes old features. Your code breaks in many places even though you didn't change anything.

The fix is usually simple, but there are dozens of them: find the error, look up what replaced the old feature, fix it, run the tests, and repeat. It takes an afternoon or a week, so it keeps getting pushed to "next sprint." Meanwhile the team misses security fixes and new features, and the upgrade gets harder the longer it waits.

### 3.2 Rules files: the patch that goes stale

Because agents forget everything between sessions, teams write rules files by hand: AGENTS.md, CLAUDE.md, Cursor rules. The Compaction Cliff paper reports a large number of these on public GitHub (the brief we were given says nearly 400,000; **verify** in the paper before it goes on a slide). They fail in two ways:

- **Nobody updates them.** Lessons from today's session never make it into the file, so tomorrow's session repeats the mistakes.
- **They silently go stale.** A library updates, a rule becomes wrong, and the agent follows it confidently.

### 3.3 Why AI agents also fail at long tasks

A general coding agent working through 50 files keeps everything in its conversation: every file it read, every test run, every failed attempt. By file 10 the context is full of stale output. It slows down, costs more per step, starts repeating fixes it already tried, and forgets what it learned in file 2. That is exactly the "drowning in their own history" failure the hackathon is about.

### 3.4 A real example from today

On September 25, 2026, the OpenSAK project reported CI breaking twice after a merge with no related code change: new SQLAlchemy and mypy releases changed behavior underneath them (https://github.com/OpenSAK-Org/OpenSAK/issues/897). Libraries change under teams constantly; upgrades are the planned version of the same pain.

### 3.5 Slide-ready problem statement

> "Every coding agent reads a rules file. Nobody keeps it true. Lessons never get written down, and the ones that do go stale the day a library changes."

Demo framing: "Watch it happen on the task every team postpones: a major-version upgrade."

---

## 4. What Evergreen does

In the demo, you bump the version (pandas 1.5 → 2.2) and most tests go red. Evergreen then works alone:

1. **Runs the tests** and sees what broke.
2. **Takes the next broken file** and figures out each error.
3. **Checks its rulebook.** A small model on the laptop (Liquid) decides: is this a problem we've already solved, or a new one?
4. **For a new problem, looks it up live** with Nimble: official migration notes, GitHub issues.
5. **Writes a fix** for that one file with a model on AWS Bedrock.
6. **Runs all the tests again.** The fix is kept only if nothing that worked before broke and at least one more test passes. Otherwise it's rolled back and retried with the new error as feedback (up to 3 tries).
7. **Saves a rule** from every fix that passes, like "`df.append()` was removed; use `pd.concat()`," with a confidence score, its source link, and the library version it was proven on.
8. **Uses trusted rules instantly.** Once a rule has proven itself twice, matching errors are fixed with zero LLM tokens (still checked by the tests).
9. **Moves to the next file.** Repeats until all tests pass.
10. **Writes AGENTS.md** from the verified rules, so the next coding session starts with them.
11. **Opens a pull request**: one commit per verified fix, the updated AGENTS.md, a table of rules learned, the evidence links, and a list of anything it couldn't fix ("needs a human").
12. **(Stretch) Expires rules.** When pandas 3.0 is checked, Evergreen reads the release notes via Nimble, re-tests each rule, and retires the ones that no longer hold.

**What it solves:**

- **For teams using coding agents:** a rules file that stays true on its own, instead of one nobody maintains.
- **For engineers:** hours of repetitive upgrade work become one PR to review.
- **For long-running agents:** it shows how to stay reliable on a long task. Each step sees only a short rulebook and the current file; everything else lives in a database.

---

## 5. How it fits the challenge and the criteria

### 5.1 The challenge slide, word by word

| Slide says | Evergreen |
|---|---|
| Plan | Picks the next file and decides: known rule, or look it up |
| Act | Writes the patch and applies it |
| Observe | Runs the full test suite after every attempt |
| Self-correct | Rolls back any fix that breaks a passing test and retries with the new failure |
| Full build cycle: spec | The existing tests and the old version's outputs are the spec |
| Implementation | The patch |
| Testing | Full suite plus golden-output check after every attempt |
| Iteration | Retry loop per file; rules carry forward to later files |
| Without drowning in history | Prompt contains only the current file, its failures, and one rule or evidence snippet. History lives in RawTree |
| Preserve what matters, discard what doesn't | Only test-proven lessons persist (in RawTree and AGENTS.md); lessons that stop holding are retired |
| Use 3+ sponsor tools | AWS Bedrock, Liquid, Nimble, Tinybird/RawTree |

### 5.2 Criteria scorecard

| Criterion | Strength | How we win it |
|---|---|---|
| Autonomy | Medium (our weakest) | Every Nimble lookup shown live with its URL; a "human interventions: 0" counter; ends by opening a real PR on GitHub |
| Idea | High | Every engineer on the panel has a postponed upgrade |
| Technical Implementation | High | The ratchet check, rule lifecycle, hallucination guards, flat prompt, append-only memory |
| Tool Use | High | Each sponsor does a job that is essential, and it's visible on screen |
| Presentation | High if timed | Red → green → PR in about 90 seconds, then three charts |

---

## 6. Architecture

```
 pytest --junitxml ──► triage: test, file, exception, message, offending line
                          │
                          ▼
        Liquid LFM (laptop): match failure → known rule ID or "unknown"
                          │
          known rule ─────┤───── unknown
               │          │          │
               │          │    Nimble: live migration notes / GitHub issue
               ▼          ▼          ▼
        Bedrock: patch the whole file (+ propose a rule if new)
                          │
                          ▼
        GUARDS: parses? tests untouched? no skip/except-pass? not too big?
                          │
                          ▼
        RATCHET CHECK: full test suite + golden outputs
          passing ⊇ before AND ≥1 new pass AND outputs match?
            yes → git commit, rule verified     no → roll back, retry
                          │
                          ▼
        RawTree: every attempt, rule event, and test count (append-only)
                          │
                          ▼
        All green → push branch → gh pr create
```

---

## 7. The loop, step by step

1. **Run the full suite** in the new environment: `pytest -q --junitxml=report.xml`. JUnit XML is built into pytest, so no plugin is needed. Record the set of passing tests.
2. **Pick the next file with failures**, in a fixed order (see section 13.3). Map test modules to source modules by naming convention: `tests/test_clean.py` ↔ `src/clean.py`.
3. **Triage deterministically.** Parse the XML for each failure's test ID, exception type, and message. Find the offending source line from the traceback text. Normalize into a short signature, for example `AttributeError: DataFrame.append`.
4. **Match with Liquid.** Send the signature plus current rules (one line each). A grammar built per call allows only `R1 | R2 | … | unknown`. Then double-check deterministically: the matched rule's exception type must equal the failure's. If `llama-server` is down, fall back to exact signature matching.
5. **For unknown errors, get evidence.** Nimble search for `pandas 2.0 <short error>`. Prefer pandas.pydata.org (the "What's new in 2.0" page) and github.com/pandas-dev. Keep about 500 characters around the API name, plus the URL.
6. **Patch with Bedrock.** One call fixes all of the file's failures. Use the Converse API with a forced `submit_patch` tool, so output always matches a schema. The model returns the whole new file, plus a proposed rule if the fix is new.
7. **Guards** (section 9). Reject immediately if the patch fails any guard; count it as a retry with the reason as feedback.
8. **The ratchet check.** Write the file, run the full suite and the golden-output check. **Accept only if every previously passing test still passes, at least one new test passes, and outputs still match the old version.**
9. **On accept:** `git commit` with a message like `ratchet: fix clean.py (R1, R2)`, mark the proposed rule as verified, log everything to RawTree.
10. **On reject:** restore the file from its snapshot, retry with the new failure as feedback. Maximum 3 tries per file.
11. **After 3 failed tries:** mark "needs a human," restore the file, move on. It's listed in the PR.
12. **When everything passes** (or only "needs a human" items remain): push the branch, `gh pr create`.

Pseudocode for one file:

```python
def fix_file(src_file, failures):
    before = run_tests()                       # TestRun(passing=set, failing=[Failure])
    snapshot = read(src_file)
    feedback = None
    for attempt in range(3):
        hints = []
        for f in failures:
            rule = match_rule(f, rules)        # Liquid + deterministic check
            hints.append(rule or get_evidence(f))   # Nimble for unknowns
        res = patch(src_file, snapshot, failures, hints, feedback)   # Bedrock
        ok, why = patch_ok(snapshot, res.new_source)
        if not ok:
            log_attempt(..., accepted=0, rejected_by_guard=1); feedback = why; continue
        write(src_file, res.new_source)
        after = run_tests()
        if (tests_hash() == BASELINE_TESTS_HASH
                and before.passing <= after.passing
                and len(after.passing) > len(before.passing)
                and golden_ok()):
            commit(src_file, res); verify_rule(res.new_rule, evidence_urls)
            log_attempt(..., accepted=1); return True
        write(src_file, snapshot)              # roll back
        feedback = summarize(after.failing); log_attempt(..., accepted=0, rolled_back=1)
    mark_needs_human(src_file); return False
```

---

## 8. The rulebook

**A rule** is a short, reusable fix:

```json
{"rule_id": "R1",
 "signature": "AttributeError: DataFrame.append",
 "pattern": "df.append(other, ignore_index=True)",
 "replacement": "pd.concat([df, other], ignore_index=True)",
 "source_url": "https://pandas.pydata.org/...",
 "status": "verified", "applied": 3, "succeeded": 3}
```

**Rule lifecycle:**

- **Born only from a verified fix.** The model proposes a rule alongside a patch; it becomes real only if that patch passes the ratchet check. The model cannot invent rules on its own.
- **Scoped to an error signature.** A rule is used only when the same error signature appears. It is a hint to the patch model, never a find-and-replace.
- **Every use is checked.** A rule-guided patch still goes through the guards and the ratchet check.
- **Tracked and demoted.** Each rule counts applications and successes. After 2 failures it's demoted; the next occurrence is treated as unknown and gets a fresh web lookup.
- **Sourced or labeled.** `source_url` must be a URL Nimble actually returned this run. Otherwise the rule is saved as "unsourced" and labeled that way in the PR.

**Cross-run memory (stretch goal).** Start a second run on a different small repo. Evergreen loads verified rules from RawTree and needs zero web lookups from the first file. That's memory across tasks, not just within one.

---

## 9. Safety: stopping hallucinated fixes

The model will hallucinate sometimes. Evergreen's job is to make sure no hallucination reaches the PR.

| Hallucination | What catches it |
|---|---|
| Uses a function that doesn't exist | Test fails → ratchet check rejects → rolled back |
| Liquid picks the wrong rule | Deterministic exception-type check; if it slips through, the patch fails tests → rolled back → retried as unknown |
| Invents a rule without a real fix | Impossible: rules exist only after a verified fix |
| Rule too broad (e.g. rewrites a Python list's `.append()`) | Rules fire only on matching error signatures; the list test in the demo repo catches it → rolled back |
| **Cheats to make tests pass** (edits tests, adds `pytest.skip`, `try/except: pass`, deletes the function) | **Tests are read-only** (hash check) and the **patch guard** blocks these patterns |
| Invents a source URL | URL must be one Nimble returned this run; otherwise labeled "unsourced" |
| Tests pass but behavior changed | **Golden-output check**: outputs on sample data must match pandas 1.5's outputs |

**Patch guard:**

```python
import ast, re, difflib

BANNED = [r"pytest\.(skip|xfail)", r"except\s*:", r"except\s+Exception"]

def names(src):
    return {n.name for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}

def patch_ok(old, new, max_ratio=0.4):
    try:
        ast.parse(new)
    except SyntaxError:
        return False, "does not parse"
    if names(old) - names(new):
        return False, "removed a function or class"
    for pat in BANNED:
        if len(re.findall(pat, new)) > len(re.findall(pat, old)):
            return False, f"added {pat}"
    changed = sum(1 for l in difflib.ndiff(old.splitlines(), new.splitlines()) if l[:1] in "+-")
    if changed > max_ratio * 2 * max(len(old.splitlines()), 1):
        return False, "patch too large"
    return True, "ok"
```

**Tests are read-only:**

```python
import hashlib, pathlib
def tests_hash():
    files = sorted(pathlib.Path("tests").rglob("*.py"))
    return hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
```

The agent may only write inside `src/`. Compute `BASELINE_TESTS_HASH` once at start.

**Golden outputs.** Before the upgrade, in the old environment, run each pipeline function on the fixture data and save outputs to `golden/*.json`. After every candidate patch, run the same functions in the new environment and compare (floats within a small tolerance). Example: if the model "fixes" `df.mean()` by manually dropping columns instead of `numeric_only=True`, tests might pass but outputs won't match.

**The honest limit.** Evergreen can verify only what the tests and golden outputs cover. That's why it opens a PR for human review, with one commit per fix, and never merges.

**Why GitHub review isn't enough on its own.** Review happens once, hours later. Evergreen reuses its fixes, so a bad fix must be stopped before it becomes a rule and spreads to other files. Also, a cheating patch shows a green check on GitHub too. GitHub review is our last line of defense, not our first.

**Optional GitHub reinforcements:** publish guard results as a `ratchet-verify` commit status on the PR; CODEOWNERS on `tests/`; branch protection requiring CI, `ratchet-verify`, and one human approval.

---

## 10. Why the prompt never grows

Every patch prompt contains only:

- the system prompt,
- the current file,
- that file's triaged failures,
- one matched rule or one evidence snippet per failure,
- on a retry, the previous attempt's failure.

Nothing from earlier files goes in. For every attempt, log `prompt_tokens` (from Bedrock's usage response) and `naive_prompt_tokens`: what a chat-style agent would send if it kept its whole conversation (running total of all earlier prompts and outputs plus the current one). Evergreen's line stays flat; the naive line climbs. This chart is our answer to "without drowning in their own history."

---

## 11. Data model (RawTree)

Keep everything **append-only**. Tables are created automatically on first insert, and the query API is read-only SQL, so never update rows. Current state = latest event per ID. Store timestamps as epoch seconds (plain numbers) to avoid type-inference surprises.

```json
// attempts: one row per patch attempt
{"run_id":"r1","mode":"rules_on","attempt":7,"file":"report.py",
 "signatures":["AttributeError: DataFrame.append"],"rule_ids":["R1"],
 "used_web":0,"accepted":1,"rolled_back":0,"rejected_by_guard":0,
 "prompt_tokens":1840,"naive_prompt_tokens":14200,"output_tokens":620,
 "duration_s":9.1,"at":1790360000}

// rule_events: proposed / verified / applied / succeeded / failed / demoted
{"run_id":"r1","rule_id":"R1","event":"verified","signature":"AttributeError: DataFrame.append",
 "pattern":"df.append(...)","replacement":"pd.concat([...])",
 "regex_find":null,"regex_replace":null,"proven_on":"pandas 2.2.3",
 "proof":["tests/test_clean.py::test_merge_batches"],"confidence":0.67,
 "source_url":"https://...","at":1790359800}

// test_runs: one row per full-suite run
{"run_id":"r1","mode":"rules_on","passing":12,"failing":8,"total":20,"at":1790360010}

// evidence: one row per Nimble lookup
{"run_id":"r1","signature":"AttributeError: DataFrame.append","query":"pandas 2.0 ...",
 "url":"https://...","latency_s":2.4,"at":1790359790}
```

Keep a local copy of the rules for speed; write each event to RawTree as it happens. Charts read from RawTree with `rtree query --json`.

Example chart queries (SQL looks ClickHouse-like; **verify** against RawTree's SQL reference):

```sql
-- attempts and web lookups per file, in order
SELECT file, count() AS attempts, sum(used_web) AS web_lookups, min(at) AS started
FROM attempts WHERE run_id = 'r1' GROUP BY file ORDER BY started;

-- flat vs growing prompt
SELECT attempt, prompt_tokens, naive_prompt_tokens
FROM attempts WHERE run_id = 'r1' ORDER BY attempt;

-- the staircase
SELECT at, passing FROM test_runs WHERE run_id = 'r1' ORDER BY at;
```

---

## 12. Evergreen features (on top of the ratchet loop)

Evergreen is the product; **the ratchet loop (sections 6–11) is its engine.** Evergreen adds three things: it writes the verified rules into a real AGENTS.md, it applies trusted rules with zero LLM tokens, and it retires rules when the library moves on.

### 12.1 The living AGENTS.md (must-have)

After every verified rule, and at the end of the run, Evergreen renders its rules into `AGENTS.md` at the repo root and commits it in the PR. Any coding agent that reads the rules file at session start (AGENTS.md; CLAUDE.md for Claude Code) then begins the next session with verified knowledge instead of nothing.

Evergreen only manages its own block between markers. Anything humans wrote outside the block is left untouched.

```markdown
<!-- evergreen:start -->
## Library rules (verified by Evergreen)

### pandas
- **R1 · `DataFrame.append` was removed.** Use `pd.concat([df, other], ignore_index=True)`.
  Proven on pandas 2.2.3 by `tests/test_clean.py::test_merge_batches` (+2 files) · confidence 0.80 · source: https://pandas.pydata.org/...
- **R2 · `.iteritems()` was removed.** Use `.items()`.
  Proven on pandas 2.2.3 · confidence 0.83 · source: https://...

## Retired rules
- ~~Use `df.select_dtypes(include="object")` to pick text columns~~
  No longer holds on pandas 3.0 (string dtype is the default). Retired 2026-09-25 · source: https://pandas.pydata.org/...

## Needs a human
- `index_utils.py::make_index`: 3 attempts failed; see PR notes.
<!-- evergreen:end -->
```

### 12.2 Confidence scores (must-have, 5 lines of code)

```python
def confidence(rule):                    # Laplace-smoothed success rate
    return (rule.succeeded + 1) / (rule.applied + 2)

def trusted(rule):                       # eligible for zero-token application
    return rule.succeeded >= 2 and confidence(rule) >= 0.75
```

A new rule from its first verified fix scores 0.67 ("verified"). One more verified reuse brings it to 0.75 ("trusted"). A failure drops it; two failures in a row demote it back to "unknown," so the next occurrence gets a fresh lookup. Confidence is shown in AGENTS.md and on the dashboard.

In the demo repo, `append` and `iteritems` each appear 3 times, so the audience sees the full progression: **learned (LLM + web) → reused as a hint (LLM, no web) → instant (zero tokens).**

### 12.3 Instant rules: zero LLM tokens (should-have)

When the model proposes a rule, it also writes a mechanical transform: a regex find/replace for the offending line. Examples:

| Rule | `regex_find` | `regex_replace` |
|---|---|---|
| iteritems | `\.iteritems\(\)` | `.items()` |
| line_terminator | `\bline_terminator=` | `lineterminator=` |
| is_monotonic | `\.is_monotonic\b(?!_)` | `.is_monotonic_increasing` |
| mean on mixed columns | `\.mean\(\)` | `.mean(numeric_only=True)` |

Safety rules for instant application:

- **Validated at birth.** When the rule is created, apply the regex to the original offending line and check it reproduces the model's verified fix for that line. If not, the rule never gets an instant transform (it stays a hint for the LLM).
- **Applied only to the lines the traceback points at,** never file-wide. That's why the Python list `.append()` in `clean.py` is never touched.
- **Still checked.** An instant fix goes through the guards, the ratchet check, and the golden outputs like any other.
- **Falls back.** If an instant fix fails, record the failure (confidence drops) and retry through the LLM with the rule as a hint.

`append` is harder to do safely with a regex (arguments vary), so let it stay LLM-with-hint unless the transform validates at birth.

**The chart this enables:** LLM tokens per file dropping to zero on files fully covered by trusted rules. That's the strongest learning-curve visual we can show, and it's a cost story for AWS and a "small model does the work" story for Liquid.

### 12.4 Expiry: re-test rules when the library moves (stretch)

Every rule records `proven_on` (the library version) and `proof` (the test IDs and golden checks that verified it). When a new version appears:

1. **Nimble fetches the live release notes.** Real case: pandas 3.0.0 was released in January 2026, and the 3.0.x series is current. Its headline changes are a dedicated string data type by default and Copy-on-Write behavior.
2. **Re-run each rule's proof** in a pandas 3.0 environment (`uv venv --python 3.11 .venv-p3`, `pandas==3.0.*`; pandas 3.0 supports Python 3.11+).
3. **Pass:** add the new version to `proven_on`. **Fail:** retire the rule (moved to "Retired rules" with reason and source), or narrow it (for example "pandas < 3").

**How to make a real retirement happen on stage.** Seed the demo repo's existing AGENTS.md (outside Evergreen's block, as a typical human-written rule) with: "To select text columns, use `df.select_dtypes(include="object")`." Add code in `export.py` that follows it, plus a test. That's true on pandas 1.x/2.x. On pandas 3.0, text columns are inferred as the new `str` dtype instead of `object`, so that selection should come back empty and the test should fail. Evergreen traces the failure to the rule, retires it, and writes a replacement rule proven on 3.0. **Verify this behavior on pandas 3.0 before relying on it.**

This shows problem #2 live: rules files silently go stale, and Evergreen notices.

**Scope honestly:** build expiry only if the 2:15 checkpoint passed. Also run the fixed 2.2 code on pandas 3.0 early to see what else breaks; other failures would clutter the beat.

### 12.5 Novelty: how to say it

Three properties together:

1. **Proven-only memory:** a lesson enters memory only after tests prove it works.
2. **Outcome-scored memory:** confidence rises with every successful use and drops with every failure; bad lessons get demoted automatically.
3. **Expiring memory:** every lesson is tied to a library version and a source, and gets re-tested when upstream changes.

**Say:** "We haven't found an agent memory or rules-file tool that combines all three, to our knowledge."

**Don't say:** "Other agent memories are never checked." 2026 research already explores provenance-aware verified memory, revoking stale memories, and temporal validity for agent memory. And don't state specifics about how Cursor, Windsurf, Devin, or Claude Code memories work unless you've checked; product features change. "Typically LLM-written notes" is safe.

Novelty isn't a judging criterion anyway (Idea = meaningful problem, real-world value). **Lead with the problem, not the novelty.**

---

## 13. The demo repo

### 13.1 What it is

A small but realistic data pipeline called **sales-report**, in its own GitHub repo (the PR goes there). Six source files of about 30–40 lines each, 3–4 tests per file (about 20 total), and a small fixture CSV. It runs cleanly on **pandas 1.5**. After bumping to **pandas 2.2**, most tests fail.

**Why pandas and not NumPy:** ruff's `NPY201` rule reportedly auto-fixes many NumPy 2 changes **(verify)**, so a judge could say "one command does this." pandas 2 removals don't have an equally well-known one-command fix. Keep `numpy<2` in both environments so every failure comes from pandas.

### 13.2 Planted breakages (all real pandas 2.0 changes; verify each raises an error, not just a warning)

| Removed or changed in pandas 2.0 | Error on 2.x | Fix | Appears in |
|---|---|---|---|
| `DataFrame.append` / `Series.append` | AttributeError | `pd.concat([...])` | clean, report, summary |
| `.iteritems()` | AttributeError | `.items()` | clean, report, export |
| `df.mean()` / `groupby().mean()` on mixed columns | TypeError (`numeric_only` default changed) | `numeric_only=True` | metrics, summary |
| `to_csv(line_terminator=...)` | TypeError | `lineterminator=` | export |
| `pd.Int64Index(...)` | AttributeError | `pd.Index(..., dtype="int64")` | index_utils |
| `Index.is_monotonic` | AttributeError | `.is_monotonic_increasing` | index_utils |

Note: on pandas 1.5, `mean()` on mixed columns silently dropped non-numeric columns (with a FutureWarning), so `numeric_only=True` preserves the old behavior. The golden-output check confirms that.

### 13.3 File order (so rules visibly fire)

| Order | File | Patterns | What the audience sees |
|---|---|---|---|
| 1 | `clean.py` | append, iteritems, **plus a Python list `.append()`** | Two unknown errors → Nimble lookups → rules R1, R2 learned |
| 2 | `metrics.py` | mean / groupby().mean() | Unknown → lookup → rule R3 |
| 3 | `report.py` | append, iteritems | **R1, R2 fire. First try, no web** |
| 4 | `export.py` | iteritems, line_terminator | R2 fires; one new lookup → R4 |
| 5 | `summary.py` | append, mean | **R1, R3 fire. First try, no web** |
| 6 | `index_utils.py` | Int64Index, is_monotonic | Two new patterns late in the run: it still handles unknowns |

**The list `.append()` trap.** `clean.py` also uses an ordinary Python list's `.append()`, with a test covering it. A too-broad "replace every `.append`" fix breaks that test and gets rolled back. This is realistic (real code mixes both) and gives a genuine example of a bad fix being caught.

### 13.4 Suggested functions

| File | Functions |
|---|---|
| `clean.py` | `merge_batches(frames)` (DataFrame.append in a loop), `column_types(df)` (iteritems), `collect_ids(rows)` (list.append) |
| `metrics.py` | `avg_by_region(df)` (groupby().mean()), `overall_mean(df)` (df.mean()) |
| `report.py` | `build_rows(df)` (iteritems), `add_total_row(df)` (append) |
| `export.py` | `to_csv_text(df)` (line_terminator), `header_map(df)` (iteritems) |
| `summary.py` | `summarize(frames)` (append + mean) |
| `index_utils.py` | `make_index(ids)` (Int64Index), `is_sorted(idx)` (is_monotonic) |

Fixture: `data/sales.csv`, about 30 rows with `region` (text), `rep` (text), `units` (int), `revenue` (float), `date` (text).

### 13.5 Environments

pandas 1.5.3 may not install on Python 3.12, so pin 3.11 with uv:

```bash
uv venv --python 3.11 .venv-old
uv pip install --python .venv-old "pandas==1.5.3" "numpy<2" pytest
uv venv --python 3.11 .venv-new
uv pip install --python .venv-new "pandas==2.2.*" "numpy<2" pytest
```

Confirm: the old environment is all green; the new one fails exactly as planned. Generate `golden/*.json` in the old environment.

---

## 14. Sponsors: roles, pain points, lines for judges

To be upfront: Evergreen's main problems (stale rules files, postponed upgrades) belong to every engineering team, not specifically to any sponsor. What it does for each sponsor is give their product a job where it's the right tool.

### Liquid: "small models are worth using in real agent loops"

- **Their challenge:** convincing developers a small on-device model beats sending every step to a big cloud model.
- **Role:** decides on every failure, in milliseconds, "which known rule is this, or is it new?" The big model is only called to write patches. Matching never sends code off the laptop.
- **Show on screen:** match latency per failure.
- **Line:** "Liquid decides on every failure, in milliseconds, whether we even need the big model."

### Nimble: "agents need the live web, not frozen training data"

- **Their challenge:** showing why agents need real-time web data when the model "already knows things."
- **Role:** fetches live migration notes and GitHub issues for unknown errors. Every lookup becomes a reusable rule, so each search becomes permanent knowledge.
- **Be honest:** pandas 2.0 is from 2023, so the model probably knows these fixes already. The demo shows the mechanism; the live web matters most for brand-new releases.
- **Framing:** continuous upgrades across every dependency, not once a year. Don't pitch "fewer searches."
- **Line:** "The model's knowledge ends at its training date. New releases don't. Nimble fills that gap."

### Tinybird / RawTree: "a database built for agents"

- **Their challenge:** getting developers to see an analytics database as agent infrastructure.
- **Role:** the agent's entire memory: rulebook, every attempt, every test count, every lookup, as raw events with no schema design. All charts are SQL queries against it. Stretch: a second repo loads the rules and starts out already knowing them.
- **Line:** "The agent doesn't carry its history in the prompt. It queries it from RawTree."

### AWS: "long-running agents on Bedrock that stay affordable"

- **Their challenge:** agent cost grows with context, so long tasks get expensive. AWS already sells Amazon Q code transformation for Java upgrades, so it sees upgrades as a customer problem.
- **Role:** Bedrock writes every patch through a forced tool call. The prompt on file 50 is the same size as on file 1, so cost per file stays flat.
- **Line:** "Same cost per file on file 50 as on file 1."

### Not used

OpenAI (we chose Bedrock), Black Forest Labs, Broccoli. Don't mention them in the pitch.

---

## 15. Proof: what we measure

### 15.1 Conditions

| Condition | What it does | Purpose |
|---|---|---|
| **Rules off** (`--no-rules`) | Every error treated as new: web lookup every time, no rules reused | Isolates the value of the rulebook |
| **Rules on** (Evergreen) | Verified rules carry forward | Our system |
| Naive prompt (computed, not run) | What a chat-style agent's prompt would be if it kept everything | Shows the flat-prompt effect |

Same repo, same model, same temperature, same order. Run each condition at least twice if time allows, and report every run.

### 15.2 Metrics

- Tests passing at the end (and "needs a human" count)
- Attempts per file, web lookups per file, **LLM tokens per file**, instant (zero-token) fixes
- Prompt tokens per attempt vs. naive
- Rollbacks and patches rejected by guard
- Total time and total tokens
- Liquid match latency; Nimble lookup latency

### 15.3 Charts for the results slide

1. **Learning curve:** attempts, web lookups, and LLM tokens per file, rules on vs. off. With instant rules, the tokens line drops to zero on files covered by trusted rules.
2. **Flat prompt:** prompt tokens per attempt, Evergreen vs. naive.
3. **Staircase:** tests passing over time. It only ever goes up: the ratchet guarantee made visible.

### 15.4 Live counters on the demo screen

Tests passing · Rules learned · Rules applied · **Instant fixes (0 tokens)** · Web lookups · Rollbacks · Patches rejected by guard · **Human interventions: 0** · Prompt tokens (now) vs. naive

Showing that the system refused bad fixes is more convincing than claiming it never makes any.

---

## 16. The 3-minute demo

**Setup:** terminal with a live log and the counters (use `rich`). Browser tab open on the demo repo's GitHub page. Start the run at 0:00 and take your hands off the keyboard.

| Time | What happens | On screen |
|---|---|---|
| 0:00 | "We just bumped pandas. Most of our 20 tests are red." Start Evergreen | Red test count |
| 0:15 | Problem: every team has a postponed upgrade; it's long and repetitive, and exactly where agents drown in their own output | Terminal running |
| 0:35 | clean.py: unknown error → Nimble lookup (URL on screen) → patch → ratchet check passes → R1, R2 saved | Log + counters |
| 1:00 | Point out any rollback or guard rejection live. If none happens, show the count from the recorded run. **Don't fake one** | Counters |
| 1:25 | report.py, summary.py: Liquid matches R1/R2/R3 → first try, web lookup counter doesn't move | Counters |
| 2:00 | All green → PR on GitHub: one commit per fix, **the new AGENTS.md block** (rules with confidence, version, source), evidence links | Browser |
| 2:20 | Charts: learning curve (LLM tokens per file dropping to zero), flat prompt, staircase. *Stretch:* 20-second recorded clip of a rule being retired on pandas 3.0 | Results slide |
| 2:45 | Sponsor roles, prior art in one sentence, honest limit, close | Final slide |

**Timing target:** the full run finishes in about 90 seconds. Keep files small, use a fast model, fix all of a file's failures in one call. Time a full run by 2:15. If it's too slow, play the recorded run with the counters and say so.

**Backup:** screen recording of a full successful run plus saved RawTree data, in case the Wi-Fi or an API fails.

---

## 17. Pitch lines and claims

**Main line:** "Every coding agent reads a rules file. Nobody keeps it true. Evergreen writes only lessons that tests have proven, scores them by outcome, and retires them when the library moves on."

**Engine line:** "The ratchet fixes one file at a time and never lets a passing test fail, so every lesson in AGENTS.md is one the tests have confirmed."

**Learning line:** "The first file costs a web search and a big-model call. By the fifth, trusted rules fix it with zero LLM tokens."

**Theme line:** "The prompt for file 50 is the same size as for file 1. The agent doesn't carry its history; it queries it."

**Safety line:** "The model will hallucinate. Evergreen's job is to make sure no hallucination reaches the PR."

**Prior art (name it ourselves, one sentence each):**

- Upgrade tools (Amazon Q code transformation, OpenRewrite/Moderne, Grit, Codemod) apply recipes people wrote in advance. Evergreen writes its own, during the run.
- Agent memories are typically LLM-written notes. Evergreen's lessons are proven by tests, scored by outcome, and tied to a version so they can expire. We haven't found a tool that combines all three, to our knowledge.
- Knowledge Triage (the Compaction Cliff paper) assigns fixed labels once. Evergreen learns and corrects itself during the run.

**Say:**

- "Never lets a previously passing test fail."
- "To our knowledge…" before any comparison with existing tools.
- "The demo uses pandas 2.0, which the model may already know. The live web matters most for brand-new releases."

**Never say:**

- "Guarantees no regressions" (only true relative to tests and golden outputs).
- "Existing tools can't do this" without "to our knowledge."
- Any number we haven't measured today.

---

## 18. Judge Q&A

| Likely question | Short answer |
|---|---|
| "Isn't this Amazon Q or OpenRewrite?" | Those apply recipes written in advance. Evergreen writes its own rules mid-run from verified fixes and live docs, and reuses them across files and repos, to our knowledge |
| "What if the tests are weak?" | The ratchet is only as strong as the tests plus golden outputs. That's why it opens a PR for review instead of merging |
| "What if it hallucinates?" | Tests are read-only, cheating patterns are blocked, evidence must come from a real fetch, outputs must match the old version, and a human reviews every commit |
| "Doesn't GitHub review do this?" | Review is the last line of defense. Evergreen reuses its fixes, so a bad fix must be stopped before it becomes a rule and spreads |
| "What if a rule is wrong?" | Rules come only from verified fixes, fire only on matching signatures, are checked on every use, and are demoted after two failures |
| "Why not paste the whole migration guide in the prompt?" | Cost on every file, and details in the middle of long contexts get missed. The rulebook is the part of the guide this repo actually needs |
| "Why whole-file rewrites instead of diffs?" | With small files it's more reliable than applying diffs. Production would use diffs |
| "Does it scale to 500 files?" | Prompt size depends on one file, not the run, and rules make later files cheaper. That's what the charts show |
| "Where's the autonomy?" | Live web lookups, a real PR on GitHub, zero human interventions from red to PR |
| "Why a small model on the laptop?" | Matching runs on every failure: it must be fast and cheap. The big model only writes patches |
| "Doesn't the model already know pandas 2?" | Probably. The mechanism is the point; for last week's release, only the live web has the answer |
| "Why write AGENTS.md instead of keeping rules in the database?" | Every coding agent already reads a rules file at session start. Writing verified rules there makes the memory useful to any agent, not just ours |
| "What about rules humans wrote?" | Evergreen manages only its own marked block. Human rules are left alone; when code following one starts failing after an upgrade, Evergreen flags it |
| "How can zero-token fixes be safe?" | The transform is validated when the rule is born, applied only to the lines the traceback points at, and still goes through the tests and golden outputs |
| "Isn't confidence just a counter?" | Yes, deliberately: success rate from real test outcomes, smoothed so one lucky fix doesn't make a rule trusted. Simple and auditable beats clever here |
| "How does expiry know a rule is stale?" | Each rule stores the tests that proved it. On a new library version, those proofs are re-run; if they fail, the rule is retired with the reason and the release-notes link |

---

## 19. Team split: 3 people

| | Person 1: Agent loop | Person 2: Liquid + Nimble | Person 3: Repo, memory, story |
|---|---|---|---|
| **Owns** | Main loop, Bedrock patcher, guards, ratchet check, rollback, git commits, PR, instant-rule applier | Liquid triage and rule matching, Nimble evidence, changelog fetch (stretch) | Demo repo, environments, golden outputs, RawTree logging and queries, AGENTS.md writer, charts, slides, backup recording |
| **Sponsor they present** | AWS Bedrock | Liquid, Nimble | Tinybird / RawTree |
| **Why this split** | Critical path: everything plugs into the loop | The two sponsor-heavy components, which Liquid and Nimble judges will look at closely | Independent until integration; owns the story and the proof |

**Rule for working in parallel:** every person ships a *stub* of their interface in the first 15 minutes (section 20), so nobody waits on anybody. Person 1 builds against the stubs; real versions swap in at the 1:30 checkpoint.

**Git workflow:** two repos. `evergreen` (the agent, our hackathon repo) and `sales-report` (the demo target; the PR lands there). One branch per person in `evergreen`; merge to `main` at each checkpoint. Secrets in `.env`, never committed.

---

## 20. Interfaces between people

Shared types in `evergreen/types.py` (Person 1 writes this file first, in the first 10 minutes):

```python
from dataclasses import dataclass, field

@dataclass
class Failure:
    test_id: str            # "tests/test_clean.py::test_merge_batches"
    src_file: str           # "src/clean.py"
    exc_type: str           # "AttributeError"
    message: str            # "'DataFrame' object has no attribute 'append'"
    line_no: int | None     # offending line in src_file, from the traceback
    line: str | None        # that line's text
    signature: str          # normalized: "AttributeError: DataFrame.append"

@dataclass
class TestRun:
    passing: set[str]
    failing: list[Failure]

@dataclass
class Rule:
    rule_id: str
    signature: str
    pattern: str
    replacement: str
    regex_find: str | None = None
    regex_replace: str | None = None
    source_url: str | None = None
    proven_on: list[str] = field(default_factory=list)   # ["pandas 2.2.3"]
    proof: list[str] = field(default_factory=list)       # test IDs
    applied: int = 1
    succeeded: int = 1
    status: str = "verified"   # verified | trusted | demoted | retired

@dataclass
class Evidence:
    url: str
    snippet: str
    latency_s: float

@dataclass
class PatchResult:
    new_source: str
    explanation: str
    new_rule: dict | None
    prompt_tokens: int
    output_tokens: int
```

| Function | Owner | Stub to ship in 15 minutes |
|---|---|---|
| `run_tests(repo, venv) -> TestRun` | P1 | Real (it's simple) |
| `patch(path, source, failures, hints, feedback) -> PatchResult` | P1 | Real call on a toy file |
| `patch_ok(old, new) -> (bool, str)` | P1 | Real (section 9) |
| `apply_instant(source, failure, rule) -> str \| None` | P1 | Returns `None` |
| `match_rule(failure, rules) -> Rule \| None` | P2 | Exact signature match |
| `get_evidence(failure) -> Evidence \| None` | P2 | Returns `None` |
| `fetch_changelog(library, version) -> str` | P2 (stretch) | Returns `""` |
| `log(table, row)` / `query(sql) -> list[dict]` | P3 | Append to a local JSONL file |
| `load_rules() -> list[Rule]` / `save_rule_event(...)` | P3 | Local JSON file |
| `golden_ok(repo, venv) -> bool` | P3 | Returns `True` |
| `write_agents_md(repo, rules, retired, needs_human)` | P3 | Writes a minimal block |

---

## 21. Schedule and checkpoints (submit by 3:45; deadline 4:00)

| Time | Person 1: loop | Person 2: Liquid + Nimble | Person 3: repo, memory, story |
|---|---|---|---|
| **First 15 min** | `types.py`; Bedrock Converse call with forced `submit_patch` working on a toy file | `llama-server` running LFM2.5; one grammar-constrained answer working; one Nimble search returns results | Both environments built; old = green, new = intended failures. RawTree database + key; `rtree status --json` |
| **→ 1:30** | `run_tests` + JUnit parsing, snapshot/rollback, guards, ratchet check, git commit | Real `match_rule` (per-call grammar + deterministic check + exact-match fallback); real `get_evidence` (domain preference + snippet) | All 6 files and ~20 tests; golden record/check; RawTree `log` with background flush |
| **1:30 checkpoint** | **One file fixed end to end: triaged, matched or looked up, patched, checked, committed, rule saved** | | |
| **→ 2:15** | Full loop across all files; "needs a human"; push + `gh pr create` | Timing numbers for Liquid and Nimble; evidence logged | AGENTS.md writer (marker block); PR body template; counters display |
| **2:15 checkpoint** | **Full run: rules firing on later files, AGENTS.md in the PR. RECORD IT IMMEDIATELY (backup video)** | | |
| **→ 2:45** | Instant-rule path (regex validated at birth, line-scoped); `--no-rules` flag | Run rules-on and rules-off (twice each if time) | Three charts from RawTree (+ tokens-per-file chart if instant rules work); start slides |
| **2:45 checkpoint** | **Charts exist; instant rules work or are cut** | | |
| **2:45 → 3:00** | Bug fixes only | Stretch: expiry on pandas 3.0 (only if 2:15 passed) | Slides |
| **3:00** | **Code freeze** | | |
| **3:00 → 3:45** | Rehearse the live run twice | Check the backup recording plays | Finish slides + README; submit (repo links, README, video, slides) |

**Priority order if time runs short** (build top-down, stop wherever time runs out):

1. **Must have:** ratchet loop red → green on the demo repo, rules learned and reused, guards, AGENTS.md written, PR opened, backup recording.
2. **Should have:** golden outputs, instant rules, rules-off comparison, the three charts, live counters.
3. **Stretch:** expiry on pandas 3.0, cross-run memory on a second repo, `ratchet-verify` commit status.

---

## 22. Repo layout

```
evergreen/                      # the agent (our hackathon repo)
  evergreen/types.py            # P1: shared dataclasses
  evergreen/loop.py             # P1: main loop
  evergreen/testrun.py          # P1: pytest + JUnit parsing
  evergreen/patcher.py          # P1: Bedrock Converse + submit_patch tool
  evergreen/guards.py           # P1: patch guard + tests hash
  evergreen/instant.py          # P1: zero-token rule application
  evergreen/gitops.py           # P1: snapshot, rollback, commit, push, PR
  evergreen/liquid.py           # P2: llama-server client, grammar, fallback
  evergreen/evidence.py         # P2: Nimble search + snippet
  evergreen/changelog.py        # P2: release notes fetch (stretch)
  evergreen/memory.py           # P3: RawTree log/query + local rule cache
  evergreen/golden.py           # P3: record/check golden outputs
  evergreen/agents_md.py        # P3: AGENTS.md writer
  evergreen/display.py          # P3: rich live counters
  bench/charts.py               # P3: charts from RawTree
  run.py                        # CLI entry point
  README.md

sales-report/                   # demo target (separate GitHub repo; PR lands here)
  src/clean.py  src/metrics.py  src/report.py  src/export.py  src/summary.py  src/index_utils.py
  tests/test_*.py               # ~20 tests, read-only for the agent
  data/sales.csv
  golden/                       # recorded on pandas 1.5
  AGENTS.md                     # human-written rules + Evergreen block
  requirements.txt
```

`run.py` usage:

```bash
python run.py --repo ../sales-report --venv ../sales-report/.venv-new --run-id r1            # rules on
python run.py --repo ../sales-report --venv ../sales-report/.venv-new --run-id r2 --no-rules # ablation
```

---

## 23. Setup and code snippets

### 23.1 Environment variables (`.env`, never committed)

```bash
AWS_REGION=us-west-2              # whichever region has your Claude model
BEDROCK_MODEL_ID=...              # check the Bedrock console; use a fast model
NIMBLE_API_KEY=...
RAWTREE_API_KEY=rt_...
RAWTREE_DATABASE=evergreen
RAWTREE_ORG=...
# GitHub: run `gh auth login` once
```

### 23.2 Installs

```bash
pip install boto3 requests rich matplotlib          # agent environment
brew install llama.cpp                               # provides llama-server on macOS
# download the LFM2.5 GGUF (1.2B; 350M as a faster fallback) from huggingface.co/LiquidAI (confirm file name)
llama-server -m LFM2.5-1.2B-Q4_K_M.gguf --port 8080
npx skills add rawtreedb/agent-skills                # RawTree agent skill
# install the rtree CLI per RawTree's CLI quickstart, then:
rtree key create --name evergreen --permission read_write
rtree status --json
```

### 23.3 Bedrock patch call (Converse API, forced tool)

```python
import boto3
brt = boto3.client("bedrock-runtime", region_name=AWS_REGION)

PATCH_TOOL = {"toolSpec": {
    "name": "submit_patch",
    "description": "Submit the complete fixed file and, if the fix generalizes, a rule.",
    "inputSchema": {"json": {
        "type": "object",
        "properties": {
            "new_file": {"type": "string"},
            "explanation": {"type": "string"},
            "new_rule": {"type": "object", "properties": {
                "signature": {"type": "string"}, "pattern": {"type": "string"},
                "replacement": {"type": "string"}, "regex_find": {"type": "string"},
                "regex_replace": {"type": "string"}, "source_url": {"type": "string"}}}},
        "required": ["new_file", "explanation"]}}}}

SYSTEM_PROMPT = (
    "You are upgrading a Python repo from pandas 1.5 to pandas 2.2. "
    "Fix only what the listed failures require and preserve pandas 1.5 behavior exactly. "
    "Never edit tests. Never add try/except, pytest.skip, or xfail. Never delete functions. "
    "Return the complete file through submit_patch. If the fix generalizes to other files, "
    "propose a rule, including a regex_find/regex_replace that fixes the offending line alone. "
    "Only use a source_url from the evidence provided.")

def call_patch(user_prompt):
    resp = brt.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        toolConfig={"tools": [PATCH_TOOL], "toolChoice": {"tool": {"name": "submit_patch"}}},
        inferenceConfig={"temperature": 0, "maxTokens": 4000})
    block = next(c for c in resp["output"]["message"]["content"] if "toolUse" in c)
    return block["toolUse"]["input"], resp["usage"]   # usage: inputTokens, outputTokens
```

**(verify)** that forced `toolChoice` is supported for the model you pick.

The user prompt contains: the file path and full content; each failure (test ID, exception, message, offending line); for each failure either the matched rule or the evidence snippet with its URL; on a retry, the previous attempt's failure or guard rejection reason.

### 23.4 Liquid rule matcher (llama-server)

```python
import requests

def match_rule(f, rules):
    usable = [r for r in rules if r.status in ("verified", "trusted")]
    if not usable:
        return None
    ids = [r.rule_id for r in usable]
    grammar = "root ::= " + " | ".join(f'"{i}"' for i in ids + ["unknown"])
    listing = "\n".join(f"{r.rule_id}: {r.signature} -> {r.replacement}" for r in usable)
    prompt = (f"Known fixes:\n{listing}\n\nError: {f.signature}\nLine: {f.line}\n"
              "Which known fix applies? Answer with its ID, or unknown.\nAnswer: ")
    try:
        out = requests.post("http://localhost:8080/completion",
                            json={"prompt": prompt, "grammar": grammar,
                                  "n_predict": 4, "temperature": 0},
                            timeout=10).json()["content"].strip()
    except Exception:
        out = next((r.rule_id for r in usable if r.signature == f.signature), "unknown")  # fallback
    rule = next((r for r in usable if r.rule_id == out), None)
    if rule and rule.signature.split(":")[0] != f.exc_type:   # deterministic double-check
        return None
    return rule
```

### 23.5 Nimble evidence

```python
import requests, time

PREFERRED = ("pandas.pydata.org", "github.com/pandas-dev")

def get_evidence(f):
    t0 = time.time()
    r = requests.post("https://nimble-retriever.webit.live/search",
                      headers={"Authorization": f"Bearer {NIMBLE_API_KEY}"},
                      json={"query": f"pandas 2.0 {f.signature}"},   # verify parameter names in Nimble docs
                      timeout=20)
    results = r.json()   # pick the first result from a PREFERRED domain, else the top result
    # snippet: ~500 characters around the API name (e.g. "append") from the result's content
    ...
```

Nimble's search has a fast mode (1 credit per search) and a deep mode that also extracts full page content. Use fast mode plus a targeted extract if needed.

### 23.6 pytest JUnit parsing

```python
import subprocess, xml.etree.ElementTree as ET

def run_tests(repo, venv):
    subprocess.run([f"{venv}/bin/python", "-m", "pytest", "-q",
                    "--junitxml=report.xml", "-p", "no:cacheprovider"],
                   cwd=repo, capture_output=True)
    root = ET.parse(f"{repo}/report.xml").getroot()
    passing, failing = set(), []
    for tc in root.iter("testcase"):
        tid = f'{tc.get("classname")}::{tc.get("name")}'
        bad = tc.find("failure")
        if bad is None:                 # note: never use `or` on Elements; empty Elements are falsy
            bad = tc.find("error")
        if bad is not None:
            failing.append(parse_failure(tid, bad.get("message", ""), bad.text or ""))
        elif tc.find("skipped") is None:
            passing.add(tid)
    return TestRun(passing, failing)
```

`parse_failure` extracts the exception type, the last traceback frame inside `src/` (file and line number), and builds the normalized signature.

### 23.7 RawTree logging without slowing the demo

```python
import json, queue, subprocess, threading, time

_q = queue.Queue()

def log(table, row):
    _q.put((table, row))

def _flusher():
    while True:
        time.sleep(2)
        batch = {}
        while not _q.empty():
            t, r = _q.get()
            batch.setdefault(t, []).append(r)
        for t, rows in batch.items():
            subprocess.run(["rtree", "insert", "--table", t, "--data", json.dumps(rows), "--json"],
                           capture_output=True)

threading.Thread(target=_flusher, daemon=True).start()

def query(sql):
    out = subprocess.run(["rtree", "query", "--json", sql], capture_output=True, text=True)
    return json.loads(out.stdout)
```

Also append every row to a local JSONL file, so nothing is lost if RawTree hiccups.

### 23.8 Golden outputs

```python
# golden.py: run with <venv>/bin/python golden.py record   (old env)   or   check   (new env)
import json, sys, pandas as pd
sys.path.insert(0, "src")
import clean, metrics, report, export, summary, index_utils

df = pd.read_csv("data/sales.csv")
CASES = {
    "overall_mean": lambda: metrics.overall_mean(df),
    "avg_by_region": lambda: metrics.avg_by_region(df),
    # ... one entry per public function
}

def norm(x):
    if isinstance(x, (pd.DataFrame, pd.Series)):
        return json.loads(x.to_json(orient="split", double_precision=6))   # values, not dtypes
    if isinstance(x, pd.Index):
        return [str(v) for v in x]
    return x if isinstance(x, (int, float, str, bool, list, dict)) else repr(x)

if sys.argv[1] == "record":
    json.dump({k: norm(f()) for k, f in CASES.items()}, open("golden/golden.json", "w"))
else:
    want = json.load(open("golden/golden.json"))
    got = {k: norm(f()) for k, f in CASES.items()}
    sys.exit(0 if got == want else 1)
```

### 23.9 Pull request

```bash
git -C ../sales-report checkout -b evergreen/pandas-2
# ... one commit per verified fix, made by the loop ...
git -C ../sales-report push -u origin evergreen/pandas-2
gh pr create --repo <owner>/sales-report --base main --head evergreen/pandas-2 \
  --title "Upgrade pandas 1.5 → 2.2 (Evergreen)" --body-file pr_body.md
```

PR body: summary counts, a table of fixes (file, rule IDs, attempts), rules learned (with sources and confidence), guard rejections and rollbacks, "needs a human" list, and a note that AGENTS.md was updated.

---

## 24. Fallbacks and risks

### 24.1 Fallbacks

| If this breaks | Do this |
|---|---|
| `llama-server` / LFM | Exact-signature matching; say so honestly. Try the 350M model if 1.2B is slow |
| Nimble slow or down | Use evidence cached from the recorded run; still show the URLs |
| Bedrock rate limits | Smaller/faster model; fewer ablation runs |
| RawTree trouble | Local JSONL log; batch-insert later; charts from JSONL |
| A pattern refuses to fix | "Needs a human" path already covers it |
| Full run too slow for 3 minutes | Play the recorded run with counters; say so |
| Wi-Fi fails during the demo | Recorded video + saved data |

### 24.2 Risks

| Risk | Mitigation |
|---|---|
| Two stories (upgrade tool vs. agent memory) confuse judges | Headline is the memory: "the rules file that proves, scores, and expires itself." The upgrade is how we demo it |
| Overclaiming novelty | Use the wording in 12.5; name prior art ourselves |
| Instant rules apply a wrong fix | Validated at birth, line-scoped, still ratchet-checked, fall back to LLM |
| Model cheats to pass tests | Read-only tests, patch guard, golden outputs |
| Expiry beat not finished | It's a stretch goal; the must-have tier tells a complete story |
| Tinybird prize requires classic Tinybird, not RawTree | Ask the rep in the first 15 minutes; events are the same either way |
| Demo repo breakages behave differently than expected | Person 3 verifies every planted breakage in the first 15 minutes |
| Running out of time | Priority order in section 21; code freeze at 3:00 |

---

## 25. Verify list

- [ ] Tinybird rep: does the prize count RawTree, classic Tinybird, or either?
- [ ] Every planted pandas 2.0 breakage raises an error on 2.2 (not just a warning); all tests green on 1.5.3.
- [ ] Bedrock: which Claude models your account has, region, and forced `toolChoice` support.
- [ ] Nimble: search request parameters, response shape, and speed.
- [ ] `llama-server` `/completion` accepts `grammar`; LFM2.5 file name; latency per match on the laptop (1.2B vs 350M).
- [ ] RawTree: `rtree` install, SQL dialect, any free-plan limits.
- [ ] The "nearly 400,000 rules files on public GitHub" figure: open the Compaction Cliff paper before it goes on a slide.
- [ ] ruff `NPY201` claim, only if you mention it.
- [ ] (Stretch) pandas 3.0: `select_dtypes(include="object")` on string columns behaves as expected; what else fails on 3.0.
- [ ] Any statement about how Cursor, Windsurf, Devin, or Claude Code memories work.

---

## 26. Submission checklist

- [ ] `evergreen` repo public, with README: problem, how it works, architecture diagram, where each sponsor tool is used (with file names), how to run, results (charts), honest limits, prior art.
- [ ] `sales-report` repo public, with the PR link and the generated AGENTS.md.
- [ ] Demo video (the backup recording from 2:15).
- [ ] Slides (5): problem, how it works, live demo, results, sponsors + prior art + limits.
- [ ] Submitted by **3:45 PM** (deadline 4:00).
