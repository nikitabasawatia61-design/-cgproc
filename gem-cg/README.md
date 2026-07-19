# GeM CG — Korba Bid Tracker

**Separate GitHub repo:** https://github.com/nikitabasawatia61-design/gem-cg-korba

Open bids on GeM BidPlus for Chhattisgarh / Korba. Independent from [CG e-proc (`-cgproc`)](https://github.com/nikitabasawatia61-design/-cgproc).

## Dashboard

GitHub Pages: https://nikitabasawatia61-design.github.io/gem-cg-korba/

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
