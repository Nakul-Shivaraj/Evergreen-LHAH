// Server-only RawTree client. Runs in route handlers, so the read-only key never reaches the browser.
const API = "https://api.rawtree.com/v1/query";

export async function query(sql) {
  const db = process.env.RAWTREE_DATABASE || "evergreen";
  const res = await fetch(`${API}?database=${encodeURIComponent(db)}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${process.env.RAWTREE_DASHBOARD_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sql }),
  });
  // A table only exists after its first insert: treat errors as "no data yet".
  if (!res.ok) return [];
  const body = await res.json().catch(() => ({}));
  return body.data ?? [];
}

// Whole original rows, so the dashboard keeps working if the agent adds or renames fields.
export async function rows(table, runId, limit = 2000) {
  const data = await query(
    `SELECT __raw_data AS d FROM ${table} WHERE run_id = '${runId}' ORDER BY at LIMIT ${limit}`
  );
  return data.map((r) => (typeof r.d === "string" ? JSON.parse(r.d) : r.d));
}

export const safeRunId = (s) => (typeof s === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(s) ? s : null);
