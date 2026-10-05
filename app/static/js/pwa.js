/* Corn Disease PWA cache manager - v9-separated-evaluation-uji-citra */
const CURRENT_SW = '/service-worker.js?v=10-green-final';
const CURRENT_CACHE_PREFIX = 'corn-disease-ui-v11-separated-pages';

async function cleanOldPwaState() {
  // Remove registrations left by older versions of this project.
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map(reg => {
      const script = reg.active?.scriptURL || reg.waiting?.scriptURL || reg.installing?.scriptURL || '';
      const sameOrigin = script.startsWith(window.location.origin);
      const isCurrent = script.includes('/service-worker.js');
      return sameOrigin && isCurrent ? Promise.resolve() : reg.unregister();
    }));
  }

  // Delete every old cache belonging to previous builds.
  if ('caches' in window) {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter(key => key.startsWith('corn-disease-ui-') && key !== CURRENT_CACHE_PREFIX)
      .map(key => caches.delete(key)));
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  if (!('serviceWorker' in navigator)) return;
  try {
    await cleanOldPwaState();
    const reg = await navigator.serviceWorker.register(CURRENT_SW, { updateViaCache: 'none' });
    await reg.update();
    if (reg.waiting) reg.waiting.postMessage({ type: 'SKIP_WAITING' });
  } catch (e) {
    console.warn('PWA service worker:', e);
  }
});
