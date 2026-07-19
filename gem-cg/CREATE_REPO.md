# Create separate GitHub repo for GeM CG

Run from the **parent** `cgproc` folder (not inside gem-cg).

## Step 1 — Create empty repo on GitHub

1. Open: https://github.com/new
2. Repository name: **gem-cg-korba**
3. Visibility: Public
4. **Do NOT** add README, .gitignore, or license (empty repo)
5. Click **Create repository**

## Step 2 — Push gem-cg folder

```powershell
cd C:\Users\91706\Desktop\cgproc

# Extract gem-cg history into its own branch
git subtree split --prefix=gem-cg -b gem-cg-standalone

# Push to new repo (replace URL if you used a different name)
git push -u https://github.com/nikitabasawatia61-design/gem-cg-korba.git gem-cg-standalone:main
```

## Step 3 — Enable GitHub Pages

1. Open repo **Settings → Pages**
2. Source: **GitHub Actions**
3. Push to `main` triggers `deploy-pages.yml` automatically

Dashboard URL will be:

`https://nikitabasawatia61-design.github.io/gem-cg-korba/`

## Step 4 — Vercel (API proxy)

Create a **new** Vercel project linked to **gem-cg-korba** repo:

| Setting | Value |
|---------|--------|
| Framework | Other |
| Root Directory | *(empty)* |
| Install Command | `npm install` |
| Include files outside root | Disabled |

## Step 5 — Update links

After Pages is live, update the CG dashboard subtitle link in `-cgproc` to point to the new GeM URL.
