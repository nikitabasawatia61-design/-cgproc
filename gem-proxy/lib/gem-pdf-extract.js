export function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim().replace(/[ ,;.]+$/, "");
}

export function extractDocumentsRequired(text) {
    const patterns = [
        /\/Document required\s*from seller\s*(.+?)(?:\*In case any bidder|$)/is,
        /Documents required from seller['’]?\s*(.+?)(?:Checklist of the documents|$)/is,
    ];
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            const cleaned = clean(match[1]);
            if (cleaned.length > 5) return cleaned.slice(0, 2000);
        }
    }
    return "";
}

export function extractConsigneeBlocks(text) {
    const sectionMatch = text.match(
        /\/Consignees\/Reporting Officer and Quantity([\s\S]+?)(?:\/Buyer Added Bid Specific|Checklist of the documents|$)/i
    );
    if (!sectionMatch) return [];

    const section = sectionMatch[1];
    const rowMatch = section.match(
        /\n1\s*\n([^\n]+)\n([^\n]+)\n\(([^)]+)\)\s*\n(?:Project\s*\/\s*\n)?(?:Lumpsum\s*\n)?(?:Based\s*\n)?(N\/A|[^\n]+)/i
    );
    if (!rowMatch) return [];

    const name = clean(rowMatch[1]);
    const addressLine = clean(rowMatch[2]);
    const gst = clean(rowMatch[3] || "");
    const address = gst ? `${addressLine} (${gst})` : addressLine;
    const extra = clean(rowMatch[4] || "") || "N/A";
    if (!name || !address) return [];
    return [{ consignee: name, address, additional_requirement: extra }];
}

export function extractBidFields(text) {
    const consignees = extractConsigneeBlocks(text);
    const primary = consignees[0] || {};
    return {
        documents_required_from_seller: extractDocumentsRequired(text),
        address: primary.address || "",
        additional_requirement: primary.additional_requirement || "",
        consignee: primary.consignee || "",
        consignees,
    };
}
