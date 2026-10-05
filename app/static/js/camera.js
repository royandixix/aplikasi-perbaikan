let cameraStream=null;
const video=()=>document.getElementById('cameraVideo');
async function startCamera(){try{cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false}); video().srcObject=cameraStream; await video().play(); document.getElementById('captureCamera').disabled=false; CornDisease.toast('Kamera berhasil diaktifkan.');}catch(e){CornDisease.toast('Kamera tidak dapat diakses. Periksa izin browser dan HTTPS.','error');}}
function stopCamera(){cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null;}
function captureCamera(){if(!cameraStream)return null;const v=video(), c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0,c.width,c.height);return c.toDataURL('image/jpeg',.92);}
window.addEventListener('beforeunload',stopCamera);
