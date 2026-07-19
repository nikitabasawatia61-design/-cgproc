import pdf from "pdf-parse/lib/pdf-parse.js";
import { extractBidFields } from "../../lib/gem-pdf-extract.js";

const PDF_URL = "https://bidplus.gem.gov.in/showbidDocument/{gem_id}";

function corsHeaders(res) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Accept");
}

async function downloadPdf(gemId) {
    const response = await fetch(PDF_URL.replace("{gem_id}", gemId), {
        headers: {
            "User-Agent": "Mozilla/5.0 (compatible; CGProcGemProxy/1.0)",
            Referer: "https://bidplus.gem.gov.in/",
        },
    });
    if (!response.ok) throw new Error(`PDF download failed (${response.status})`);
    const buffer = Buffer.from(await response.arrayBuffer());
    if (!buffer.slice(0, 4).toString("utf8").startsWith("%PDF")) {
        throw new Error("GeM did not return a PDF");
    }
    return buffer;
}

export default async function handler(req, res) {
    corsHeaders(res);
    if (req.method === "OPTIONS") return res.status(200).end();
    if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

    const gemId = req.query.gem_id;
    if (!gemId) return res.status(400).json({ error: "gem_id is required" });

    try {
        const pdfBuffer = await downloadPdf(String(gemId));
        const parsed = await pdf(pdfBuffer);
        const fields = extractBidFields(parsed.text || "");
        return res.status(200).json({
            gem_id: String(gemId),
            pdf_url: PDF_URL.replace("{gem_id}", gemId),
            ...fields,
        });
    } catch (error) {
        return res.status(502).json({ error: error.message || "GeM PDF parse failed" });
    }
}
