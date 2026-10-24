/* B-SIDE service worker: repeat visits load instantly and the game keeps working offline.
   - Pages: network first, so players always get the newest deploy when online; the cached copy when offline.
   - Fonts, icons, images and data/songs.json: answered from the cache and refreshed in the background
     (stale-while-revalidate), so they never block a load twice.
   - Requests to other origins (the Supabase API) are left alone.
   Bump VERSION to drop every old cache when the caching rules change. */
const VERSION = 'bside-v1';
const CORE = ['/', '/data/songs.json', '/assets/fonts/pixelify-sans.woff2', '/assets/fonts/chakra-petch-400.woff2', '/assets/fonts/chakra-petch-600.woff2'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname === '/sw.js') return;

  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            e.waitUntil(caches.open(VERSION).then((c) => c.put('/', copy)));
          }
          return res;
        })
        .catch(() => caches.match('/'))
    );
    return;
  }

  e.respondWith(
    caches.open(VERSION).then(async (cache) => {
      const cached = await cache.match(req);
      const fresh = fetch(req)
        .then((res) => {
          if (res.ok) cache.put(req, res.clone());
          return res;
        })
        .catch(() => cached);
      if (cached) {
        e.waitUntil(fresh);
        return cached;
      }
      return fresh;
    })
  );
});
