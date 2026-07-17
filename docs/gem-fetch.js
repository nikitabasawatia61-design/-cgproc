window.GemFetch = (() => {
    const BASE_URL = "https://bidplus.gem.gov.in";
    const ADVANCE_SEARCH_URL = `${BASE_URL}/advance-search`;
    const SEARCH_BIDS_URL = `${BASE_URL}/search-bids`;

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

    function mergeFirstSeen(freshTenders, existingTenders) {
        const previous = new Map(
            (existingTenders || []).map((item) => [item.tender_no, item.first_seen_at])
        );
        return freshTenders.map((tender) => ({
            ...tender,
            first_seen_at: previous.get(tender.tender_no) || tender.first_seen_at,
        }));
    }

    function parseEndDate(value) {
        if (!value) return null;
        const cleaned = String(value).replace(/\s+IST$/i, "").replace(/\s+/g, " ").trim();
        const match = cleaned.match(
            /^(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s+(AM|PM)/i
        );
        if (!match) return null;
        const [, day, month, year, hour, minute, second, ampm] = match;
        const months = {
            jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
            jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
        };
        const monthIndex = months[month.toLowerCase().slice(0, 3)];
        if (monthIndex === undefined) return null;
        let hour24 = Number(hour) % 12;
        if (ampm.toUpperCase() === "PM") hour24 += 12;
        const utc = Date.UTC(Number(year), monthIndex, Number(day), hour24 - 5, Number(minute) - 30, Number(second));
        return new Date(utc);
    }

    function buildStats(tenders) {
        const today = new Date().toISOString().slice(0, 10);
        const active = tenders.filter((tender) => {
            const parsed = parseEndDate(tender.last_date);
            return !parsed || parsed.getTime() >= Date.now();
        });
        return {
            total: active.length,
            new_today: active.filter((t) => (t.first_seen_at || "").startsWith(today)).length,
            last_scraped: new Date().toISOString().slice(0, 19),
        };
    }

    async function fetchCsrf(sessionFetch) {
        const response = await sessionFetch(ADVANCE_SEARCH_URL, { method: "GET" });
        if (!response.ok) throw new Error(`GeM session failed (${response.status})`);

        const csrfFromCookie = readCookie(response, "csrf_gem_cookie");
        if (csrfFromCookie) return csrfFromCookie;

        const html = await response.text();
        const match = html.match(/name="csrf_bd_gem_nk"\s+value="([^"]+)"/);
        if (match) return match[1];
        throw new Error("Could not read GeM CSRF token");
    }

    function readCookie(response, name) {
        const cookies = response.headers.getSetCookie?.() || [];
        for (const cookie of cookies) {
            const [pair] = cookie.split(";");
            const [key, value] = pair.split("=");
            if (key === name) return value;
        }
        return "";
    }

    async function searchPage(sessionFetch, csrf, stateName, cityName, page) {
        const payload = JSON.stringify({
            searchType: "con",
            state_name_con: stateName,
            city_name_con: cityName,
            bidEndFromCon: "",
            bidEndToCon: "",
            page,
        });
        const body = new URLSearchParams({
            payload,
            csrf_bd_gem_nk: csrf,
        });

        const response = await sessionFetch(SEARCH_BIDS_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                Accept: "application/json, text/javascript, */*; q=0.01",
            },
            body,
        });
        if (!response.ok) throw new Error(`GeM search failed (${response.status})`);

        const data = await response.json();
        if (data.status !== 1) {
            throw new Error(data.message || "GeM search failed");
        }
        return data.response.response;
    }

    async function fetchDirectFromGem(stateName, cityName, pageSize) {
        const jar = new Map();

        const sessionFetch = async (url, options = {}) => {
            const headers = new Headers(options.headers || {});
            headers.set("User-Agent", navigator.userAgent || "Mozilla/5.0");
            headers.set("Origin", BASE_URL);
            headers.set("Referer", ADVANCE_SEARCH_URL);
            headers.set("X-Requested-With", "XMLHttpRequest");

            const cookieHeader = [...jar.entries()].map(([k, v]) => `${k}=${v}`).join("; ");
            if (cookieHeader) headers.set("Cookie", cookieHeader);

            const response = await fetch(url, {
                ...options,
                headers,
                credentials: "include",
                mode: "cors",
            });

            const setCookies = response.headers.getSetCookie?.() || [];
            for (const cookie of setCookies) {
                const [pair] = cookie.split(";");
                const [key, value] = pair.split("=");
                if (key && value) jar.set(key, value);
            }
            return response;
        };

        const csrf = await fetchCsrf(sessionFetch);
        const firstPage = await searchPage(sessionFetch, csrf, stateName, cityName, 1);
        const total = Number(firstPage.numFound || 0);
        const docs = [...(firstPage.docs || [])];
        const pages = Math.ceil(total / pageSize);

        for (let page = 2; page <= pages; page += 1) {
            const pageData = await searchPage(sessionFetch, csrf, stateName, cityName, page);
            docs.push(...(pageData.docs || []));
        }

        return docs.map((doc) => normalizeBid(doc, cityName));
    }

    async function fetchViaProxy(proxyUrl, stateName, cityName) {
        const url = new URL(proxyUrl);
        url.searchParams.set("state", stateName);
        url.searchParams.set("city", cityName);
        const response = await fetch(url.toString(), {
            headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error(`GeM proxy failed (${response.status})`);
        const payload = await response.json();
        return payload.tenders || [];
    }

    async function pullLive(existingTenders = []) {
        const config = window.GEM_API || {};
        const stateName = config.state || "CHHATTISGARH";
        const cityName = config.city || "KORBA";
        const pageSize = config.pageSize || 10;

        let tenders = [];
        const proxyUrl = config.proxyUrl || localStorage.getItem("cgproc-gem-proxy") || "";
        if (proxyUrl) {
            tenders = await fetchViaProxy(proxyUrl, stateName, cityName);
        } else {
            tenders = await fetchDirectFromGem(stateName, cityName, pageSize);
        }

        tenders = mergeFirstSeen(tenders, existingTenders);
        return {
            tenders,
            stats: buildStats(tenders),
            fetched_at: new Date().toISOString().slice(0, 19),
        };
    }

    return {
        pullLive,
        mergeFirstSeen,
        buildStats,
    };
})();
