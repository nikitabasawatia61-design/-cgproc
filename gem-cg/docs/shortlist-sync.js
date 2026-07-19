window.ShortlistSync = (function () {
    const SHORTLIST_KEY = "cgproc_shortlist";
    const SYNC_CODE_KEY = "cgproc_sync_code";

    let shortlisted = new Set();
    let listeners = [];
    let db = null;
    let listRef = null;
    let syncCode = "";
    let applyingRemote = false;
    let cloudReady = false;

    function notify() {
        listeners.forEach((fn) => fn(shortlisted, syncStatus()));
    }

    function syncStatus() {
        if (cloudReady && syncCode) {
            return { mode: "cloud", code: syncCode, message: "Synced across devices" };
        }
        if (isFirebaseConfigured()) {
            return { mode: "local", code: syncCode, message: "Local only — connect a sync code" };
        }
        return { mode: "offline", code: "", message: "Firebase not configured — local only" };
    }

    function isFirebaseConfigured() {
        const config = window.FIREBASE_CONFIG;
        return Boolean(
            config &&
            config.apiKey &&
            config.apiKey !== "YOUR_API_KEY" &&
            config.databaseURL &&
            !config.databaseURL.includes("YOUR_PROJECT")
        );
    }

    function loadLocalShortlist() {
        try {
            const saved = JSON.parse(localStorage.getItem(SHORTLIST_KEY) || "[]");
            shortlisted = new Set(Array.isArray(saved) ? saved.map(String) : []);
        } catch {
            shortlisted = new Set();
        }
    }

    function saveLocalShortlist() {
        localStorage.setItem(SHORTLIST_KEY, JSON.stringify([...shortlisted]));
    }

    function sanitizeSyncCode(value) {
        return String(value || "")
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9\-_]/g, "-")
            .replace(/-+/g, "-")
            .slice(0, 48);
    }

    function generateSyncCode() {
        const random = Math.random().toString(36).slice(2, 8);
        return `cg-${random}`;
    }

    function initFirebase() {
        if (!isFirebaseConfigured() || typeof firebase === "undefined") {
            return false;
        }
        if (!firebase.apps.length) {
            firebase.initializeApp(window.FIREBASE_CONFIG);
        }
        db = firebase.database();
        return true;
    }

    function disconnectCloud() {
        if (listRef) {
            listRef.off();
            listRef = null;
        }
        cloudReady = false;
    }

    function connectCloud(code) {
        const cleaned = sanitizeSyncCode(code);
        if (!cleaned) {
            throw new Error("Enter a sync code first");
        }
        if (!initFirebase()) {
            throw new Error("Firebase is not configured yet");
        }

        disconnectCloud();
        syncCode = cleaned;
        localStorage.setItem(SYNC_CODE_KEY, syncCode);

        listRef = db.ref(`shortlists/${syncCode}/tender_ids`);
        listRef.on("value", (snapshot) => {
            const remote = snapshot.val();
            const remoteList = Array.isArray(remote) ? remote.map(String) : [];
            applyingRemote = true;
            shortlisted = new Set(remoteList);
            applyingRemote = false;
            saveLocalShortlist();
            cloudReady = true;
            notify();
        });

        if (shortlisted.size > 0) {
            listRef.set([...shortlisted]);
        }

        notify();
        return syncCode;
    }

    function persistShortlist() {
        saveLocalShortlist();
        if (!applyingRemote && listRef) {
            listRef.set([...shortlisted]);
        }
        notify();
    }

    return {
        init() {
            loadLocalShortlist();
            syncCode = localStorage.getItem(SYNC_CODE_KEY) || "";

            if (syncCode && initFirebase()) {
                try {
                    connectCloud(syncCode);
                    return;
                } catch {
                    disconnectCloud();
                }
            }
            notify();
        },

        onChange(fn) {
            listeners.push(fn);
        },

        getAll() {
            return shortlisted;
        },

        has(tenderNo) {
            return shortlisted.has(String(tenderNo));
        },

        toggle(tenderNo) {
            const id = String(tenderNo);
            if (shortlisted.has(id)) {
                shortlisted.delete(id);
            } else {
                shortlisted.add(id);
            }
            persistShortlist();
        },

        connect(code) {
            return connectCloud(code);
        },

        generateCode() {
            return generateSyncCode();
        },

        getSyncCode() {
            return syncCode;
        },

        isCloudEnabled() {
            return cloudReady;
        },

        status() {
            return syncStatus();
        },

        isConfigured() {
            return isFirebaseConfigured();
        },
    };
})();
