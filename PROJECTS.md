# CG e-Procurement + GeM — two separate projects

This repository contains **two independent projects**:

## Project 1 — CG e-proc (`/` root)

Chhattisgarh government open tenders.

- **Dashboard:** `docs/index.html` → GitHub Pages
- **Scraper:** `run_local_and_push.ps1` on your PC
- **Live:** https://nikitabasawatia61-design.github.io/-cgproc/

## Project 2 — GeM CG (`/gem-cg/`)

GeM BidPlus Korba bids.

- **Dashboard:** `gem-cg/docs/index.html`
- **API proxy:** `gem-cg/api/` → deploy as separate Vercel project
- **Local fetch:** `gem-cg/run_gem_and_push.ps1`

Copy `gem-cg/` to a new GitHub repo for a fully separate GeM deployment.

See `gem-cg/README.md` for GeM setup and Vercel instructions.
