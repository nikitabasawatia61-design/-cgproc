import http from "http";
import { URL } from "url";
import handler from "./api/gem/fetch.js";

const PORT = process.env.PORT || 3000;

const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === "/health") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, service: "cgproc-gem-proxy" }));
        return;
    }

    if (url.pathname === "/api/gem/fetch") {
        await handler(
            {
                method: req.method,
                query: Object.fromEntries(url.searchParams.entries()),
            },
            res
        );
        return;
    }

    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(PORT, () => {
    console.log(`GeM proxy listening on port ${PORT}`);
});
