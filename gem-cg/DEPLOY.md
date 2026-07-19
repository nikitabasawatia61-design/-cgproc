# Deploy GeM proxy on Vercel (Node.js only)

This folder is **Project 2 — GeM CG**. Deploy it as its own Vercel project (separate from CG e-proc).

## Vercel settings

| Setting | Value |
|---------|--------|
| **Framework Preset** | **Other** (not Python) |
| **Root Directory** | *(leave empty if this folder is the repo root)* |
| **Include files outside root** | **Disabled** |
| **Install Command** | `npm install` |
| **Build Command** | *(empty)* |
| **Node.js** | 20.x |

## Test URLs

```
/api/gem/fetch?state=CHHATTISGARH&city=KORBA
/api/gem/detail?gem_id=9622895
```

## Dashboard

GeM dashboard HTML is in `docs/`. Deploy via GitHub Pages from this repo, or use the combined setup in `PROJECTS.md` at the parent cgproc repo.
