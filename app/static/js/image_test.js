function metric(v) {
  if (v === undefined || v === null || Number.isNaN(Number(v))) return '—';
  return typeof v === 'number' ? (Math.abs(v) <= 1 ? (v * 100).toFixed(1) + '%' : v.toFixed(3)) : v;
}
function modelTitle(row) { return `${CornDisease.formatModel(row.model)}${row.k ? ` (k=${row.k})` : ''}`; }
function labelName(label) { return CornDisease.formatDisease(label); }

let evalFile = null;
let evalStream = null;

function evalFileFromDataUrl(dataUrl, name='uji-citra-camera.jpg') {
  const [meta, data] = dataUrl.split(',');
  const bin = atob(data), arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new File([arr], name, {type: meta.match(/:(.*?);/)[1]});
}
function stopEvalCamera() {
  evalStream?.getTracks().forEach(t => t.stop());
  evalStream = null;
  const capture = document.getElementById('evalCaptureCamera');
  if (capture) capture.disabled = true;
}
async function startEvalCamera() {
  try {
    evalStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
    const v = document.getElementById('evalCameraVideo');
    v.srcObject = evalStream;
    await v.play();
    document.getElementById('evalCaptureCamera').disabled = false;
    CornDisease.toast('Kamera pengujian aktif.');
  } catch (e) {
    CornDisease.toast('Kamera tidak dapat diakses. Izinkan kamera pada browser.', 'error');
  }
}
function captureEvalCamera() {
  const v = document.getElementById('evalCameraVideo');
  if (!evalStream || !v.videoWidth) return null;
  const c = document.createElement('canvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
  return c.toDataURL('image/jpeg', .92);
}
function renderImageEvaluation(d) {
  document.getElementById('imageEvalEmpty').classList.add('d-none');
  document.getElementById('imageEvalContent').classList.remove('d-none');
  const imageUrl = CornDisease.fileUrl(d.image);
  document.getElementById('imageEvalSummary').innerHTML = `
    <button type="button" class="image-eval-preview-trigger" data-image-preview="${imageUrl}" data-preview-title="Citra Uji" data-preview-meta="${d.feature_count} fitur · Entropy ${Number(d.entropy||0).toFixed(4)}">
      <img src="${imageUrl}" alt="Citra uji"><span><i class="bi bi-arrows-fullscreen"></i> Perbesar</span>
    </button>
    <div class="image-eval-meta-text"><strong>${d.feature_count} fitur</strong><span>Entropy ${Number(d.entropy||0).toFixed(4)}</span><span>Label sebenarnya bersifat opsional</span></div>`;
  const predictions = d.predictions || [];
  document.querySelector('#imageModelTable tbody').innerHTML = predictions.map(r => `
    <tr><td><b>${modelTitle(r)}</b></td><td>${labelName(r.predicted_class)}</td><td>${metric(r.confidence)}</td><td>${r.label_match === null ? 'Tidak dinilai' : (r.label_match ? '✓ Sesuai' : '✕ Tidak sesuai')}</td></tr>`).join('');

  const sim = d.similarity || {};
  document.getElementById('splitSimilarity').innerHTML = `
    <div class="split-sim-title">Kemiripan Feature Vector terhadap Dataset</div>
    <div class="split-sim-grid">${[['train','Train'],['val','Validation'],['test','Test']].map(([k,label]) =>
      `<div class="metric-box"><span>${label}</span><strong>${metric(sim[k]?.similarity)}</strong><small>${sim[k]?.samples ?? 0} citra · jarak terdekat ${sim[k]?.nearest_distance?.toFixed?.(3) ?? '—'}</small></div>`).join('')}</div>`;
}
async function runImageEvaluation() {
  if (!evalFile) return;
  const btn = document.getElementById('runImageEvaluation');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Menguji...';
  try {
    const fd = new FormData();
    fd.append('image', evalFile);
    const trueLabel = document.getElementById('evalTrueLabel')?.value || '';
    if (trueLabel) fd.append('true_label', trueLabel);
    const res = await CornDisease.api('/api/evaluation/image', {method:'POST', body:fd});
    renderImageEvaluation(res.data);
    CornDisease.toast('Citra berhasil diuji terhadap model.');
  } catch(e) {
    CornDisease.toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-cpu"></i> Uji terhadap Model';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-image-input]').forEach(tab => tab.addEventListener('click', () => {
    document.querySelectorAll('[data-image-input]').forEach(x => x.classList.remove('active'));
    tab.classList.add('active');
    const upload = tab.dataset.imageInput === 'upload';
    document.getElementById('evalUploadPane').classList.toggle('d-none', !upload);
    document.getElementById('evalCameraPane').classList.toggle('d-none', upload);
    if (upload) stopEvalCamera();
  }));

  const input = document.getElementById('evalImageInput');
  input?.addEventListener('change', () => {
    evalFile = input.files[0] || null;
    if (evalFile) {
      const url = URL.createObjectURL(evalFile);
      document.getElementById('evalImagePreview').innerHTML = `<button type="button" class="source-image-trigger" data-image-preview="${url}" data-preview-title="Citra Uji" data-preview-meta="${evalFile.name}"><img src="${url}" alt="Citra uji"><span class="zoom-hint"><i class="bi bi-arrows-fullscreen"></i> Klik untuk memperbesar</span></button>`;
      document.getElementById('runImageEvaluation').disabled = false;
    }
  });

  document.getElementById('evalStartCamera')?.addEventListener('click', startEvalCamera);
  document.getElementById('evalCaptureCamera')?.addEventListener('click', () => {
    const url = captureEvalCamera();
    if (url) {
      evalFile = evalFileFromDataUrl(url);
      document.getElementById('evalImagePreview').innerHTML = `<button type="button" class="source-image-trigger" data-image-preview="${url}" data-preview-title="Citra hasil kamera" data-preview-meta="Capture kamera"><img src="${url}" alt="Citra hasil kamera"><span class="zoom-hint"><i class="bi bi-arrows-fullscreen"></i> Klik untuk memperbesar</span></button>`;
      document.getElementById('runImageEvaluation').disabled = false;
      stopEvalCamera();
    }
  });
  document.getElementById('runImageEvaluation')?.addEventListener('click', runImageEvaluation);
});
window.addEventListener('beforeunload', stopEvalCamera);
