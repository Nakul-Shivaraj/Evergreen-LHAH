import { query, rows, safeRunId } from "../../../lib/rawtree";

export const dynamic = "force-dynamic";

// Field names follow README section 11; every read tolerates missing fields.
const num = (v) => (typeof v === "number" ? v : Number(v) || 0);
const truthy = (v) => v === true || v === 1 || v === "1" || v === "true";

export async function GET(request) {
  const runs = await query(
    "SELECT run_id, max(at) AS last FROM test_runs WHERE run_id != 'selftest' GROUP BY run_id ORDER BY last DESC LIMIT 20"
  );
  const asked = safeRunId(new URL(request.url).searchParams.get("run"));
  const runId = asked || runs[0]?.run_id;
  if (!runId) return Response.json({ runs: [], runId: null });

  const [tests, attempts, ruleEvents, evidence, patchRows, testResults] = await Promise.all([
    rows("test_runs", runId),
    rows("attempts", runId),
    rows("rule_events", runId),
    rows("evidence", runId),
    rows("patches", runId),
    rows("test_results", runId, 5000),
  ]);
  const bySeq = (a, b) => num(a.at) - num(b.at) || num(a.seq) - num(b.seq);
  tests.sort(bySeq); ruleEvents.sort(bySeq); evidence.sort(bySeq);
  attempts.sort((a, b) => num(a.attempt) - num(b.attempt) || bySeq(a, b));

  // Current state of each rule = its latest event.
  const rules = {};
  const STATUSES = ["verified", "trusted", "demoted", "retired"];
  for (const e of ruleEvents) {
    const r = (rules[e.rule_id] ||= { rule_id: e.rule_id, reused: 0, failed: 0, appliedField: 0, status: "verified" });
    if (e.event === "succeeded") r.reused++;
    if (e.event === "failed") r.failed++;
    if (typeof e.applied === "number") r.appliedField = Math.max(r.appliedField, e.applied);  // agent's running count
    for (const k of ["signature", "pattern", "replacement", "source_url", "confidence", "proven_on"])
      if (e[k] !== undefined && e[k] !== null) r[k] = e[k];
    if (STATUSES.includes(e.status)) r.status = e.status;          // the rule's own status field
    else if (STATUSES.includes(e.event)) r.status = e.event;       // or a status-changing event
  }
  for (const r of Object.values(rules)) {
    r.applied = Math.max(r.appliedField, 1 + r.reused + r.failed);   // birth + every reuse
    r.inAgentsMd = r.status === "verified" || r.status === "trusted";
  }

  // Kept commits, oldest first. Diffs are capped so one huge patch can't bloat every poll.
  patchRows.sort((a, b) => num(a.attempt) - num(b.attempt) || bySeq(a, b));
  const patches = patchRows.map((p) => ({
    file: p.file,
    sha: String(p.commit_sha || "").slice(0, 7),
    mode: p.mode,
    rules: Array.isArray(p.rule_ids) ? p.rule_ids : p.rule_ids ? [p.rule_ids] : [],
    attempt: num(p.attempt),
    diff: String(p.diff || "").slice(0, 6000),
  }));

  // Test grid: one row per test, one column per suite run; the latest status wins per cell.
  testResults.sort(bySeq);
  const suites = [...new Set(testResults.map((t) => num(t.suite)))].sort((a, b) => a - b);
  const cells = {}, sigs = {}, suiteInfo = {};
  for (const t of testResults) {
    (cells[t.test_id] ||= {})[num(t.suite)] = t.status;
    if (t.signature) sigs[t.test_id] = t.signature;
    suiteInfo[num(t.suite)] = { file: t.file, kept: truthy(t.kept), attempt: num(t.attempt) };
  }
  const lastSuite = suites[suites.length - 1];
  const grid = {
    suites: suites.map((s) => ({ suite: s, ...suiteInfo[s] })),
    tests: Object.keys(cells).sort().map((id) => ({
      id,
      statuses: suites.map((s) => cells[id][s] || null),
      signature: cells[id][lastSuite] !== "passed" ? sigs[id] || null : null,
    })),
  };

  const last = tests[tests.length - 1] || {};
  const accepted = attempts.filter((a) => truthy(a.accepted));
  const counters = {
    passing: num(last.passing),
    total: num(last.total) || num(last.passing) + num(last.failing),
    rulesLearned: Object.values(rules).filter((r) => r.status !== "proposed").length,
    rulesApplied: ruleEvents.filter((e) => e.event === "succeeded").length,   // successful reuses
    instantFixes: accepted.filter((a) => a.fixer === "liquid_quick" || truthy(a.instant) || num(a.output_tokens) === 0).length,
    webLookups: evidence.length,                                          // every lookup, cached or live
    cachedLookups: evidence.filter((e) => truthy(e.cached)).length,
    attempts: attempts.length,
    rollbacks: attempts.filter((a) => truthy(a.rolled_back)).length,
    guardRejections: attempts.filter((a) => truthy(a.rejected_by_guard)).length,
    llmTokens: attempts.reduce((s, a) => s + num(a.output_tokens) + num(a.prompt_tokens), 0),
  };

  return Response.json({
    runs: runs.map((r) => r.run_id),
    runId,
    counters,
    staircase: tests.map((t) => ({ at: num(t.at), passing: num(t.passing), total: num(t.total) })),
    attemptsTotal: attempts.length,
    prompt: attempts.map((a, i) => ({
      attempt: num(a.attempt) || i + 1,
      prompt: num(a.prompt_tokens),
      naive: num(a.naive_prompt_tokens),
    })),
    rules: Object.values(rules),
    patches,
    grid,
    feed: attempts.slice(-12).reverse().map((a) => ({
      file: a.file,
      accepted: truthy(a.accepted),
      rolledBack: truthy(a.rolled_back),
      guard: truthy(a.rejected_by_guard),
      web: truthy(a.used_web),
      tokens: num(a.output_tokens) + num(a.prompt_tokens),   // same basis as the Liquid tokens tile
      rules: a.rule_ids || [],
    })),
    evidence: evidence.slice(-8).reverse().map((e) => ({ signature: e.signature, url: e.url || null, cached: truthy(e.cached) })),
  });
}
