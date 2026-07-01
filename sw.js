const CACHE = 'rfp-gen-v4';

const PRECACHE = [
  'index.html',
  'favicon.ico',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'manifest.json',
  'ai-assist.js',
  'worker.js',
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
    caches.open(CACHE).then((c) =>
      // Cache what we can — don't fail install if one file 404s
      Promise.allSettled(PRECACHE.map((url) =>
        c.add(url).catch(() => {})
      ))
    )
  );
  // Don't skipWaiting — let the SW wait for page refresh
  // so it never interferes with the first page load.
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  // Don't claim clients — first page load works without SW interference.
  // SW takes control on next visit (when PWA is reopened).
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
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
        }).catch(() => {
          // Network failed and nothing in cache — that's OK,
          // the app handles its own errors.
          return new Response('', { status: 503 });
        });
      })
    );
  }
  // Pass through for everything else
});
