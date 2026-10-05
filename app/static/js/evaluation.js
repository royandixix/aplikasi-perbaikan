function metric(v) {
  if (v === undefined || v === null || Number.isNaN(Number(v))) return '—';
  return typeof v === 'number' ? (Math.abs(v) <= 1 ? (v * 100).toFixed(1) + '%' : v.toFixed(3)) : v;
}
function duration(v) {
  if (v === undefined || v === null || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n < 1 ? `${(n * 1000).toFixed(2)} ms` : `${n.toFixed(3)} s`;
}
function modelRows(data) { return Array.isArray(data?.models) ? data.models : []; }
function modelTitle(row) { return `${CornDisease.formatModel(row.model)}${row.k ? ` (k=${row.k})` : ''}`; }

function renderDataset(data) {
  const d = data.dataset || {};
  const cards = document.querySelectorAll('#datasetEvalCards .dataset-eval-card');
  [d.train, d.val, d.test, d.feature_count].forEach((value, i) => {
    const strong = cards[i]?.querySelector('strong');
    if (strong) strong.textContent = value ?? '—';
  });
  document.getElementById('selectionBasis').textContent =
    data.selection_basis === 'validation'
      ? 'Model terbaik dipilih berdasarkan validation'
      : 'Belum ada hasil training';
  document.getElementById('protocolTrain').textContent = d.train ?? '—';
  document.getElementById('protocolVal').textContent = d.val ?? '—';
  document.getElementById('protocolFit').textContent = d.train_plus_val ?? '—';
  document.getElementById('protocolTest').textContent = d.test ?? '—';
}

function validationFor(row, validationRows) {
  return (validationRows || []).find(v =>
    v.model === row.model && (!row.k || Number(v.k) === Number(row.k))
  );
}

function renderTable(data) {
  const body = document.querySelector('#modelTable tbody');
  const rows = modelRows(data);
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-4">Belum ada hasil evaluasi. Jalankan training terlebih dahulu.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(r => `
    <tr>
      <td><b>${modelTitle(r)}</b></td>
      <td>${r.k ?? '—'}</td>
      <td>${metric(r.accuracy)}</td>
      <td>${metric(r.macro_precision)}</td>
      <td>${metric(r.macro_recall)}</td>
      <td>${metric(r.macro_f1)}</td>
      <td>${duration(r.test_time ?? r.evaluation_time ?? r.training_time)}</td>
    </tr>`).join('');

  const best = data.best_model || {};
  document.getElementById('bestModelName').textContent = CornDisease.formatModel(best.model);
  document.getElementById('bestModelK').textContent = best.k ? `K = ${best.k}` : 'Model terbaik';
  document.getElementById('bestAccuracy').textContent = metric(best.validation_accuracy);
  document.getElementById('bestF1').textContent = metric(best.validation_macro_f1);

  renderAllMatrices(rows, data.dataset?.classes || []);
  renderCalculations(rows, data.validation || [], data.dataset?.classes || []);
  renderReport(rows, data.dataset?.classes || []);
}

function labelName(label) {
  return CornDisease.formatDisease(label);
}

function renderMatrixHtml(matrix, labels) {
  if (!Array.isArray(matrix) || !matrix.length) {
    return '<div class="text-secondary small">Confusion matrix belum tersedia.</div>';
  }
  const names = labels.length ? labels : matrix.map((_, i) => `Kelas ${i + 1}`);
  return `<table class="matrix-table">
    <tr><th>Aktual \\ Prediksi</th>${names.map(x => `<th>${labelName(x).split(' ')[0]}</th>`).join('')}</tr>
    ${matrix.map((row, i) => `<tr>
      <th>${labelName(names[i]).split(' ')[0]}</th>
      ${row.map((v, j) => `<td class="${i === j ? 'diag' : ''}" title="${i === j ? 'Prediksi benar' : 'Prediksi salah'}">${v}</td>`).join('')}
    </tr>`).join('')}
  </table>`;
}

function renderAllMatrices(rows, labels) {
  const root = document.getElementById('allMatrices');
  if (!root) return;
  root.innerHTML = rows.map((r, i) => `
    <div class="matrix-card">
      <div class="matrix-card-header"><strong>${modelTitle(r)}</strong><span>Accuracy ${metric(r.accuracy)}</span></div>
      <div class="matrix-wrap">${renderMatrixHtml(r.confusion_matrix, labels)}</div>
    </div>`).join('') || '<div class="text-secondary">Belum ada confusion matrix.</div>';
}

function matrixStats(matrix) {
  const n = Array.isArray(matrix) ? matrix.length : 0;
  if (!n) return null;
  const total = matrix.flat().reduce((a, b) => a + Number(b || 0), 0);
  const correct = matrix.reduce((sum, row, i) => sum + Number(row[i] || 0), 0);
  const classes = [];
  for (let i = 0; i < n; i++) {
    const tp = Number(matrix[i][i] || 0);
    const fp = matrix.reduce((sum, row) => sum + Number(row[i] || 0), 0) - tp;
    const fn = (matrix[i] || []).reduce((sum, x) => sum + Number(x || 0), 0) - tp;
    const precision = tp + fp ? tp / (tp + fp) : 0;
    const recall = tp + fn ? tp / (tp + fn) : 0;
    const f1 = precision + recall ? 2 * precision * recall / (precision + recall) : 0;
    classes.push({ tp, fp, fn, precision, recall, f1, support: tp + fn });
  }
  const macro = key => classes.reduce((s, x) => s + x[key], 0) / n;
  return { total, correct, accuracy: total ? correct / total : 0, classes, precision: macro('precision'), recall: macro('recall'), f1: macro('f1') };
}

function calculationBlock(row, labels, validationRow) {
  const stats = matrixStats(row.confusion_matrix);
  if (!stats) return '';
  const names = labels.length ? labels : stats.classes.map((_, i) => `Kelas ${i + 1}`);
  const classRows = stats.classes.map((c, i) => `
    <tr>
      <td>${labelName(names[i])}</td>
      <td>${c.tp}</td><td>${c.fp}</td><td>${c.fn}</td>
      <td>${metric(c.precision)}</td><td>${metric(c.recall)}</td><td>${metric(c.f1)}</td>
    </tr>`).join('');
  const vStats = validationRow ? matrixStats(validationRow.confusion_matrix) : null;
  return `<details class="calculation-card" open>
    <summary><span>${modelTitle(row)}</span><b>Accuracy ${metric(row.accuracy)}</b></summary>
    <div class="calculation-body">
      <div class="formula-box">
        <div class="formula-title">1. Accuracy — Test Set</div>
        <code>Accuracy = jumlah prediksi benar / seluruh data</code>
        <div class="formula-line">= (${stats.classes.map(c => c.tp).join(' + ')}) / ${stats.total}</div>
        <div class="formula-line">= ${stats.correct} / ${stats.total} = <strong>${metric(stats.accuracy)}</strong></div>
      </div>
      <div class="table-responsive">
        <table class="table table-dark-custom calc-table">
          <thead><tr><th>Kelas</th><th>TP</th><th>FP</th><th>FN</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
          <tbody>${classRows}</tbody>
        </table>
      </div>
      <div class="formula-grid">
        <div class="formula-box"><div class="formula-title">2. Macro Precision</div><code>Precision = TP / (TP + FP)</code><div class="formula-line">= (${stats.classes.map(c => metric(c.precision)).join(' + ')}) / ${stats.classes.length}</div><strong>${metric(stats.precision)}</strong></div>
        <div class="formula-box"><div class="formula-title">3. Macro Recall</div><code>Recall = TP / (TP + FN)</code><div class="formula-line">= (${stats.classes.map(c => metric(c.recall)).join(' + ')}) / ${stats.classes.length}</div><strong>${metric(stats.recall)}</strong></div>
        <div class="formula-box"><div class="formula-title">4. Macro F1-score</div><code>F1 = 2 × Precision × Recall / (Precision + Recall)</code><div class="formula-line">Rata-rata F1 setiap kelas</div><strong>${metric(stats.f1)}</strong></div>
      </div>
      ${vStats ? `<div class="validation-note"><b>Validation untuk pemilihan model:</b> Accuracy ${metric(vStats.accuracy)} · Macro Precision ${metric(vStats.precision)} · Macro Recall ${metric(vStats.recall)} · Macro F1 ${metric(vStats.f1)}. Test tidak digunakan untuk memilih model.</div>` : ''}
    </div>
  </details>`;
}

function renderCalculations(rows, validationRows, labels) {
  const root = document.getElementById('metricCalculations');
  if (!root) return;
  root.innerHTML = rows.map(row => calculationBlock(row, labels, validationFor(row, validationRows))).join('') ||
    '<div class="text-secondary py-4">Belum ada perhitungan.</div>';
}

function renderReport(rows, labels) {
  const body = document.querySelector('#classificationTable tbody');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="text-secondary">Classification report belum tersedia.</td></tr>';
    return;
  }
  body.innerHTML = rows.flatMap(model => {
    const report = model.classification_report || {};
    const names = labels.length ? labels : Object.keys(report).filter(k => !['accuracy','macro avg','weighted avg'].includes(k));
    return names.map(k => {
      const r = report[k] || {};
      return `<tr><td><b>${modelTitle(model)}</b></td><td>${labelName(k)}</td><td>${metric(r.precision)}</td><td>${metric(r.recall)}</td><td>${metric(r['f1-score'])}</td><td>${r.support ?? '—'}</td></tr>`;
    });
  }).join('');
}

function renderDetail(kind, data) {
  const root = document.getElementById(kind + 'Content');
  const row = data?.data;
  if (!row) {
    root.innerHTML = '<div class="text-secondary py-4">Hasil training belum tersedia. Jalankan training terlebih dahulu.</div>';
    return;
  }
  if (kind === 'c45') {
    root.innerHTML = `
      <div class="metric-box"><span>Criterion</span><strong>${row.criterion || 'entropy'}</strong><small>${row.node_count ?? '—'} node · depth ${row.depth ?? '—'}</small></div>
      <div class="metric-box"><span>Feature</span><strong>${row.feature_count ?? '—'}</strong><small>Feature vector yang digunakan model</small></div>
      <div class="tree-text"><div class="panel-kicker mb-2">STRUKTUR DECISION TREE</div><pre>${row.tree || 'Tree belum tersedia.'}</pre></div>`;
  } else if (kind === 'gnb') {
    const priors = row.class_prior || [];
    root.innerHTML = `
      <div class="metric-box"><span>Class Prior</span><strong>${priors.map(x => Number(x).toFixed(3)).join(' · ') || '—'}</strong><small>Probabilitas awal masing-masing kelas.</small></div>
      <div class="prob-grid">${priors.map((x, i) => `<div class="metric-box"><span>${labelName((row.classes || [])[i] || `Kelas ${i+1}`)}</span><strong>${(Number(x)*100).toFixed(2)}%</strong><small>Class prior</small></div>`).join('')}</div>
      <div class="metric-box"><span>Parameter</span><strong>${row.feature_count ?? '—'} fitur</strong><small>Mean dan variance tersimpan pada model.</small></div>`;
  } else {
    const rows = Array.isArray(data.data) ? data.data : [];
    root.innerHTML = rows.map(r => `<div class="metric-box"><span>K = ${r.k ?? '—'}</span><strong>${metric(r.accuracy)}</strong><small>Precision ${metric(r.macro_precision)} · Recall ${metric(r.macro_recall)} · F1 ${metric(r.macro_f1)}</small></div>`).join('') || '<div class="text-secondary">Model KNN belum tersedia.</div>';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  document.querySelectorAll('.eval-tab').forEach(tab => tab.addEventListener('click', () => {
    document.querySelectorAll('.eval-tab').forEach(x => x.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.eval-view').forEach(x => x.classList.add('d-none'));
    const map = {summary:'Summary', c45:'C45', gnb:'Gnb', knn:'Knn'};
    const target = document.getElementById('eval' + map[tab.dataset.evalTab]);
    if (target) target.classList.remove('d-none');
  }));

  try {
    const res = await CornDisease.api('/api/evaluation/');
    const data = res.data || {};
    renderDataset(data);
    renderTable(data);
    const [c,g,k] = await Promise.all([
      CornDisease.api('/api/evaluation/c45'),
      CornDisease.api('/api/evaluation/gaussian-nb'),
      CornDisease.api('/api/evaluation/knn')
    ]);
    renderDetail('c45', c);
    renderDetail('gnb', g);
    renderDetail('knn', k);
  } catch(e) {
    CornDisease.toast(e.message,'error');
  }
});
