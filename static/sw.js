const CACHE = 'imarks-pwa-v1';
const PRECACHE = [
    '/manifest.webmanifest',
    '/favicon.ico',
    '/apple-touch-icon.png',
    '/home.js',
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE).then(function (cache) {
            return cache.addAll(PRECACHE);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.filter(function (key) {
                return key !== CACHE;
            }).map(function (key) {
                return caches.delete(key);
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', function (event) {
    if (event.request.method !== 'GET') return;
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;
    if (event.request.mode === 'navigate') {
        event.respondWith(fetch(event.request).catch(function () {
            return caches.match('/');
        }));
        return;
    }
    if (!PRECACHE.includes(url.pathname)) return;
    event.respondWith(
        fetch(event.request).then(function (response) {
            const copy = response.clone();
            caches.open(CACHE).then(function (cache) {
                cache.put(event.request, copy);
            });
            return response;
        }).catch(function () {
            return caches.match(event.request);
        })
    );
});
