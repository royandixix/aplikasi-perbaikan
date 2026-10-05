/* Corn Disease Service Worker - v8 separated evaluation and uji citra */
const CACHE_NAME = 'corn-disease-ui-v11-separated-pages';
const OLD_PREFIX = 'corn-disease-ui-';
const CORE_ASSETS = [
  '/',
  '/static/css/style.css?v=20260814-7',
  '/static/js/app.js?v=20260814-7',
  '/static/js/pwa.js?v=20260814-7',
  '/static/manifest.json',
  '/static/icons/icon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-maskable-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(key => key.startsWith(OLD_PREFIX) && key !== CACHE_NAME)
           .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data?.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key))))
    );
  }
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === '/service-worker.js' || url.pathname.startsWith('/api/') || url.pathname.startsWith('/data/')) return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.ok && response.type !== 'opaque') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy)).catch(() => {});
        }
        return response;
      }).catch(() => {
        if (event.request.mode === 'navigate') return caches.match('/');
        return new Response('', { status: 504, statusText: 'Offline' });
      });
    })
  );
});
