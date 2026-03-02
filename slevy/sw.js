// SlevyDnes Service Worker — offline cache (stale-while-revalidate)
const CACHE_NAME = 'slevydnes-v3';
const PRECACHE = [
  './',
  './index.html',
  './manifest.json',
  './icons.svg',
  './slevy.json'
];

// Install — precache klíčové soubory
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// Activate — smazání starých cache
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch — stale-while-revalidate
self.addEventListener('fetch', e => {
  // Jen GET requesty
  if (e.request.method !== 'GET') return;

  e.respondWith(
    caches.open(CACHE_NAME).then(cache =>
      cache.match(e.request).then(cached => {
        const fetched = fetch(e.request).then(response => {
          // Uložit do cache jen úspěšné odpovědi
          if (response.ok) {
            cache.put(e.request, response.clone());
          }
          return response;
        }).catch(() => {
          // Offline — vrátit z cache nebo fallback
          return cached;
        });

        // Stale-while-revalidate: vrátit cached hned, update na pozadí
        return cached || fetched;
      })
    )
  );
});
