// HomeStack service worker — Web Push only (docs/32_Core_Notifications_and_Push.md §10).
// Deliberately minimal: no offline caching/asset strategy yet (that's a separate PWA decision).

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim())
})

// Payloads are always sparse (docs/32 §10) — a title/body and a deep link, never sensitive
// content. The click handler re-checks session/permission by loading the real app route.
self.addEventListener('push', event => {
  let payload = { title: 'HomeStack', body: 'You have a new notification.', url: '/' }
  try {
    if (event.data) payload = { ...payload, ...event.data.json() }
  } catch {
    // Non-JSON payload: fall back to the generic text above rather than failing silently.
  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/brand/mark-192.png',
      badge: '/brand/mark-192.png',
      data: { url: payload.url || '/' },
    })
  )
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      for (const client of clients) {
        if ('focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      return self.clients.openWindow(url)
    })
  )
})
