window.GEM_API = {
    state: "CHHATTISGARH",
    city: "KORBA",
    pageSize: 10,
    // Deploy the gem-proxy/ folder to Vercel (Root Directory = gem-proxy), then paste URL here.
    // Example: https://cgproc-sezk.vercel.app/api/gem/fetch
    proxyUrl: localStorage.getItem("cgproc-gem-proxy") || "",
};
