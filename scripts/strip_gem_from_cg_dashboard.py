"""One-off: remove GeM UI from CG docs/index.html."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / "docs" / "index.html"
html = html_path.read_text(encoding="utf-8")

html = re.sub(
    r'    <div class="modal-backdrop" id="gem-modal".*?'
    r'    <div class="modal-backdrop" id="gem-tender-modal".*?</div>\n\n',
    "",
    html,
    flags=re.S,
)

for script in ("gem-config.js", "gem-fetch.js", "gem-detail.js"):
    html = html.replace(f'    <script src="{script}"></script>\n', "")

html = html.replace(
    """                <div class="header-actions">
                    <span class="source-pill" id="source-pill">CG Portal</span>
                    <button class="btn btn-gem" id="btn-open-gem-modal" type="button">GeM</button>
                </div>""",
    '                <span class="source-pill" id="source-pill">CG Portal</span>',
)

html = html.replace(
    "Hosted free on GitHub Pages.",
    "Hosted free on GitHub Pages. GeM Korba bids live in the separate <code>gem-cg/</code> project.",
)

html = html.replace('        let dataSource = localStorage.getItem("cgproc-source") || "cg";\n', "")
html = html.replace(
    '        const GEM_FETCH_URL = "https://github.com/nikitabasawatia61-design/-cgproc/actions/workflows/fetch-gem.yml";\n',
    "",
)
html = re.sub(r",\n            gem: \{.*?\n            \},", "", html, flags=re.S)

for key in (
    "btnOpenGemModal",
    "gemModal",
    "btnCloseGemModal",
    "btnSwitchCg",
    "btnSwitchGem",
    "gemProxyUrl",
    "btnSaveGemProxy",
    "gemTenderModal",
    "gemTenderModalBody",
    "btnCloseGemTenderModal",
):
    html = re.sub(rf'            {key}: document\.getElementById\([^)]+\),\n', "", html)

old_block = html[html.find("function getSourceConfig"):html.find("function updateShortlistStats")]
new_block = """        const config = SOURCE_CONFIG.cg;

        function applySourceUi() {
            document.title = config.title;
            els.headerEyebrow.textContent = config.eyebrow;
            els.headerTitle.textContent = config.title;
            els.headerSubtitle.textContent = config.subtitle;
            els.sourcePill.textContent = config.pill;
            els.footerLink.href = config.footerLink;
            els.footerLink.textContent = config.footerLabel;
            els.footerNote.textContent = config.footerNote;
            els.btnFetch.textContent = config.fetchLabel;
            els.btnFetch.disabled = isFetching;
            els.runHint.innerHTML = config.runHint;
        }

"""
html = html.replace(old_block, new_block)

html = html.replace("if (dataSource === \"gem\") {\n                    searchFields.push(t.documents_required_from_seller, t.address);\n                }\n\n                ", "")
html = html.replace("                const config = getSourceConfig();\n                const emptyMessage = filterMode === \"shortlist\"", "                const emptyMessage = filterMode === \"shortlist\"")
html = html.replace(': config.emptyHint;', ': "Try another search, or wait for the daily GitHub Action to fetch data.";')

# renderTable: remove gem branch - keep only CG row template
html = re.sub(
    r"            const isGemView = dataSource === \"gem\";\n\n            const rows = tenders\.map\(\(t\) => \{.*?if \(isGemView\) \{.*?\`;\n                \}\n\n                return \`",
    "            const rows = tenders.map((t) => {\n                return `",
    html,
    flags=re.S,
)

html = re.sub(
    r"                let tenderCell;\n                if \(isGemView && t\.gem_id\) \{.*?\} else if \(t\.url\) \{",
    "                let tenderCell;\n                if (t.url) {",
    html,
    flags=re.S,
)

html = re.sub(
    r"            const tableClass = isGemView \? \"gem-table\" : \"\";\n            const tableHead = isGemView\n                \? \`.*?\`\n                : \`\n                        <tr>",
    "            const tableHead = `\n                        <tr>",
    html,
    flags=re.S,
)

html = html.replace('                <table class="${tableClass}">', "                <table>")

html = html.replace("if (dataSource === \"cg\" && portalTotal", "if (portalTotal")

html = re.sub(r"        function applyGemPayload\(payload\) \{.*?\n        \}\n\n", "", html, flags=re.S)
html = re.sub(r"        async function runCloudGemFetch\(\) \{.*?\n        \}\n\n", "", html, flags=re.S)

html = html.replace(
    """        async function handleFetchClick() {
            if (isFetching) return;

            if (dataSource === "cg") {
                window.open(CG_FETCH_URL, "_blank", "noopener");
                return;
            }

            isFetching = true;
            const previousLabel = els.btnFetch.textContent;
            els.btnFetch.textContent = "Fetching from GeM API...";
            els.btnFetch.disabled = true;
            els.meta.textContent = "Calling GeM BidPlus API for all Korba bids...";

            const proxyUrl = localStorage.getItem("cgproc-gem-proxy") || window.GEM_API?.proxyUrl || "";
            if (proxyUrl) {
                window.GEM_API = { ...(window.GEM_API || {}), proxyUrl };
            }

            try {
                const payload = await GemFetch.pullLive(allTenders);
                applyGemPayload(payload);
                els.meta.textContent = `Fetched ${allTenders.length} GeM bids from BidPlus API just now.`;
            } catch (error) {
                const message = error?.message || "GeM API fetch failed";
                const blocked = /failed to fetch|cors|networkerror|502|503|504/i.test(message);
                if (blocked || !proxyUrl) {
                    await runCloudGemFetch();
                } else {
                    els.table.innerHTML = `
                        <div class="error">
                            <strong>GeM API fetch failed</strong>
                            <p>${escapeHtml(message)}</p>
                        </div>
                    `;
                    els.meta.textContent = message;
                }
            } finally {
                isFetching = false;
                els.btnFetch.textContent = previousLabel;
                applySourceUi();
            }
        }""",
    """        function handleFetchClick() {
            window.open(CG_FETCH_URL, "_blank", "noopener");
        }""",
)

html = html.replace("            const config = getSourceConfig();\n            try {", "            try {")
html = html.replace('                const response = await fetch(config.dataFile + "?" + Date.now());', '                const response = await fetch("data/tenders.json?" + Date.now());')

# Remove gem event listeners
for block in [
    """        els.btnOpenGemModal.addEventListener("click", openGemModal);
        els.btnCloseGemModal.addEventListener("click", closeGemModal);
        els.gemModal.addEventListener("click", (event) => {
            if (event.target === els.gemModal) closeGemModal();
        });
        els.btnSwitchCg.addEventListener("click", () => {
            setDataSource("cg");
            closeGemModal();
        });
        els.btnSwitchGem.addEventListener("click", () => {
            setDataSource("gem");
            closeGemModal();
        });

        els.btnSaveGemProxy.addEventListener("click", () => {
            const url = els.gemProxyUrl.value.trim();
            if (!url) {
                localStorage.removeItem("cgproc-gem-proxy");
                els.meta.textContent = "Cleared GeM API URL. Fetch will use GitHub cloud workflow.";
                return;
            }
            localStorage.setItem("cgproc-gem-proxy", url);
            window.GEM_API = { ...(window.GEM_API || {}), proxyUrl: url };
            els.meta.textContent = "Saved GeM API URL. Click Fetch GeM Tenders to pull live data.";
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeGemModal();
        });

""",
    """        els.table.addEventListener("click", (event) => {
            const gemBtn = event.target.closest(".gem-tender-open");
            if (gemBtn) {
                openGemTenderDetail(gemBtn.dataset.gemId, gemBtn.dataset.tenderNo);
                return;
            }
            const button = event.target.closest(".btn-star");
            if (!button) return;
            toggleShortlist(button.dataset.tenderNo);
        });

        els.btnCloseGemTenderModal.addEventListener("click", closeGemTenderModal);
        els.gemTenderModal.addEventListener("click", (event) => {
            if (event.target === els.gemTenderModal) closeGemTenderModal();
        });

""",
]:
    html = html.replace(block, "")

html = html.replace(
    """        els.table.addEventListener("click", (event) => {
            const button = event.target.closest(".btn-star");
            if (!button) return;
            toggleShortlist(button.dataset.tenderNo);
        });

""",
    """        els.table.addEventListener("click", (event) => {
            const button = event.target.closest(".btn-star");
            if (!button) return;
            toggleShortlist(button.dataset.tenderNo);
        });

""",
)

html_path.write_text(html, encoding="utf-8")
print("Updated", html_path)
