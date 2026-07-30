// Minimal service worker: its ONLY job is to make offline.html reachable when the
// network is gone. It deliberately does not cache the app shell or any API response —
// a concert list served from cache would be worse than no list at all, and a cached
// app shell is how service workers start shipping stale UI.
const CACHE = "frontrow-offline-v1";
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(c => c.add(new Request(OFFLINE_URL, { cache: "reload" }))));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const { request } = event;
  // Top-level page loads only. Everything else — assets, API calls, the whole OAuth
  // dance — goes straight to the network, untouched.
  if (request.mode !== "navigate" || new URL(request.url).pathname.startsWith("/oauth2/")) return;
  event.respondWith(
    fetch(request).catch(() => caches.open(CACHE).then(c => c.match(OFFLINE_URL)))
  );
});
