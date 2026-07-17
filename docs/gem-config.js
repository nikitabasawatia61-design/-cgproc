window.GEM_API = {
    state: "CHHATTISGARH",
    city: "KORBA",
    pageSize: 10,
    // Deploy api/gem/fetch.js to Vercel (free), then paste the full URL here.
    // Example: https://your-app.vercel.app/api/gem/fetch
    proxyUrl: localStorage.getItem("cgproc-gem-proxy") || "",
};
