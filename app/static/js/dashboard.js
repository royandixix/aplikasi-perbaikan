let selectedFile=null, lastPrediction=null;

function setPreview(src){
  const box=document.getElementById('imagePreview');
  box.innerHTML=`<img src="${src}" alt="Preview daun jagung">`;
  document.getElementById('imageStatus').innerHTML='<i class="bi bi-dot"></i> Siap diproses';
  document.getElementById('detectBtn').disabled=false;
  document.getElementById('previewBtn').disabled=false;
}

function fileFromDataUrl(dataUrl,name='camera_leaf.jpg'){
  const [meta,data]=dataUrl.split(',');
  const bin=atob(data); const arr=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);
  return new File([arr],name,{type:meta.match(/:(.*?);/)[1]});
}

function renderSymptomEvidence(details=[]){
  const list=document.getElementById('symptomList');
  const bar=document.getElementById('symptomBar');
  if(!details.length){
    list.innerHTML='<div class="text-secondary small">Bukti gejala belum tersedia.</div>';
    bar.style.width='0%';
    return;
  }
  list.innerHTML=details.map(s=>{
    const score=Number(s.score||0);
    const matched=Boolean(s.matched);
    const icon=matched?'bi-check-circle-fill':'bi-circle';
    return `<div class="symptom-item ${matched?'matched':'unmatched'}">
      <i class="bi ${icon}"></i>
      <span class="symptom-name">${s.name||s.symptom_name}</span>
      <strong class="symptom-value">${score.toFixed(0)}%</strong>
    </div>`;
  }).join('');
}

function renderResult(d){
  lastPrediction=d;
  document.getElementById('resultEmpty').classList.add('d-none');
  document.getElementById('resultContent').classList.remove('d-none');
  document.getElementById('resultDisease').textContent=CornDisease.formatDisease(d.predicted_class);
  const p=CornDisease.percent(d.confidence);
  document.getElementById('resultConfidence').textContent=p;
  document.getElementById('confidenceText').textContent=p;
  document.getElementById('confidenceBar').style.width=p;
  document.getElementById('resultModel').textContent=CornDisease.formatModel(d.model);

  const symptomScore=Number(d.symptom_score||0);
  const symptomPercent=`${symptomScore.toFixed(1)}%`;
  document.getElementById('symptomScore').textContent=symptomPercent;
  document.getElementById('symptomBar').style.width=`${Math.max(0,Math.min(100,symptomScore))}%`;
  renderSymptomEvidence(d.symptom_details || d.symptoms || []);
  document.getElementById('processingLink').href=`/processing?id=${d.id}`;
}

async function detect(){
  if(!selectedFile)return;
  const btn=document.getElementById('detectBtn');
  btn.disabled=true;
  btn.innerHTML='<span class="spinner-border spinner-border-sm me-2"></span>Memproses...';
  try{
    const fd=new FormData();
    fd.append('image',selectedFile);
    const result=await CornDisease.api('/api/prediction/',{method:'POST',body:fd});
    renderResult(result.data);
    CornDisease.toast('Deteksi dan analisis gejala berhasil disimpan.');
  }catch(e){
    CornDisease.toast(e.message,'error');
  }finally{
    btn.disabled=false;
    btn.innerHTML='<i class="bi bi-stars"></i> Deteksi Sekarang';
  }
}

document.addEventListener('DOMContentLoaded',()=>{
  const input=document.getElementById('imageInput'),drop=document.getElementById('dropzone');
  if(!input)return;
  input.addEventListener('change',()=>{selectedFile=input.files[0];if(selectedFile)setPreview(URL.createObjectURL(selectedFile));});
  ['dragenter','dragover'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('dragover')}));
  ['dragleave','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('dragover')}));
  drop.addEventListener('drop',e=>{selectedFile=e.dataTransfer.files[0];if(selectedFile){input.files=e.dataTransfer.files;setPreview(URL.createObjectURL(selectedFile));}});
  document.getElementById('detectBtn').addEventListener('click',detect);
  document.getElementById('startCamera').addEventListener('click',startCamera);
  document.getElementById('captureCamera').addEventListener('click',()=>{const url=captureCamera();if(url){selectedFile=fileFromDataUrl(url);setPreview(url);document.querySelector('[data-detect-tab="upload"]').click();stopCamera();}});
  document.querySelectorAll('[data-detect-tab]').forEach(tab=>tab.addEventListener('click',()=>{document.querySelectorAll('[data-detect-tab]').forEach(x=>x.classList.remove('active'));tab.classList.add('active');const upload=tab.dataset.detectTab==='upload';document.getElementById('uploadPane').classList.toggle('d-none',!upload);document.getElementById('cameraPane').classList.toggle('d-none',upload);}));
  document.getElementById('previewBtn').addEventListener('click',()=>{if(selectedFile)window.open(URL.createObjectURL(selectedFile),'_blank');});
});
