export const metadata = {
  title: "Evergreen",
  description: "The AGENTS.md that writes, tests, and expires itself. Live run from RawTree.",
};

const css = `
:root { --bg:#f7f8f6; --panel:#ffffff; --ink:#15201a; --muted:#5d6b62; --line:#dde3de;
  --green:#1f8a4c; --red:#c2412d; --amber:#b7791f; --accent:#1f8a4c; }
@media (prefers-color-scheme: dark) { :root { --bg:#0e1411; --panel:#151d18; --ink:#e6ede8;
  --muted:#93a39a; --line:#26322b; --green:#4cc27f; --red:#ef6b55; --amber:#e0a84a; --accent:#4cc27f; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.45 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:26px; margin:0; letter-spacing:-0.01em; }
h2 { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:0 0 10px; }
.sub { color:var(--muted); margin:4px 0 20px; }
.grid { display:grid; gap:12px; }
.tiles { grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); margin-bottom:12px; }
.two { grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; min-width:0; }
.tile .v { font-size:28px; font-weight:650; font-variant-numeric:tabular-nums; }
.tile .k { color:var(--muted); font-size:13px; }
.good { color:var(--green); } .bad { color:var(--red); } .warn { color:var(--amber); }
table { width:100%; border-collapse:collapse; font-size:13px; }
td, th { text-align:left; padding:6px 4px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:500; }
code { font:12px ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap:anywhere; }
a { color:var(--accent); overflow-wrap:anywhere; }
select { background:var(--panel); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:4px 6px; }
.bar { height:8px; border-radius:4px; background:var(--line); overflow:hidden; }
.bar > span { display:block; height:100%; background:var(--green); }
.empty { color:var(--muted); padding:40px 0; text-align:center; }
.tgrid { width:auto; border-collapse:separate; border-spacing:2px; }
.tgrid th, .tgrid td { border-bottom:none; padding:2px 4px; }
.tgrid th { text-align:center; font-size:11px; }
.tgrid .tname { max-width:260px; padding-right:8px; }
.tgrid .cell { width:22px; min-width:22px; height:20px; text-align:center; font-size:11px; font-weight:600;
  color:#0e1411; border-radius:3px; }
.patch { border:1px solid var(--line); border-radius:8px; padding:6px 10px; }
.patch summary { cursor:pointer; font-size:13px; }
.diff { margin:8px 0 2px; padding:8px; background:var(--bg); border-radius:6px; overflow-x:auto;
  font:12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; white-space:pre; }
.diff .add { color:var(--green); } .diff .del { color:var(--red); } .diff .hunk { color:var(--muted); }
`;

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <style>{css}</style>
      </head>
      <body>{children}</body>
    </html>
  );
}
