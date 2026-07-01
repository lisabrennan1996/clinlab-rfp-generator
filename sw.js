const CACHE = 'rfp-gen-v2';

const PRECACHE = [
  'index.html',
  'manifest.json',
  'ai-assist.js',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'engine/build_analytes.py',
  'engine/build_soa.py',
  'engine/build_specimen.py',
  'engine/populate_rfp.py',
  'engine/patch_docx.py',
  'liteparse/liteparse_wasm.js',
  'liteparse/liteparse_wasm_bg.js',
  'liteparse/liteparse_wasm_bg.wasm',
];

// CDN origins to cache on first fetch
const CDN_ORIGINS = [
  'cdn.jsdelivr.net',
  'huggingface.co',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Cache same-origin + CDN resources
  const shouldCache = url.origin === location.origin ||
    CDN_ORIGINS.some(o => url.hostname.endsWith(o));

  if (shouldCache) {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        if (cached) return cached;
        return fetch(e.request).then((res) => {
          if (res.ok && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE).then((c) => c.put(e.request, clone));
          }
          return res;
        });
      })
    );
  }
  // Pass through for everything else
});
