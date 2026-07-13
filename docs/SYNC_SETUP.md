# Cross-device shortlist sync

Shortlist sync uses **Firebase Realtime Database** (free tier). The same sync code on phone, laptop, or tablet loads the same shortlist.

## One-time setup (about 5 minutes)

### 1. Create a Firebase project

1. Go to [https://console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add project** → name it e.g. `cgproc-tenders` → create
3. Disable Google Analytics if you want (optional)

### 2. Enable Realtime Database

1. In Firebase console → **Build** → **Realtime Database**
2. Click **Create Database**
3. Choose a region (e.g. `asia-southeast1`)
4. Start in **test mode** for now (we'll add rules next)
5. Copy the database URL, e.g. `https://cgproc-tenders-default-rtdb.firebaseio.com`

### 3. Get web app config

1. Project **Settings** (gear icon) → **General**
2. Under **Your apps** → click **Web** `</>`
3. Register app name: `cgproc-dashboard`
4. Copy the `firebaseConfig` values

### 4. Add config to this repo

Edit `docs/firebase-config.js`:

```javascript
window.FIREBASE_CONFIG = {
  apiKey: "AIza...",
  authDomain: "cgproc-tenders.firebaseapp.com",
  databaseURL: "https://cgproc-tenders-default-rtdb.firebaseio.com",
  projectId: "cgproc-tenders",
};
```

Commit and push:

```bash
git add docs/firebase-config.js
git commit -m "Add Firebase config for shortlist sync"
git push
```

### 5. Set database rules

In Firebase console → **Realtime Database** → **Rules**, paste:

```json
{
  "rules": {
    "shortlists": {
      "$syncCode": {
        ".read": true,
        ".write": true
      }
    }
  }
}
```

Click **Publish**.

> **Note:** Anyone who knows your sync code can read/write that shortlist. Use a private code only you know (e.g. `my-secret-tenders-2026`).

## Using sync on devices

1. Open your dashboard on **device 1**
2. In **Sync shortlist across devices**, click **Generate** or enter a code → **Connect**
3. Shortlist tenders with the star button
4. On **device 2**, open the same site, enter the **same sync code** → **Connect**
5. Your shortlist appears automatically and stays in sync

## Without Firebase

If `firebase-config.js` is not configured, shortlist still works but only on the current browser (localStorage).
