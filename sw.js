/* ─────────────────────────────────────────────────────────────────────────
   sw.js — Minimal Service Worker
   This app is served via a local HTTP server (required by Pyodide).
   The SW just enables PWA installation without interfering with requests.
   ───────────────────────────────────────────────────────────────────────── */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => self.clients.claim());
// No fetch handler — all requests go directly to the HTTP server,
// exactly as they do when the app is opened in a regular browser tab.
