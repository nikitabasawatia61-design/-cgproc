# Deploy GeM proxy on Vercel

This folder is a **Node.js** serverless API (not Python).

## Vercel project settings

Open **Project → Settings → Build and Deployment** and set:

| Setting | Value |
|---------|--------|
| **Framework Preset** | **Other** (not Python) |
| **Root Directory** | `gem-proxy` |
| **Include files outside the root directory** | **Disabled** |
| **Install Command** | `npm install` |
| **Build Command** | *(leave empty)* |
| **Output Directory** | *(leave empty)* |
| **Node.js Version** | 20.x or 24.x |

Then **Redeploy** from the latest `main` commit.

## Test after deploy

```
https://YOUR-APP.vercel.app/api/gem/fetch?state=CHHATTISGARH&city=KORBA
https://YOUR-APP.vercel.app/api/gem/detail?gem_id=9622895
```

Paste the fetch URL into the dashboard **GeM modal → Save API URL**.

## Why Python errors happen

If **Framework Preset** is Python, or **Include files outside root** is enabled, Vercel scans the parent repo and finds `app.py` / scraper files, then fails looking for a Python web entrypoint. This folder has no Python — only `api/gem/*.js`.
