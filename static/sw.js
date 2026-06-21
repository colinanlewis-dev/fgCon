const CACHE = 'fgcon-v1';

// Pages and assets to pre-cache on install
const SHELL = [
  '/',
  '/orders',
  '/static/glemons.png',
];

// API routes worth caching for offline fallback
const CACHE_API = [
  '/api/orders/init',
  '/api/events/active',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  // Only handle same-origin GETs
  if (request.method !== 'GET') return;
  if (url.origin !== location.origin) return;

  // API routes: network first, fall back to cache
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(request)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(request, clone));
          }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Pages and static assets: cache first, update in background
  e.respondWith(
    caches.match(request).then(cached => {
      const networkFetch = fetch(request).then(res => {
        if (res.ok) {
          caches.open(CACHE).then(c => c.put(request, res.clone()));
        }
        return res;
      });
      return cached || networkFetch;
    })
  );
});
