const processingKeys = [
  ['original','Original'], ['resize','Resize'], ['normalisasi','Normalisasi'],
  ['rgb','RGB'], ['hsv','HSV'], ['grayscale','Grayscale'], ['histogram','Histogram'],
  ['lbp','LBP'], ['entropy',null], ['sobel','Sobel'], ['laplacian','Laplacian'],
  ['feature_vector','Feature Vector']
];

const timingLabels = {
  original: 'Original / baca citra',
  resize: 'Resize',
  normalisasi: 'Normalisasi',
  rgb: 'RGB',
  hsv: 'HSV',
  grayscale: 'Grayscale',
  histogram: 'Histogram',
  lbp: 'LBP',
  entropy: 'Entropy',
  sobel: 'Sobel',
  laplacian: 'Laplacian',
  feature_vector: 'Feature vector'
};

function safeImage(src, label, timing) {
  if (!src) {
    return `<div class="feature-card"><div class="feature-missing"><i class="bi bi-image-alt"></i><span>Visualisasi belum tersedia</span></div><div class="feature-caption"><strong>${label}</strong><small>Belum tersedia</small></div></div>`;
  }
  const safeSrc = String(src).replace(/"/g, '&quot;');
  const meta = timing != null ? `Waktu proses ${Number(timing * 1000).toFixed(2)} ms` : 'Visualisasi proses';
  return `<div class="feature-card">
    <button type="button" class="feature-image-trigger" data-image-preview="${safeSrc}" data-preview-title="${label}" data-preview-meta="${meta}" aria-label="Perbesar ${label}">
      <img src="${safeSrc}" alt="${label}" loading="lazy">
      <span class="zoom-hint"><i class="bi bi-arrows-fullscreen"></i></span>
    </button>
    <div class="feature-caption"><strong>${label}</strong><small>${meta}</small></div>
  </div>`;
}

function renderTimingGrid(timings) {
  const root = document.getElementById('processingTimingGrid');
  const totalEl = document.getElementById('processingTotalTime');
  if (!root) return;
  const entries = Object.entries(timings || {}).filter(([key]) => key !== 'total' && timingLabels[key]);
  if (!entries.length) {
    root.innerHTML = `<div class="timing-empty">Data waktu pemrosesan belum tersimpan. Lakukan deteksi baru untuk merekam waktu.</div>`;
    if (totalEl) totalEl.textContent = '—';
    return;
  }
  root.innerHTML = entries.map(([key, value]) => `
    <div class="timing-item">
      <span>${timingLabels[key]}</span>
      <strong>${(Number(value) * 1000).toFixed(2)} ms</strong>
    </div>`).join('');
  if (totalEl) totalEl.textContent = `${(Number(timings.total || 0) * 1000).toFixed(2)} ms total`;
}

function formatFeatureValue(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toFixed(6);
}

function buildFeatureGroupsFallback(featureData) {
  const values = (featureData?.values || featureData?.feature_vector || []).map(Number);
  const existing = featureData?.groups || featureData?.feature_groups;
  if (existing && Object.keys(existing).length) return existing;
  const spec = [
    ['rgb', 12], ['hsv', 12], ['rgb_hist', 48], ['hsv_hist', 48],
    ['gray_hist', 16], ['lbp', 26], ['entropy', 1], ['sobel', 7], ['laplacian', 3]
  ];
  const canonical = {
    rgb: ['R','G','B'].flatMap(c => ['mean','std','min','max'].map(s => `rgb_${c}_${s}`)),
    hsv: ['H','S','V'].flatMap(c => ['mean','std','min','max'].map(s => `hsv_${c}_${s}`)),
    rgb_hist: ['R','G','B'].flatMap(c => Array.from({length:16}, (_,i) => `rgb_hist_${c}_bin_${String(i+1).padStart(2,'0')}`)),
    hsv_hist: ['H','S','V'].flatMap(c => Array.from({length:16}, (_,i) => `hsv_hist_${c}_bin_${String(i+1).padStart(2,'0')}`)),
    gray_hist: Array.from({length:16}, (_,i) => `gray_hist_C1_bin_${String(i+1).padStart(2,'0')}`),
    lbp: Array.from({length:26}, (_,i) => `lbp_LBP_bin_${String(i+1).padStart(2,'0')}`),
    entropy: ['entropy'],
    sobel: ['sobel_x_mean_abs','sobel_x_std','sobel_y_mean_abs','sobel_y_std','sobel_magnitude_mean','sobel_magnitude_std','sobel_magnitude_max'],
    laplacian: ['laplacian_mean_abs','laplacian_std','laplacian_max_abs']
  };
  const names = featureData?.names || featureData?.feature_names || [];
  const groups = {};
  let offset = 0;
  spec.forEach(([key, count]) => {
    const chunk = values.slice(offset, offset + count);
    if (!chunk.length) return;
    const sourceNames = names.slice(offset, offset + chunk.length);
    const genericPattern = /^(?:rgb|hsv|rgb_hist|hsv_hist|gray_hist|lbp)_\d+$/;
    const generic = sourceNames.length !== chunk.length || sourceNames.every(n => genericPattern.test(String(n)));
    groups[key] = {
      count: chunk.length, start_index: offset, end_index: offset + chunk.length - 1,
      names: generic ? canonical[key].slice(0, chunk.length) : sourceNames, values: chunk
    };
    offset += count;
  });
  return groups;
}

function renderFeatureGroups(groups) {
  const root = document.getElementById('featureGroups');
  if (!root) return;
  const order = ['rgb', 'hsv', 'rgb_hist', 'hsv_hist', 'gray_hist', 'lbp', 'entropy', 'sobel', 'laplacian'];
  const labels = {
    rgb: 'RGB — Mean, Std, Min, Max per channel',
    hsv: 'HSV — Mean, Std, Min, Max per channel',
    rgb_hist: 'Histogram RGB — 16 bin/channel',
    hsv_hist: 'Histogram HSV — 16 bin/channel',
    gray_hist: 'Histogram Grayscale — 16 bin',
    lbp: 'LBP — Histogram tekstur',
    entropy: 'Entropy — Shannon entropy',
    sobel: 'Sobel — Statistik edge',
    laplacian: 'Laplacian — Statistik perubahan intensitas'
  };
  const keys = order.filter(k => groups[k]);
  if (!keys.length) {
    root.innerHTML = '<div class="timing-empty">Nilai fitur belum tersedia. Lakukan deteksi baru.</div>';
    return;
  }
  root.innerHTML = keys.map(key => {
    const g = groups[key] || {};
    const names = g.names || [];
    const vals = g.values || [];
    const rows = names.map((name, i) => `<tr><td>${name}</td><td>${formatFeatureValue(vals[i])}</td></tr>`).join('');
    return `<div class="feature-group-card">
      <div class="feature-group-head"><strong>${labels[key] || key}</strong><span>${g.count || vals.length || 0} fitur</span></div>
      <div class="table-responsive"><table class="table table-sm feature-values-table"><thead><tr><th>Nama Fitur</th><th>Nilai</th></tr></thead><tbody>${rows}</tbody></table></div>
    </div>`;
  }).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
  const id = window.CORN_PROCESSING_ID;
  if (!id) {
    CornDisease.toast('Belum ada hasil deteksi. Silakan lakukan deteksi dari Dashboard.', 'error');
    return;
  }
  try {
    const res = await CornDisease.api(`/api/history/${id}`);
    const d = res.data || {};
    const processingData = d.processing || {};
    const files = processingData.files || processingData || {};
    const timings = processingData.timings || {};
    const fv = d.feature_vector || {};
    const steps = d.steps || [];

    document.getElementById('processingRecord').textContent = `#${d.id} · ${CornDisease.formatDisease(d.predicted_class)}`;
    document.getElementById('sourceFileName').textContent = d.image_name || '—';
    document.getElementById('sourceDisease').textContent = CornDisease.formatDisease(d.predicted_class);
    document.getElementById('sourceConfidence').textContent = CornDisease.percent(d.confidence);
    document.getElementById('sourceModel').textContent = CornDisease.formatModel(d.selected_model);

    const source = CornDisease.fileUrl(d.image_path);
    const sourceBox = document.getElementById('sourcePreview');
    if (source) {
      sourceBox.innerHTML = `<button type="button" class="source-image-trigger" data-image-preview="${source.replace(/"/g,'&quot;')}" data-preview-title="Citra Input" data-preview-meta="${(d.image_name || 'Citra hasil upload/capture').replace(/"/g,'&quot;')}"><img src="${source}" alt="${d.image_name || 'Citra daun jagung'}"><span class="zoom-hint"><i class="bi bi-arrows-fullscreen"></i> Klik untuk memperbesar</span></button>`;
      sourceBox.querySelector('img').addEventListener('error', () => {
        sourceBox.innerHTML = '<div class="empty-visual"><i class="bi bi-exclamation-octagon"></i><span>Gambar input tidak ditemukan</span></div>';
      });
    }

    const stepFor = key => steps.find(x => x.step_name.toLowerCase().replaceAll(' ', '') === key);
    document.getElementById('processingGallery').innerHTML = processingKeys.map(([key, label]) => {
      if (key === 'entropy') {
        const entropy = fv.entropy ?? '—';
        const t = timings.entropy;
        return `<div class="feature-card">
          <button type="button" class="feature-value-trigger" data-preview-title="Entropy" data-preview-meta="Nilai Shannon entropy: ${entropy}" aria-label="Detail entropy">
            <div class="feature-value-card"><div class="fs-4 fw-bold">${entropy}</div><small>Kompleksitas citra</small></div>
          </button>
          <div class="feature-caption"><strong>Entropy</strong><small>${t != null ? `${(Number(t)*1000).toFixed(2)} ms` : 'Nilai Shannon entropy'}</small></div>
        </div>`;
      }
      if (key === 'feature_vector') {
        return `<div class="feature-card">
          <button type="button" class="feature-value-trigger" data-preview-title="Feature Vector" data-preview-meta="${fv.values?.length || 0} fitur diekstraksi">
            <div class="feature-value-card feature-vector-icon"><i class="bi bi-braces"></i><small>${fv.values?.length || 0} nilai</small></div>
          </button>
          <div class="feature-caption"><strong>Feature Vector</strong><small>${fv.values?.length || 0} nilai</small></div>
        </div>`;
      }
      const src = CornDisease.fileUrl(files[key] || stepFor(key)?.image_path);
      return safeImage(src, label, timings[key]);
    }).join('');

    renderTimingGrid(timings);

    const values = fv.values || [];
    const groups = buildFeatureGroupsFallback(fv);
    renderFeatureGroups(groups);
    document.getElementById('featureCount').textContent = values.length || '0';
    document.getElementById('entropyValue').textContent = fv.entropy ?? '—';
    document.getElementById('featureVector').textContent = JSON.stringify(values.slice(0, 250), null, 2) + (values.length > 250 ? '\n…' : '');
    document.getElementById('copyFeatures').onclick = async () => {
      try {
        await navigator.clipboard.writeText(JSON.stringify(values));
        CornDisease.toast('Feature vector disalin.');
      } catch (_) {
        CornDisease.toast('Feature vector tidak dapat disalin.', 'error');
      }
    };
  } catch (e) {
    CornDisease.toast(e.message, 'error');
  }
});
