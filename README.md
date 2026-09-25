# Evergreen

**The AGENTS.md that writes, tests, and expires itself.**

Long Horizon Agents Hack · September 25, 2026 · Saahith Veeramaneni, Nakul Shivaraj, Dhanraj Pandya

Coding agents start every session knowing nothing, and the rules files teams write for them
(AGENTS.md, CLAUDE.md) go stale the day a library changes. Evergreen runs a coding agent through a
real upgrade (pandas 1.5 → 2.2), fixes one file at a time, keeps a fix only if no passing test breaks,
and turns every kept fix into a scored, sourced, versioned rule written into AGENTS.md. Its memory
lives in a database, not the prompt, so file fifty costs the same as file one.

The original plan, with the full design rationale, is in [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md).
Where it disagrees with this README (it assumed AWS Bedrock), this README wins.

## How it works

```
 pytest (JUnit XML) ──► failure: test, file, line, error signature
                              │
            rule for this signature? ── yes ──► apply it (0 model tokens; still checked)
                              │ no
            Nimble: live pandas docs for the error (cached after the first lookup)
                              │
            Liquid LFM2.5-8B-A1B on the laptop patches the offending line
                              │
            guards: parses? tests untouched? no skip / except-pass? not too big?
                              │
            ratchet: every previously passing test still passes, at least one more passes,
                     golden outputs still match pandas 1.5
                   ├── yes → keep, git commit, save/strengthen the rule
                   └── no  → roll back, retry with the failure as feedback (3 tries, then "needs a human")
                              │
            every event ──► RawTree `evergreen` database ──► Vercel dashboard (live)
                              │
            all green ──► AGENTS.md block written
```

## Sponsor tools (3)

| Tool | Job | Where |
|---|---|---|
| **Liquid** (LFM2.5-8B-A1B, llama.cpp) | The only model. Writes every patch on the laptop; confirms near-miss rule matches. No cloud AI anywhere. | agent laptop, `LIQUID_URL` |
| **Nimble** | Live docs for errors the agent hasn't seen, restricted to pandas.pydata.org, falling back to the open web. | `evergreen/evidence.py`, `evergreen/changelog.py` |
| **Tinybird / RawTree** | The agent's memory: every attempt, rule event, test run and lookup. All dashboard numbers are SQL over it. | `evergreen/memory.py`, `dashboard/` |

## Repo layout

```
evergreen/
  types.py        shared dataclasses: Failure, TestRun, Rule, Evidence, PatchResult (the contract)
  liquid.py       match_rule(): exact signature, then same exception + API name; Liquid confirms near misses
  evidence.py     get_evidence(): Nimble search, snippet centered on the deprecation sentence, disk cache
  changelog.py    fetch_changelog() + affected_rules() for the expiry pass (stretch)
  memory.py       log()/flush()/query(): local runs/events.jsonl + RawTree over HTTP, 2 s background flush
  agents_md.py    writes only inside the <!-- evergreen:start/end --> block of AGENTS.md
  golden.py       golden-output check against pandas 1.5, called after every candidate patch
  # From the agent laptop, to be merged (see "Merging the agent code" below):
  testrun.py  patcher.py  guards.py  instant.py  gitops.py  loop.py  display.py   + run.py at the root
dashboard/        Next.js app deployed on Vercel (Root Directory = dashboard)
check_integration.py   end-to-end check of everything except the patcher, against the demo repo
.evidence_cache.json   pre-warmed Nimble lookups for the demo's failures (public docs only)
INTEGRATION_HANDOFF.txt  detailed wiring notes for each service
docs/PROJECT_BRIEF.md    the original plan
```

Demo target: [`Nakul-Shivaraj/sales-report`](https://github.com/Nakul-Shivaraj/sales-report):
6 source files, 19 tests. All pass on pandas 1.5.3; on pandas 2.2.3, 14 fail and 5 pass. Includes the
list-`.append()` trap test and golden outputs recorded on pandas 1.5.

## Setup on the agent laptop

1. **Code and demo repo**, side by side:
   ```
   git clone https://github.com/Nakul-Shivaraj/Evergreen-LHAH.git
   git clone https://github.com/Nakul-Shivaraj/sales-report.git
   ```
2. **Python 3.11** (pandas 1.5.3 has no wheels for newer Python), with [uv](https://docs.astral.sh/uv/):
   ```
   cd Evergreen-LHAH
   uv venv -p 3.11 .venv && uv pip install -p .venv requests python-dotenv pytest rich
   cd ../sales-report
   uv venv -p 3.11 .venv-old && uv pip install -p .venv-old "pandas==1.5.3" "numpy<2" pytest
   uv venv -p 3.11 .venv-new && uv pip install -p .venv-new "pandas==2.2.3" "numpy<2" pytest
   ```
3. **Liquid**: download a llama.cpp release for your OS and the model
   `LiquidAI/LFM2.5-8B-A1B-GGUF` (Q4_K_M, ~5 GB) from Hugging Face, then:
   ```
   llama-server -m LFM2.5-8B-A1B-Q4_K_M.gguf --port 8080
   ```
4. **Keys**: a `.env` in `Evergreen-LHAH/` (git-ignored; get the values from Saahith or
   `vercel env pull .env.local` if you own the Vercel project):
   ```
   NIMBLE_API_KEY=...
   RAWTREE_API_KEY=...          # key "evergreen-agent", read_write
   RAWTREE_DATABASE=evergreen
   RAWTREE_ORG=tokensand
   RAWTREE=1
   LIQUID_URL=http://localhost:8080
   ```
5. **Check**: `.venv/bin/python check_integration.py ../sales-report` must print `ALL CHECKS PASS`.

## Running a demo run

```
.venv/bin/python run.py --repo ../sales-report --venv ../sales-report/.venv-new --run-id <new-id>
```
(`run.py` arrives with the agent code; the flags follow the brief, adjust if the merged version differs.)
Use a fresh `--run-id` each time. The dashboard picks the newest run automatically.

**Verify it's really logging** (don't take anyone's word for it): before the run, and every few
seconds during it,
```
set -a; . ./.env; set +a
curl -s -X POST "https://api.rawtree.com/v1/query?database=evergreen" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" -H "Content-Type: application/json" \
  -d '{"sql":"SELECT run_id, count() AS rows, max(passing) AS best FROM test_runs GROUP BY run_id"}'
```
Your new run ID must appear and its row count must climb.

## Dashboard (Vercel)

- Project settings: **Root Directory = `dashboard`**, Framework = Next.js, Production Branch = `main`.
- Env vars: `RAWTREE_DASHBOARD_KEY` (key "evergreen-dashboard", read_only) and `RAWTREE_DATABASE=evergreen`.
- It queries RawTree only from server code (`dashboard/app/api/run/route.js`), polls every 1.5 s, and
  ignores `run_id = 'selftest'` (rows from `check_integration.py`). `<site>/api/run` shows the raw JSON.

## RawTree tables (database `evergreen`, created on first insert)

| Table | One row per | Main fields |
|---|---|---|
| `test_runs` | full pytest run | run_id, at, passing, failing, total |
| `attempts` | patch attempt | file, attempt, accepted, rolled_back, rejected_by_guard, used_web, prompt_tokens, naive_prompt_tokens, output_tokens |
| `rule_events` | rule change | rule_id, event (proposed/verified/applied/succeeded/failed/demoted/retired), signature, pattern, replacement, confidence, source_url, proven_on |
| `evidence` | Nimble lookup | signature, url, latency_s, cached |

Every row carries `run_id` and `at` (epoch seconds). API keys cover the whole hackathon cluster, so
never log secrets.

## Merging the agent code

The working agent (Liquid patcher, test runner, guards, loop) was built on the agent laptop in a
separate repo. To bring it in:

```
cd Evergreen-LHAH && git checkout -b agent-merge
# copy the agent's modules into evergreen/ and run.py into the root
git add -A && git commit -m "Merge agent loop from the agent laptop"
```

Rules while merging:
- **Keep this repo's** `evergreen/types.py`, `memory.py` (HTTP, retries, no `rtree` CLI) and
  `evidence.py`. If the agent has its own versions, adapt the agent's calls to these, not the reverse.
- Rules loaded with `memory.load_rules()` are dicts: convert with `Rule(**d)` before `match_rule`.
- A new rule's `signature` comes from the failure (`AttributeError: DataFrame.append`), never from
  model output: `match_rule` and `agents_md.py` key on it.
- Point the loop at `sales-report` (19 tests), not the older 21-test demo repo.
- Then: `check_integration.py`, one full run with a fresh run ID, confirm it on the dashboard, push
  the branch, and merge to `main` once it is green.

## Status

| Piece | State |
|---|---|
| Nimble evidence + changelog, rule matcher, memory (HTTP), AGENTS.md writer, golden check | on `main`, tested (`check_integration.py`: all pass) |
| Demo repo `sales-report` | on GitHub, 19 tests, 14 red on pandas 2.2.3 |
| RawTree `evergreen` database + keys | live; agent runs r1/r2 logged from the agent laptop |
| Vercel dashboard | deployed from `dashboard/` |
| Liquid patcher, test runner, guards, loop, `run.py` | working on the agent laptop, **not yet merged** |
