export function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim().replace(/[ ,;.]+$/, "");
}

function isStopFooter(line) {
    const low = line.toLowerCase();
    return (
        low.includes("buyer added") ||
        low.includes("option clause") ||
        low.includes("number of covers") ||
        low.includes("checklist of the documents") ||
        low.includes("generic")
    );
}

function isQuantityLine(line) {
    return /^\d+$/.test(line);
}

function isAddressStart(line) {
    return /^\d{6},/.test(line);
}

function isGstLine(line) {
    return /^\(GST-/i.test(line);
}

function continuesAddress(line) {
    if (!line || isStopFooter(line)) return false;
    if (isQuantityLine(line)) return false;
    if (["N/A", "PROJECT /", "LUMPSUM", "BASED"].includes(line.toUpperCase())) return false;
    if (/^(Project|Lumpsum|Based)\s*\/?\s*$/i.test(line)) return false;
    return /[A-Za-z]/.test(line);
}

function parseConsigneeRow(lines) {
    if (!lines.length) return null;

    const addrStart = lines.findIndex((line) => isAddressStart(line));
    if (addrStart < 0) return null;

    const name = clean(lines.slice(0, addrStart).join(" "));
    const addressParts = [];
    let extra = "N/A";

    for (const line of lines.slice(addrStart)) {
        if (isStopFooter(line)) break;
        if (addressParts.length && isQuantityLine(line)) break;
        if (addressParts.length && line.toUpperCase() === "N/A") {
            extra = "N/A";
            break;
        }
        if (isAddressStart(line) || isGstLine(line) || (addressParts.length && continuesAddress(line))) {
            addressParts.push(line);
            continue;
        }
        if (addressParts.length) {
            if (!/^(Project|Lumpsum|Based)\s*\/?\s*$/i.test(line)) {
                extra = clean(line) || extra;
            }
            break;
        }
    }

    const address = clean(addressParts.join(" "));
    if (!name || !address) return null;
    return { consignee: name, address, additional_requirement: extra || "N/A" };
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
    const rowMatch = section.match(/(?:^|\n)1\n([\s\S]+)/);
    if (!rowMatch) return [];

    const rawLines = rowMatch[1].split("\n").map((line) => line.trim()).filter(Boolean);
    const cleanedLines = [];
    for (const line of rawLines) {
        if (cleanedLines.length && isStopFooter(line)) break;
        cleanedLines.push(line);
    }

    const parsed = parseConsigneeRow(cleanedLines);
    if (parsed) return [parsed];

    const legacyMatch = section.match(
        /\n1\s*\n([^\n]+)\n([^\n]+)\n\(([^)]+)\)\s*\n(?:Project\s*\/\s*\n)?(?:Lumpsum\s*\n)?(?:Based\s*\n)?(N\/A|[^\n]+)/i
    );
    if (!legacyMatch) return [];

    const name = clean(legacyMatch[1]);
    const addressLine = clean(legacyMatch[2]);
    const gst = clean(legacyMatch[3] || "");
    const address = gst ? `${addressLine} (${gst})` : addressLine;
    const extra = clean(legacyMatch[4] || "") || "N/A";
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
