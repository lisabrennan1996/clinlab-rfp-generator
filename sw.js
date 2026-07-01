// Minimal SW — enables PWA install, does not intercept requests
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => self.clients.claim());
