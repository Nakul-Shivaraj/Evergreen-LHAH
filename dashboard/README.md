# Evergreen dashboard

Next.js app that shows Evergreen runs live from RawTree.

Vercel settings: Root Directory = `dashboard`, Framework = Next.js.
Env vars: `RAWTREE_DASHBOARD_KEY` (read-only key), `RAWTREE_DATABASE=evergreen`.

Local: `npm install && npm run dev`, with those two vars in `.env.local`.
