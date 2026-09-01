// 徒步助手 Service Worker — 离线缓存 + 瓦片缓存 + API 兜底
const CACHE_NAME = 'hiking-assistant-vmti2jhbq';
// 派生缓存（随 CACHE_NAME 版本自动轮换，activate 阶段统一清理）
const TILE_CACHE = CACHE_NAME + '-tiles';
const API_CACHE = CACHE_NAME + '-api';
// 瓦片缓存上限（防止缓存无限膨胀）
const MAX_TILES = 1500;

const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/favicon.svg',
  '/manifest.json',
];

// 安装：预缓存核心资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {
        // 某些资源可能不存在，忽略错误
      });
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// 激活：清理旧版本缓存（含派生缓存）
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !name.startsWith(CACHE_NAME))
          .map((name) => caches.delete(name))
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// 有界缓存写入：超过上限时淘汰最旧的
async function putBounded(cacheName, request, response, limit) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length >= limit) {
    // 淘汰最旧 10%
    await Promise.all(keys.slice(0, Math.ceil(keys.length * 0.1)).map((k) => cache.delete(k)));
  }
  await cache.put(request, response);
}

// 拦截请求
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // ---- 地图瓦片：缓存优先（离线也能看之前看过的区域）----
  if (event.request.method === 'GET' && url.hostname.includes('tile.openstreetmap.org')) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(TILE_CACHE);
        const cached = await cache.match(event.request);
        if (cached) return cached;
        try {
          const resp = await fetch(event.request);
          // opaque 响应没有 status，也要缓存
          if (resp.ok || resp.type === 'opaque') {
            await putBounded(TILE_CACHE, event.request, resp.clone(), MAX_TILES);
          }
          return resp;
        } catch {
          return new Response('', { status: 408 });
        }
      })()
    );
    return;
  }

  // ---- 路线 API：网络优先 + 缓存兜底（离线可看已访问过的路线详情/轨迹）----
  if (event.request.method === 'GET' && url.pathname.startsWith('/api/routes')) {
    event.respondWith(
      fetch(event.request).then((resp) => {
        if (resp.status === 200) {
          const clone = resp.clone();
          caches.open(API_CACHE).then((cache) => cache.put(event.request, clone));
        }
        return resp;
      }).catch(async () => {
        const cached = await caches.match(event.request, { cacheName: API_CACHE });
        if (cached) return cached;
        return new Response(JSON.stringify({ detail: '离线且无缓存数据' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        });
      })
    );
    return;
  }

  // API 其余请求：不缓存（网络优先，由浏览器处理）
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // ---- 静态资源：缓存优先 ----
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request).then((response) => {
        // 只缓存成功的 GET 请求
        if (
          event.request.method === 'GET' &&
          response.status === 200 &&
          (url.pathname.startsWith('/assets/') ||
           url.pathname === '/' ||
           url.pathname.endsWith('.js') ||
           url.pathname.endsWith('.css') ||
           url.pathname.endsWith('.svg') ||
           url.pathname.endsWith('.png'))
        ) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      }).catch(() => {
        // 离线时返回缓存首页（SPA fallback）
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
        return new Response('Offline', { status: 503 });
      });
    })
  );
});
