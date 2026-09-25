"use client";
import { useEffect, useState } from "react";

function Line({ points, max, color, height = 140 }) {
  if (points.length < 2) return null;
  const w = 600;
  const xs = (i) => (i / (points.length - 1)) * w;
  const ys = (v) => height - (max ? (v / max) * (height - 8) : 0) - 4;
  const d = points.map((v, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(" ");
  return <path d={d} fill="none" stroke={color} strokeWidth="2.5" vectorEffect="non-scaling-stroke" />;
}

function Steps({ points, max, color, height = 140 }) {
  // points: [{ x: time, y: passing }]. A ratchet only moves up in steps, so draw steps.
  if (points.length < 2) return null;
  const w = 600, x0 = points[0].x, span = Math.max(1, points[points.length - 1].x - x0);
  const xs = (x) => ((x - x0) / span) * w;
  const ys = (v) => height - (max ? (v / max) * (height - 8) : 0) - 4;
  let d = `M0,${ys(points[0].y).toFixed(1)}`;
  for (const p of points.slice(1)) d += ` H${xs(p.x).toFixed(1)} V${ys(p.y).toFixed(1)}`;
  return <path d={d} fill="none" stroke={color} strokeWidth="2.5" vectorEffect="non-scaling-stroke" />;
}

function StepChart({ points, total, label }) {
  const height = 140, max = Math.max(1, total || 0, ...points.map((p) => p.y));
  return points.length < 2 ? <div className="empty">Waiting for data…</div> : (
    <div>
      <svg viewBox={`0 0 600 ${height}`} width="100%" height={height} preserveAspectRatio="none" role="img" aria-label={label}>
        <Steps points={points} max={max} color="var(--green)" height={height} />
      </svg>
      <div style={{ fontSize: 12, color: "var(--muted)" }}>
        <span style={{ color: "var(--green)" }}>■</span> passing: {points[0].y} → {points[points.length - 1].y} of {total}
      </div>
    </div>
  );
}

const host = (u) => { try { return new URL(u).hostname; } catch { return u; } };

function Chart({ series, height = 140, label }) {
  const max = Math.max(1, ...series.flatMap((s) => s.points));
  const has = series.some((s) => s.points.length >= 2);
  return (
    <div>
      {has ? (
        <svg viewBox={`0 0 600 ${height}`} width="100%" height={height} preserveAspectRatio="none" role="img" aria-label={label}>
          {series.map((s) => <Line key={s.name} points={s.points} max={max} color={s.color} height={height} />)}
        </svg>
      ) : (
        <div className="empty">Waiting for data…</div>
      )}
      <div style={{ display: "flex", gap: 14, fontSize: 12, color: "var(--muted)" }}>
        {series.map((s) => (
          <span key={s.name}><span style={{ color: s.color }}>■</span> {s.name}</span>
        ))}
      </div>
    </div>
  );
}

const Tile = ({ k, v, cls }) => (
  <div className="card tile"><div className={`v ${cls || ""}`}>{v}</div><div className="k">{k}</div></div>
);

export default function Page() {
  const [data, setData] = useState(null);
  const [run, setRun] = useState("");

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`/api/run${run ? `?run=${encodeURIComponent(run)}` : ""}`, { cache: "no-store" });
        const j = await r.json();
        if (alive) setData(j);
      } catch {}
    };
    load();
    const t = setInterval(load, 1500);
    return () => { alive = false; clearInterval(t); };
  }, [run]);

  const c = data?.counters;
  const pct = c?.total ? Math.round((100 * c.passing) / c.total) : 0;

  return (
    <main>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1>Evergreen</h1>
          <p className="sub">The AGENTS.md that writes, tests, and expires itself. Live from RawTree; the agent runs on a laptop with Liquid.</p>
        </div>
        {data?.runs?.length > 0 && (
          <label style={{ fontSize: 13, color: "var(--muted)" }}>
            Run{" "}
            <select value={run || data.runId} onChange={(e) => setRun(e.target.value)}>
              {data.runs.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
        )}
      </div>

      {!data ? (
        <div className="empty">Loading…</div>
      ) : !data.runId ? (
        <div className="card empty">No runs yet. Start the agent with RAWTREE=1 and this page fills in live.</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <strong>Tests passing</strong>
              <span className={pct === 100 ? "good" : ""}>{c.passing} / {c.total} ({pct}%)</span>
            </div>
            <div className="bar"><span style={{ width: `${pct}%` }} /></div>
          </div>

          <div className="grid tiles">
            <Tile k="Rules learned" v={c.rulesLearned} cls="good" />
            <Tile k="Rules reused (worked)" v={c.rulesApplied} cls={c.rulesApplied ? "good" : ""} />
            <Tile k="Fixed straight from a rule" v={c.instantFixes} cls="good" />
            <Tile k={`Web lookups (Nimble)${c.cachedLookups ? `, ${c.cachedLookups} cached` : ""}`} v={c.webLookups} />
            <Tile k="Rollbacks" v={c.rollbacks} cls={c.rollbacks ? "warn" : ""} />
            <Tile k="Rejected by guard" v={c.guardRejections} cls={c.guardRejections ? "warn" : ""} />
            <Tile k="Human interventions" v={0} cls="good" />
            <Tile k="Liquid tokens" v={c.llmTokens.toLocaleString()} />
          </div>

          <div className="grid two" style={{ marginBottom: 12 }}>
            <div className="card">
              <h2>Staircase: tests passing over time</h2>
              <StepChart label="Tests passing over time" total={c.total} points={data.staircase.map((s) => ({ x: s.at, y: s.passing }))} />
            </div>
            <div className="card">
              <h2>Prompt size per attempt</h2>
              <Chart label="Prompt tokens per attempt" series={[
                { name: "Evergreen", color: "var(--green)", points: data.prompt.map((p) => p.prompt) },
                { name: "naive agent", color: "var(--red)", points: data.prompt.map((p) => p.naive) },
              ]} />
            </div>
          </div>

          <div className="grid two">
            <div className="card">
              <h2>Rulebook (verified rules go to AGENTS.md)</h2>
              {data.rules.length === 0 ? <div className="empty">No rules yet</div> : (
                <table>
                  <thead><tr><th>Rule</th><th>Fix</th><th>Status</th></tr></thead>
                  <tbody>
                    {data.rules.map((r) => (
                      <tr key={r.rule_id}>
                        <td><strong>{r.rule_id}</strong><br /><code>{r.signature}</code></td>
                        <td><code>{r.replacement}</code>
                          {r.source_url && <><br /><a href={r.source_url} target="_blank" rel="noreferrer">source</a></>}</td>
                        <td className={r.status === "retired" || r.status === "demoted" ? "bad" : "good"}>
                          {r.status}{r.confidence != null ? ` · ${Number(r.confidence).toFixed(2)}` : ""}
                          {r.applied ? ` · used ${r.applied}×` : ""}
                          {!r.inAgentsMd ? " · not in AGENTS.md" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="card">
              <h2>Latest attempts{data.attemptsTotal > data.feed.length ? ` (last ${data.feed.length} of ${data.attemptsTotal})` : ""}</h2>
              {data.feed.length === 0 ? <div className="empty">No attempts yet</div> : (
                <table>
                  <tbody>
                    {data.feed.map((a, i) => (
                      <tr key={i}>
                        <td><code>{a.file}</code></td>
                        <td className={a.accepted ? "good" : "bad"}>
                          {a.accepted ? "kept" : a.guard ? "blocked by guard" : a.rolledBack ? "rolled back" : "rejected"}
                        </td>
                        <td style={{ color: "var(--muted)" }}>
                          {a.tokens === 0 && a.accepted ? "0 tokens (rule)" : `${a.tokens} tokens`}{a.web ? " · web" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {data.evidence.length > 0 && (
                <>
                  <h2 style={{ marginTop: 16 }}>Evidence (Nimble)</h2>
                  <table><tbody>
                    {data.evidence.map((e, i) => (
                      <tr key={i}><td><code>{e.signature}</code></td>
                        <td>{e.url ? <a href={e.url} target="_blank" rel="noreferrer">{host(e.url)}</a> : "no result"}{e.cached ? " · cached" : ""}</td></tr>
                    ))}
                  </tbody></table>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
