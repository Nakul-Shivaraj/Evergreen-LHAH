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

  const [tests, attempts, ruleEvents, evidence] = await Promise.all([
    rows("test_runs", runId),
    rows("attempts", runId),
    rows("rule_events", runId),
    rows("evidence", runId),
  ]);

  // Current state of each rule = its latest event.
  const rules = {};
  for (const e of ruleEvents) {
    const r = (rules[e.rule_id] ||= { rule_id: e.rule_id, applied: 0, failed: 0 });
    if (e.event === "applied") r.applied++;
    if (typeof e.applied === "number") r.applied = Math.max(r.applied, e.applied);   // agent's running count
    if (e.event === "failed") r.failed++;
    for (const k of ["signature", "pattern", "replacement", "source_url", "confidence", "proven_on"])
      if (e[k] !== undefined && e[k] !== null) r[k] = e[k];
    r.status = e.event;
  }

  const last = tests[tests.length - 1] || {};
  const accepted = attempts.filter((a) => truthy(a.accepted));
  const counters = {
    passing: num(last.passing),
    total: num(last.total) || num(last.passing) + num(last.failing),
    rulesLearned: Object.values(rules).filter((r) => r.status !== "proposed").length,
    rulesApplied: ruleEvents.filter((e) => e.event === "applied").length,
    instantFixes: accepted.filter((a) => truthy(a.instant) || num(a.output_tokens) === 0).length,
    webLookups: evidence.filter((e) => !truthy(e.cached)).length,
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
    prompt: attempts.map((a, i) => ({
      attempt: num(a.attempt) || i + 1,
      prompt: num(a.prompt_tokens),
      naive: num(a.naive_prompt_tokens),
    })),
    rules: Object.values(rules),
    feed: attempts.slice(-12).reverse().map((a) => ({
      file: a.file,
      accepted: truthy(a.accepted),
      rolledBack: truthy(a.rolled_back),
      guard: truthy(a.rejected_by_guard),
      web: truthy(a.used_web),
      tokens: num(a.output_tokens),
      rules: a.rule_ids || [],
    })),
    evidence: evidence.slice(-8).reverse().map((e) => ({ signature: e.signature, url: e.url, cached: truthy(e.cached) })),
  });
}
