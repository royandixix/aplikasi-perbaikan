window.CornDisease = (() => {
  const api = async (url, options = {}) => {
    const response = await fetch(url, options);
    let data = null;
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(data?.message || `Request gagal (${response.status})`);
    return data;
  };

  const toast = (message, type = 'success') => {
    const wrap = document.getElementById('toastContainer');
    if (!wrap) return;
    const el = document.createElement('div');
    el.className = `toast ${type} show`;
    el.setAttribute('role', 'alert');
    el.innerHTML = `<div class="d-flex"><div class="toast-body"><i class="bi ${type === 'error' ? 'bi-exclamation-triangle' : 'bi-check-circle'} me-2"></i>${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    wrap.appendChild(el);
    setTimeout(() => el.remove(), 4200);
  };

  const formatDisease = name => ({
    Bercak_Daun: 'Bercak Daun',
    Hawar_Daun: 'Hawar Daun',
    Bulai_Daun: 'Bulai Daun'
  }[name] || name || '—');

  const formatModel = name => ({
    c45: 'C4.5',
    gaussian_nb: 'Gaussian NB',
    knn: 'KNN'
  }[name] || name || '—');

  const percent = n => `${(Number(n || 0)).toFixed(1)}%`;

  // Mendukung URL baru /data/... dan membersihkan path Windows lama.
  const fileUrl = value => {
    if (!value) return '';
    let p = String(value).replaceAll('\\', '/');
    if (p.startsWith('/data/') || p.startsWith('/static/')) return p;
    const dataMarker = '/data/';
    if (p.includes(dataMarker)) return dataMarker + p.split(dataMarker).pop();
    const staticMarker = '/app/static/';
    if (p.includes(staticMarker)) return '/static/' + p.split(staticMarker).pop();
    const winDataMarker = '/data/';
    if (/^[A-Za-z]:\//.test(p) && p.includes(winDataMarker)) return '/data/' + p.split(winDataMarker).pop();
    return `/data/${p.replace(/^\/+/, '')}`;
  };

  return { api, toast, formatDisease, formatModel, percent, fileUrl };
})();

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('appSidebar');
  toggle?.addEventListener('click', () => sidebar?.classList.toggle('open'));
  document.querySelectorAll('.side-link').forEach(a => a.addEventListener('click', () => sidebar?.classList.remove('open')));

  const themeButton = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');
  const themeMeta = document.getElementById('themeColorMeta');
  const root = document.documentElement;

  const applyTheme = theme => {
    const normalized = theme === 'dark' ? 'dark' : 'light';
    root.setAttribute('data-bs-theme', normalized);
    localStorage.setItem('cornDiseaseTheme', normalized);
    if (themeIcon) themeIcon.className = normalized === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    if (themeButton) {
      themeButton.title = normalized === 'dark' ? 'Gunakan mode terang' : 'Gunakan mode gelap';
      themeButton.setAttribute('aria-label', normalized === 'dark' ? 'Ganti ke mode terang' : 'Ganti ke mode gelap');
    }
    if (themeMeta) themeMeta.setAttribute('content', '#0f6b3f');
  };

  applyTheme(root.getAttribute('data-bs-theme'));
  themeButton?.addEventListener('click', () => {
    applyTheme(root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
  });
});

document.addEventListener('click', event => {
  const trigger = event.target.closest('[data-image-preview]');
  if (!trigger) return;
  const src = trigger.getAttribute('data-image-preview');
  if (!src) return;
  const title = trigger.getAttribute('data-preview-title') || 'Visualisasi';
  const meta = trigger.getAttribute('data-preview-meta') || '';
  const image = document.getElementById('imagePreviewModalImage');
  const titleEl = document.getElementById('imagePreviewModalLabel');
  const metaEl = document.getElementById('imagePreviewModalMeta');
  if (!image || !titleEl) return;
  image.src = src;
  image.alt = title;
  titleEl.textContent = title;
  if (metaEl) metaEl.textContent = meta;
  const modalEl = document.getElementById('imagePreviewModal');
  if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
});
