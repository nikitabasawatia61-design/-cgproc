(() => {
    let allTenders = [];
    let stats = {};
    let filterMode = "all";
    let searchTerm = "";
    let isFetching = false;
    const today = new Date().toISOString().slice(0, 10);
    const DATA_FILE = "data/gem-tenders.json";

    const els = {
        total: document.getElementById("stat-total"),
        newToday: document.getElementById("stat-new"),
        updated: document.getElementById("stat-updated"),
        shortlistStat: document.getElementById("stat-shortlist"),
        shortlistCount: document.getElementById("shortlist-count"),
        search: document.getElementById("search"),
        meta: document.getElementById("result-meta"),
        table: document.getElementById("table-container"),
        btnSearch: document.getElementById("btn-search"),
        btnNew: document.getElementById("btn-new"),
        btnAll: document.getElementById("btn-all"),
        btnShortlist: document.getElementById("btn-shortlist"),
        syncCode: document.getElementById("sync-code"),
        syncStatus: document.getElementById("sync-status"),
        btnSyncConnect: document.getElementById("btn-sync-connect"),
        btnSyncGenerate: document.getElementById("btn-sync-generate"),
        btnFetch: document.getElementById("btn-fetch"),
        gemProxyUrl: document.getElementById("gem-proxy-url"),
        btnSaveGemProxy: document.getElementById("btn-save-gem-proxy"),
        settingsModal: document.getElementById("settings-modal"),
        btnCloseSettings: document.getElementById("btn-close-settings"),
        gemTenderModal: document.getElementById("gem-tender-modal"),
        gemTenderModalBody: document.getElementById("gem-tender-modal-body"),
        btnCloseGemTenderModal: document.getElementById("btn-close-gem-tender-modal"),
    };

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
    }

    function parseLastDate(value) {
        if (!value) return null;
        const cleaned = String(value).replace(/\s+IST$/i, "").replace(/\s+/g, " ").trim();
        const match = cleaned.match(/^(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s+(AM|PM)/i);
        if (!match) return null;
        const [, day, month, year, hour, minute, second, ampm] = match;
        const months = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };
        const monthIndex = months[month.toLowerCase().slice(0, 3)];
        if (monthIndex === undefined) return null;
        let hour24 = Number(hour) % 12;
        if (ampm.toUpperCase() === "PM") hour24 += 12;
        return new Date(Date.UTC(Number(year), monthIndex, Number(day), hour24 - 5, Number(minute) - 30, Number(second)));
    }

    function isTenderOpen(tender) {
        const parsed = parseLastDate(tender.last_date);
        return !parsed || parsed.getTime() >= Date.now();
    }

    function getActiveTenders() {
        return allTenders.filter(isTenderOpen);
    }

    function sortNewestFirst(tenders) {
        return [...tenders].sort((a, b) => {
            const aSeen = a.first_seen_at || "";
            const bSeen = b.first_seen_at || "";
            if (bSeen !== aSeen) return bSeen.localeCompare(aSeen);
            return (Number(b.tender_no?.split("/").pop()) || 0) - (Number(a.tender_no?.split("/").pop()) || 0);
        });
    }

    function getFilteredTenders() {
        return sortNewestFirst(getActiveTenders().filter((t) => {
            const fields = [t.tender_no, t.name, t.documents_required_from_seller, t.address, t.area_city];
            const matchesSearch = !searchTerm || fields.some((f) => (f || "").toLowerCase().includes(searchTerm));
            const matchesNew = filterMode !== "new" || (t.first_seen_at || "").startsWith(today);
            const matchesShortlist = filterMode !== "shortlist" || ShortlistSync.has(t.tender_no);
            return matchesSearch && matchesNew && matchesShortlist;
        }));
    }

    function updateStats() {
        els.total.textContent = stats.total ?? 0;
        els.newToday.textContent = stats.new_today ?? 0;
        els.updated.textContent = (stats.last_scraped || "Never").replace("T", " ").slice(0, 16);
        const count = ShortlistSync.getAll().size;
        els.shortlistStat.textContent = count;
        els.shortlistCount.textContent = count;
    }

    function renderTable() {
        const tenders = getFilteredTenders();
        els.meta.textContent = `${tenders.length} bid${tenders.length === 1 ? "" : "s"} shown`;
        if (!tenders.length) {
            els.table.innerHTML = `<div class="empty"><strong>No bids found</strong><p>Run run_gem_and_push.ps1 locally or click Fetch with a Vercel proxy URL.</p></div>`;
            return;
        }

        const rows = tenders.map((t) => {
            const starred = ShortlistSync.has(t.tender_no);
            const tenderCell = t.gem_id
                ? `<button type="button" class="tender-link tender-link-btn gem-tender-open" data-gem-id="${escapeHtml(t.gem_id)}" data-tender-no="${escapeHtml(t.tender_no)}">${escapeHtml(t.tender_no)}</button>`
                : `<span class="tender-no">${escapeHtml(t.tender_no)}</span>`;
            return `<tr>
                <td><button class="btn-star ${starred ? "active" : ""}" type="button" data-tender-no="${escapeHtml(t.tender_no)}">${starred ? "★" : "☆"}</button></td>
                <td>${tenderCell}</td>
                <td class="name-cell">${escapeHtml(t.name || "—")}</td>
                <td class="docs-cell">${escapeHtml(t.documents_required_from_seller || "—")}</td>
                <td class="address-cell">${escapeHtml(t.address || "—")}</td>
                <td>${escapeHtml(t.last_date || "—")}</td>
                <td>${escapeHtml((t.first_seen_at || "").slice(0, 10) || "—")}${(t.first_seen_at || "").startsWith(today) ? '<span class="badge-new">New</span>' : ""}</td>
            </tr>`;
        }).join("");

        els.table.innerHTML = `<table class="gem-table"><thead><tr>
            <th></th><th>Tender No</th><th>Description</th><th>Document Required from Seller</th><th>Address</th><th>Bid Due Date</th><th>Added</th>
        </tr></thead><tbody>${rows}</tbody></table>`;
    }

    async function loadData() {
        const response = await fetch(`${DATA_FILE}?${Date.now()}`);
        if (!response.ok) throw new Error("Could not load gem-tenders.json");
        const payload = await response.json();
        allTenders = payload.tenders || [];
        stats = { ...(payload.stats || {}), total: getActiveTenders().length };
        updateStats();
        renderTable();
    }

    async function handleFetchClick() {
        if (isFetching) return;
        isFetching = true;
        els.btnFetch.disabled = true;
        els.btnFetch.textContent = "Fetching...";
        const proxyUrl = localStorage.getItem("cgproc-gem-proxy") || window.GEM_API?.proxyUrl || "";
        if (proxyUrl) window.GEM_API = { ...(window.GEM_API || {}), proxyUrl };
        try {
            const payload = await GemFetch.pullLive(allTenders);
            allTenders = payload.tenders || [];
            stats = { ...(payload.stats || {}), total: getActiveTenders().length, last_scraped: payload.fetched_at };
            updateStats();
            renderTable();
            els.meta.textContent = `Fetched ${allTenders.length} GeM bids just now.`;
        } catch (error) {
            els.table.innerHTML = `<div class="error"><strong>Fetch failed</strong><p>${escapeHtml(error.message)}</p><p>Run <code>run_gem_and_push.ps1</code> locally or save a Vercel proxy URL (double-click footer area / use settings).</p></div>`;
        } finally {
            isFetching = false;
            els.btnFetch.disabled = false;
            els.btnFetch.textContent = "Fetch GeM Bids";
        }
    }

    async function openGemTenderDetail(gemId, tenderNo) {
        const tender = allTenders.find((item) => item.gem_id === gemId || item.tender_no === tenderNo);
        if (!tender) return;
        els.gemTenderModal.classList.add("open");
        document.getElementById("gem-tender-modal-title").textContent = tender.tender_no || "GeM Bid Details";
        els.gemTenderModalBody.innerHTML = `<div class="loading">Reading bid PDF...</div>`;
        if (tender.documents_required_from_seller || tender.address) {
            GemDetail.renderFields(els.gemTenderModalBody, tender);
            return;
        }
        try {
            const detail = await GemDetail.fetchLiveDetail(gemId);
            if (detail) {
                Object.assign(tender, detail);
                GemDetail.renderFields(els.gemTenderModalBody, tender, detail);
                return;
            }
        } catch (_) {}
        GemDetail.renderFields(els.gemTenderModalBody, { ...tender, pdf_url: GemDetail.pdfUrl(gemId) });
    }

    function updateSyncStatus() {
        const status = ShortlistSync.status();
        els.syncStatus.className = `sync-status ${status.mode === "cloud" ? "cloud" : "local"}`;
        els.syncStatus.textContent = status.message;
        if (ShortlistSync.getSyncCode()) els.syncCode.value = ShortlistSync.getSyncCode();
    }

    els.btnFetch.addEventListener("click", handleFetchClick);
    els.btnSaveGemProxy.addEventListener("click", () => {
        const url = els.gemProxyUrl.value.trim();
        if (!url) localStorage.removeItem("cgproc-gem-proxy");
        else localStorage.setItem("cgproc-gem-proxy", url);
        els.settingsModal.classList.remove("open");
    });
    els.btnCloseSettings.addEventListener("click", () => els.settingsModal.classList.remove("open"));
    els.btnCloseGemTenderModal.addEventListener("click", () => els.gemTenderModal.classList.remove("open"));
    els.table.addEventListener("click", (event) => {
        const gemBtn = event.target.closest(".gem-tender-open");
        if (gemBtn) return openGemTenderDetail(gemBtn.dataset.gemId, gemBtn.dataset.tenderNo);
        const star = event.target.closest(".btn-star");
        if (star) { ShortlistSync.toggle(star.dataset.tenderNo); renderTable(); updateStats(); }
    });
    els.btnSearch.addEventListener("click", () => { searchTerm = els.search.value.trim().toLowerCase(); renderTable(); });
    els.search.addEventListener("keydown", (e) => { if (e.key === "Enter") { searchTerm = els.search.value.trim().toLowerCase(); renderTable(); } });
    els.btnNew.addEventListener("click", () => { filterMode = "new"; els.btnNew.classList.add("active"); els.btnAll.classList.remove("active"); els.btnShortlist.classList.remove("active"); renderTable(); });
    els.btnAll.addEventListener("click", () => { filterMode = "all"; searchTerm = ""; els.search.value = ""; els.btnAll.classList.add("active"); els.btnNew.classList.remove("active"); els.btnShortlist.classList.remove("active"); renderTable(); });
    els.btnShortlist.addEventListener("click", () => { filterMode = "shortlist"; els.btnShortlist.classList.add("active"); els.btnAll.classList.remove("active"); els.btnNew.classList.remove("active"); renderTable(); });
    els.btnSyncConnect.addEventListener("click", () => { ShortlistSync.connect(els.syncCode.value); updateSyncStatus(); });
    els.btnSyncGenerate.addEventListener("click", () => { els.syncCode.value = ShortlistSync.generateCode(); });

    els.gemProxyUrl.value = localStorage.getItem("cgproc-gem-proxy") || "";
    document.querySelector(".footer").addEventListener("dblclick", () => {
        els.settingsModal.classList.add("open");
        els.gemProxyUrl.value = localStorage.getItem("cgproc-gem-proxy") || "";
    });

    ShortlistSync.onChange(() => { updateStats(); renderTable(); updateSyncStatus(); });
    ShortlistSync.init();
    updateSyncStatus();
    loadData().catch((error) => {
        els.table.innerHTML = `<div class="error"><strong>Failed to load data</strong><p>${escapeHtml(error.message)}</p></div>`;
    });
})();
