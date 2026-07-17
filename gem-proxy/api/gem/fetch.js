const BASE_URL = "https://bidplus.gem.gov.in";
const ADVANCE_SEARCH_URL = `${BASE_URL}/advance-search`;
const SEARCH_BIDS_URL = `${BASE_URL}/search-bids`;
const PAGE_SIZE = 10;

function first(value, fallback = "") {
    if (value == null) return fallback;
    if (Array.isArray(value)) return value.length ? String(value[0]) : fallback;
    return String(value);
}

function formatEndDate(isoValue) {
    if (!isoValue) return "";
    const parsed = new Date(isoValue);
    if (Number.isNaN(parsed.getTime())) return isoValue;
    return parsed.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
    }) + " IST";
}

function normalizeBid(doc, cityName) {
    const gemId = first(doc.id);
    const bidNumber = first(doc.b_bid_number);
    const title = first(doc.bbt_title) || first(doc.b_category_name);
    const ministry = first(doc.ba_official_details_minName);
    let department = first(doc.ba_official_details_deptName);
    if (ministry && department) department = `${department} · ${ministry}`;
    else if (ministry) department = ministry;

    const now = new Date().toISOString().slice(0, 19);
    return {
        tender_no: bidNumber || gemId,
        name: title,
        department,
        amount: "",
        last_date: formatEndDate(first(doc.final_end_date_sort)),
        area_city: cityName,
        first_seen_at: now,
        last_updated_at: now,
        gem_id: gemId,
        url: gemId ? `${BASE_URL}/showbidresult/${gemId}` : "",
        source: "gem",
    };
}

function corsHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept",
    };
}

async function fetchCsrf(cookieJar) {
    const response = await fetch(ADVANCE_SEARCH_URL, {
        headers: {
            "User-Agent": "Mozilla/5.0 (compatible; CGProcGemProxy/1.0)",
            Referer: ADVANCE_SEARCH_URL,
            Origin: BASE_URL,
            Cookie: cookieJar,
        },
    });
    if (!response.ok) throw new Error(`GeM session failed (${response.status})`);

    const setCookie = response.headers.get("set-cookie") || "";
    const csrfMatch = setCookie.match(/csrf_gem_cookie=([^;]+)/);
    if (csrfMatch) return { csrf: csrfMatch[1], cookieJar: mergeCookies(cookieJar, setCookie) };

    const html = await response.text();
    const match = html.match(/name="csrf_bd_gem_nk"\s+value="([^"]+)"/);
    if (match) return { csrf: match[1], cookieJar: mergeCookies(cookieJar, setCookie) };
    throw new Error("Could not read GeM CSRF token");
}

function mergeCookies(existing, setCookieHeader) {
    const jar = new Map();
    for (const part of (existing || "").split(";")) {
        const [key, value] = part.trim().split("=");
        if (key && value) jar.set(key, value);
    }
    for (const chunk of (setCookieHeader || "").split(",")) {
        const [pair] = chunk.split(";");
        const [key, value] = pair.trim().split("=");
        if (key && value) jar.set(key, value);
    }
    return [...jar.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
}

async function searchPage(cookieJar, csrf, stateName, cityName, page) {
    const payload = JSON.stringify({
        searchType: "con",
        state_name_con: stateName,
        city_name_con: cityName,
        bidEndFromCon: "",
        bidEndToCon: "",
        page,
    });
    const body = new URLSearchParams({ payload, csrf_bd_gem_nk: csrf });

    const response = await fetch(SEARCH_BIDS_URL, {
        method: "POST",
        headers: {
            "User-Agent": "Mozilla/5.0 (compatible; CGProcGemProxy/1.0)",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            Accept: "application/json, text/javascript, */*; q=0.01",
            Origin: BASE_URL,
            Referer: ADVANCE_SEARCH_URL,
            "X-Requested-With": "XMLHttpRequest",
            Cookie: cookieJar,
        },
        body,
    });
    if (!response.ok) throw new Error(`GeM search failed (${response.status})`);

    const data = await response.json();
    if (data.status !== 1) throw new Error(data.message || "GeM search failed");
    return data.response.response;
}

async function fetchGemTenders(stateName, cityName) {
    let { csrf, cookieJar } = await fetchCsrf("");
    const firstPage = await searchPage(cookieJar, csrf, stateName, cityName, 1);
    const total = Number(firstPage.numFound || 0);
    const docs = [...(firstPage.docs || [])];
    const pages = Math.ceil(total / PAGE_SIZE);

    for (let page = 2; page <= pages; page += 1) {
        const pageData = await searchPage(cookieJar, csrf, stateName, cityName, page);
        docs.push(...(pageData.docs || []));
    }

    return docs.map((doc) => normalizeBid(doc, cityName));
}

export default async function handler(req, res) {
    Object.entries(corsHeaders()).forEach(([key, value]) => res.setHeader(key, value));
    if (req.method === "OPTIONS") return res.status(200).end();
    if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

    const stateName = req.query.state || "CHHATTISGARH";
    const cityName = req.query.city || "KORBA";

    try {
        const tenders = await fetchGemTenders(stateName, cityName);
        return res.status(200).json({
            source: "gem",
            filters: { state: stateName, city: cityName },
            fetched_at: new Date().toISOString().slice(0, 19),
            tenders,
        });
    } catch (error) {
        return res.status(502).json({ error: error.message || "GeM fetch failed" });
    }
}
