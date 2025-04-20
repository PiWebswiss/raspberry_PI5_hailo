/* ---------- helpers ---------- */
const $ = s => document.querySelector(s);                     // short selector

const toast = m => {                                          // 2‑s toast
  const t = $('#toast'); t.textContent = m; t.classList.add('show');
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 2400);
};


/* ---------- live stream ---------- */
$('#startBtn').onclick = () => {
  const cv = $('#liveCanvas'), ctx = cv.getContext('2d');
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType = 'blob';
  let last = performance.now();

  ws.onopen  = () => toast('Stream connected');
  ws.onerror = () => toast('WS error');
  ws.onclose = () => toast('Stream closed');

  ws.onmessage = async e => {
    ctx.drawImage(await createImageBitmap(e.data), 0, 0, cv.width, cv.height);
    const now = performance.now(); $('#fps').textContent = `${Math.round(1000/(now-last))} FPS`; last = now;
  };
};


/* ---------- drag‑&‑drop upload ---------- */
const up = $('#uploader');

function sendFile(f) {
  const fd = new FormData(); fd.append('file', f);
  toast('Uploading…');

  fetch('/detect', { method: 'POST', body: fd })
    .then(r => r.ok ? r.blob() : Promise.reject(r.statusText))
    .then(blob => {
      const url = URL.createObjectURL(blob);

      // clear previous preview
      $('#fileCard').querySelectorAll('img,video').forEach(el => el.remove());

      if (blob.type.startsWith('image/')) {           // JPEG returned
        const img = document.createElement('img');
        img.src = url;
        img.style.maxWidth = '100%';
        $('#fileCard').appendChild(img);
      } else {                                        // video/mp4 returned
        const vid = document.createElement('video');
        vid.controls = true;
        vid.src = url;
        vid.style.maxWidth = '100%';
        vid.autoplay = true;    
        $('#fileCard').appendChild(vid);
      }
      toast('Detection done');
    })
    .catch(err => toast(`Error: ${err}`));
}

/* click to browse */
up.onclick = () => {
  const i = Object.assign(document.createElement('input'), { type: 'file' });
  i.onchange = () => i.files.length && sendFile(i.files[0]);
  i.click();
};

/* drag‑drop UX */
['dragenter','dragover'].forEach(ev =>
  up.addEventListener(ev, e => { e.preventDefault(); up.classList.add('drag'); })
);
['dragleave','drop'].forEach(ev =>
  up.addEventListener(ev, e => { e.preventDefault(); up.classList.remove('drag'); })
);
up.addEventListener('drop', e => {
  if (e.dataTransfer.files.length) sendFile(e.dataTransfer.files[0]);
});
