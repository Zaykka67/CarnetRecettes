// Service worker : l'appli s'ouvre même sans réseau, les recettes viennent du serveur.
const CACHE = 'carnet-v4';
const SHELL = ['/', '/app.css', '/app.js', '/manifest.webmanifest', '/icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;           // polices Google : laissées au navigateur
  if (url.pathname.startsWith('/api/')) return;          // données : toujours le réseau
  if (url.pathname.startsWith('/photos/')) {             // photos : cache d'abord
    e.respondWith(caches.open(CACHE).then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) c.put(req, res.clone());
      return res;
    }));
    return;
  }
  if (req.mode === 'navigate') {                         // pages : réseau, sinon version en cache
    e.respondWith(fetch(req).catch(() => caches.match('/')));
    return;
  }
  e.respondWith(caches.open(CACHE).then(async c => {    // fichiers de l'appli : cache puis mise à jour
    const hit = await c.match(req);
    const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => hit);
    return hit || net;
  }));
});
