/* ──────────────────────────  Helpers  ────────────────────────── */
const $ = sel => document.querySelector(sel);

/* Optional toast message (call toast("text")) */
function toast(msg, ms = 2400) {
  let t = $("#toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.style.cssText =
      "position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);" +
      "background:#333;color:#fff;padding:.6rem 1rem;border-radius:6px;" +
      "opacity:0;transition:.3s;";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = 1;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => (t.style.opacity = 0), ms);
}

/* ───────────────────  Elements / global refs  ────────────────── */
const startBtn    = $("#startBtn");
const endBtn      = $("#endBtn");
const camSelect   = $("#cam-select");
const remoteVideo = $("#remote");

const uploader    = $("#uploader");
const fileInput   = $("#fileInput");
const loader      = $("#loader");
const preview     = $("#resultPreview");

let pc = null;           // RTCPeerConnection instance

/* ─────────────────────  WebRTC live stream  ──────────────────── */
startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  endBtn.disabled   = false;

  // 1) build peer-connection
  pc = new RTCPeerConnection();

  // 2) tell browser we want to receive one video track
  pc.addTransceiver("video", { direction: "recvonly" });

  // 3) render incoming stream
  pc.ontrack = ({ streams }) => {
    remoteVideo.srcObject = streams[0];
    remoteVideo.play();
  };

  // 4) negotiate
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  /* Send the offer and selected camera to the server */
  const res  = await fetch("/offer", {
    method : "POST",
    headers: { "Content-Type": "application/json" },
    body   : JSON.stringify({
      sdp   : offer.sdp,
      type  : offer.type,
      camera: camSelect.value   // "csi" or "usb"
    })
  });

  if (!res.ok) {
    toast("Failed to negotiate WebRTC");
    startBtn.disabled = false;
    endBtn.disabled   = true;
    return;
  }

  const answer = await res.json();
  await pc.setRemoteDescription(answer);
});

endBtn.addEventListener("click", () => {
  if (pc) {
    pc.close();
    pc = null;
  }
  if (remoteVideo.srcObject) {
    remoteVideo.srcObject.getTracks().forEach(t => t.stop());
    remoteVideo.srcObject = null;
  }
  startBtn.disabled = false;
  endBtn.disabled   = true;
});

/* ────────────────  Drag-&-Drop file detection  ───────────────── */
uploader.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", e => {
  if (e.target.files.length) sendFile(e.target.files[0]);
});

/* Visual feedback for drag-over */
["dragenter", "dragover"].forEach(ev =>
  uploader.addEventListener(ev, e => {
    e.preventDefault();
    uploader.classList.add("drag");
  })
);

["dragleave", "drop"].forEach(ev =>
  uploader.addEventListener(ev, e => {
    if (ev !== "drop") e.preventDefault();
    uploader.classList.remove("drag");
  })
);

uploader.addEventListener("drop", e => {
  e.preventDefault();
  if (e.dataTransfer.files.length) sendFile(e.dataTransfer.files[0]);
});

/* Upload to /detect and display result */
async function sendFile(file) {
  loader.style.display  = "block";
  preview.style.display = "none";

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch("/detect", { method: "POST", body: form });
    loader.style.display = "none";

    if (!res.ok) {
      toast("Detection failed");
      return;
    }

    /* Image result */
    if (res.headers.get("content-type").startsWith("image/")) {
      const blob = await res.blob();
      preview.src = URL.createObjectURL(blob);
      preview.style.display = "block";
    } else {
      /* Video result → trigger download */
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url;
      a.download = "annotated.mp4";
      a.click();
      URL.revokeObjectURL(url);
      toast("Annotated video downloaded");
    }
  } catch (err) {
    loader.style.display = "none";
    toast("Error: " + err.message);
  }
}
