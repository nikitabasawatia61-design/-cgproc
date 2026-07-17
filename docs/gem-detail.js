window.GemDetail = (() => {
    const PDF_BASE = "https://bidplus.gem.gov.in/showbidDocument/";

    function pdfUrl(gemId) {
        return `${PDF_BASE}${gemId}`;
    }

    function detailProxyUrl(gemId) {
        const proxy = localStorage.getItem("cgproc-gem-proxy") || window.GEM_API?.proxyUrl || "";
        if (!proxy) return "";
        const base = proxy.replace(/\/api\/gem\/fetch\/?$/, "");
        return `${base}/api/gem/detail?gem_id=${encodeURIComponent(gemId)}`;
    }

    async function fetchLiveDetail(gemId) {
        const url = detailProxyUrl(gemId);
        if (!url) return null;
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error(`Detail fetch failed (${response.status})`);
        return response.json();
    }

    function renderFields(container, tender, detail) {
        const data = { ...tender, ...(detail || {}) };
        const docs = data.documents_required_from_seller || "—";
        const address = data.address || "—";
        const extra = data.additional_requirement || "—";
        const consignee = data.consignee || "—";
        const pdf = data.pdf_url || pdfUrl(data.gem_id);

        container.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Tender No</div>
                    <div class="detail-value">${escapeHtml(data.tender_no || "—")}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Consignee</div>
                    <div class="detail-value">${escapeHtml(consignee)}</div>
                </div>
                <div class="detail-item full">
                    <div class="detail-label">Document required from seller</div>
                    <div class="detail-value">${escapeHtml(docs)}</div>
                </div>
                <div class="detail-item full">
                    <div class="detail-label">Address</div>
                    <div class="detail-value">${escapeHtml(address)}</div>
                </div>
                <div class="detail-item full">
                    <div class="detail-label">Additional Requirement</div>
                    <div class="detail-value">${escapeHtml(extra)}</div>
                </div>
            </div>
            <div class="detail-actions">
                <a class="btn btn-gem" href="${escapeHtml(pdf)}" target="_blank" rel="noopener">Download PDF</a>
            </div>
        `;
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
    }

    return {
        pdfUrl,
        fetchLiveDetail,
        renderFields,
    };
})();
