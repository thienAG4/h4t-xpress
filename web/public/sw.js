// Service worker - lets the installed driver app open without network (SPEC D1, PWA).
//
// Pages: network first, the last good copy of the app shell when offline.
// /assets/*: hashed by Vite, so a cached copy never goes stale (cache first).
// API and WebSocket calls are never cached; they always go to the server.

const VERSION = "h4t-v1";
const SHELL = `${VERSION}-shell`;
const ASSETS = `${VERSION}-assets`;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.add("/")));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // A new VERSION drops every cache of the previous one.
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  // /api/docs is a page too, but it must never replace the cached app shell.
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(SHELL).then((cache) => cache.put("/", copy));
          }
          return response;
        })
        .catch(() => caches.match("/", { cacheName: SHELL })),
    );
    return;
  }

  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.match(request, { cacheName: ASSETS }).then(
        (cached) =>
          cached ??
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(ASSETS).then((cache) => cache.put(request, copy));
            }
            return response;
          }),
      ),
    );
  }
});
