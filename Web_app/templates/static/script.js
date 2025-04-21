/* ---------- Helpers ---------- */
const $ = s => document.querySelector(s);

const toast = m => {
  const t = $('#toast');
  t.textContent = m;
  t.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => t.classList.remove('show'), 2400);
};

/* ---------- Drag‑&‑drop upload ---------- */
const up = $('#uploader');

function sendFile(file){
  const xhr = new XMLHttpRequest();
  const loader = document.getElementById('loader');

  xhr.open('POST','/detect',true);
  xhr.responseType = 'blob';

  // Remove old preview video
  document.querySelectorAll('#fileCard img, #fileCard video')
  .forEach(el => el.remove());

  // Show spinner immediately
  /// Spins while the file uploads and while the server is doing inference/encoding.
  loader.style.display = 'block';           

  xhr.onload = () => {
    // Hide when server responds
    loader.style.display = 'none';          

    if (xhr.status === 200){
      const blob = xhr.response;
      const url  = URL.createObjectURL(blob);

      // Display result
      if (blob.type.startsWith('image/')){
        const img = document.getElementById('resultPreview');
        img.src = url; img.style.display = 'block';
      } else {
        const vid = document.createElement('video');
        vid.controls = true; vid.autoplay = true; vid.src = url;
        document.getElementById('fileCard').appendChild(vid);
      }
      toast('Detection done');
    } else {
      toast(`Error: ${xhr.statusText}`);
    }
  };

  xhr.onerror = () => {
    loader.style.display = 'none';
    toast('Upload failed');
  };

  const form = new FormData();
  form.append('file', file);
  toast('Uploading…');
  xhr.send(form);
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


/* ---------- Live stream ---------- */
const startBtn    = document.getElementById('startBtn');
const endBtn      = document.getElementById('endBtn');
const localVideo  = document.getElementById('local');
const remoteVideo = document.getElementById('remote');
let pc;

startBtn.addEventListener('click', async () => {
  startBtn.disabled = true;
  endBtn.disabled   = false;

  // 1) get local camera
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  localVideo.srcObject = stream;

  // 2) create PeerConnection
  pc = new RTCPeerConnection({ iceServers: [] });

  // 3) send local track to server
  stream.getTracks().forEach(track => pc.addTrack(track, stream));

  // 4) receive remote AI‑annotated stream
  pc.ontrack = ({ streams }) => {
    remoteVideo.srcObject = streams[0];
    remoteVideo.play();
  };

  // 5) negotiate SDP
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const resp = await fetch('/offer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(offer)
  });
  const answer = await resp.json();
  await pc.setRemoteDescription(answer);
});

endBtn.addEventListener('click', () => {
  if (pc) {
    pc.getSenders().forEach(sender => sender.track.stop());
    pc.close();
    pc = null;
  }
  // stop local video
  if (localVideo.srcObject) {
    localVideo.srcObject.getTracks().forEach(t => t.stop());
    localVideo.srcObject = null;
  }
  // clear remote video
  if (remoteVideo.srcObject) {
    remoteVideo.srcObject.getTracks().forEach(t => t.stop());
    remoteVideo.srcObject = null;
  }
  startBtn.disabled = false;
  endBtn.disabled   = true;
});

