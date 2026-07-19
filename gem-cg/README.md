# GeM CG — Korba Bid Tracker

Separate project from **CG e-procurement** (`cgproc`). Tracks GeM BidPlus open bids for Chhattisgarh / Korba.

## Projects

| Project | Repo folder | Deploy |
|---------|-------------|--------|
| **CG e-proc** | parent `cgproc` repo | GitHub Pages + local scraper |
| **GeM CG** | this folder (`gem-cg/`) | GitHub Pages (dashboard) + Vercel (API proxy) |

## Dashboard (GitHub Pages)

Push this folder to its own GitHub repo, enable Pages from `main` / `docs`.

Or copy `gem-cg/` to a new repo: `gem-cg-korba`.

Live data: `docs/data/gem-tenders.json`

## Local fetch (recommended)

```powershell
cd gem-cg
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_gem.py --export-json --enrich-pdf
.\run_gem_and_push.ps1
```

GeM blocks GitHub cloud servers — run fetch on your PC in India.

## Vercel API proxy

Deploy **this folder** as its own Vercel project:

| Setting | Value |
|---------|--------|
| Framework Preset | **Other** |
| Root Directory | *(empty — repo root is gem-cg)* |
| Install Command | `npm install` |
| Include files outside root | **Disabled** |

Endpoints:

- `/api/gem/fetch?state=CHHATTISGARH&city=KORBA`
- `/api/gem/detail?gem_id=9622895`

See `DEPLOY.md` for details.

## Render (alternative)

```bash
# Uses render.yaml + server.js
```

## Link to CG e-proc

CG dashboard: https://nikitabasawatia61-design.github.io/-cgproc/
