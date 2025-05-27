import cv2, time, subprocess, io, os
import numpy as np
from pathlib import Path
import degirum as dg
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from aiortc.contrib.media import MediaRelay
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from av.logging import set_level, ERROR
set_level(ERROR)

# Degirum configuration
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ''
device_type = "HAILORT/HAILO8L"
model_name = "yolo11n_silu_coco--640x640_quant_hailort_hailo8l_1"
model = dg.load_model(
    model_name=model_name,
    inference_host_address=inference_host_address,
    zoo_url=zoo_url,
    token=token,
    device_type=device_type
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "templates" / "static"),
    name="static",
)

relay = MediaRelay()
pcs = set()

# --- Pi Camera MJPEG Server Setup ---
def open_pi_camera():
    """Open the Pi CSI camera pipeline via libcamera."""
    pipeline = (
        "libcamerasrc ! video/x-raw,width=640,height=480 ! "
        "videoconvert ! appsink"
    )
    return cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# initialize on import
pi_cap = open_pi_camera()

def mjpeg_generator():
    """Yield MJPEG frames from the Pi camera."""
    global pi_cap
    while True:
        success, frame = pi_cap.read()
        if not success:
            pi_cap.release()
            pi_cap = open_pi_camera()
            continue
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        chunk = jpeg.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + chunk + b'\r\n'
        )

@app.get("/pi_feed")
def pi_feed():
    """Stream MJPEG from Pi camera to client."""
    return StreamingResponse(
        mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

# ── WebRTC VideoTrack that can switch source ────────────────────────────────
class PiCameraTransformTrack(VideoStreamTrack):
    """
    Reads frames from either CSI or USB, runs Hailo inference,
    overlays FPS, and yields them to WebRTC.
    """
    def __init__(self, source="csi"):
        super().__init__()
        if source == "csi":
            pipeline = (
                "libcamerasrc ! video/x-raw,width=640,height=480 ! "
                "videoconvert ! appsink"
            )
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:  # USB
            # adjust index if your USB cam is /dev/video1
            self.cap = cv2.VideoCapture(0)
        self.last_time = time.time()

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ok, frame = self.cap.read()
        if not ok:
            self.cap.release()
            self.cap = cv2.VideoCapture(0)
            ok, frame = self.cap.read()

        # AI inference + overlay
        annotated = model(frame).image_overlay
        now = time.time()
        fps = 1.0 / (now - self.last_time) if now != self.last_time else 0
        self.last_time = now
        cv2.putText(annotated, f"FPS: {fps:.1f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)

        out = VideoFrame.from_ndarray(annotated, format="bgr24")
        out.pts, out.time_base = pts, time_base
        return out

# ── Routes 
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/offer")
async def offer(request: Request):
    """
    Browser sends SDP offer + chosen camera (“csi” or “usb”) in JSON.
    We create a sendonly video transceiver, attach the PiCameraTransformTrack,
    and answer with the SDP.
    """
    data  = await request.json()
    offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    cam   = data.get("camera", "csi")

    pc = RTCPeerConnection()
    pcs.add(pc)

    # 1) Declare a send-only video transceiver
    tx = pc.addTransceiver("video", direction="sendonly")
    # 2) Replace its sender track with our camera track
    tx.sender.replaceTrack(PiCameraTransformTrack(cam))

    # 3) Complete WebRTC handshake
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    raw = await file.read()
    name_lc = file.filename.lower()

    if file.content_type.startswith("image/") or os.path.splitext(name_lc)[1] not in VIDEO_EXTS:
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Cannot decode image"}
        annotated = model(img).image_overlay
        ok, jpg = cv2.imencode(".jpg", annotated)
        if not ok:
            return {"error": "Encoding failed"}
        return StreamingResponse(io.BytesIO(jpg.tobytes()),
                                 media_type="image/jpeg")

    tmp_in = f"/dev/shm/{file.filename}"
    with open(tmp_in, "wb") as f:
        f.write(raw)
    cap = cv2.VideoCapture(tmp_in)
    if not cap.isOpened():
        os.remove(tmp_in)
        return {"error": "Cannot open video file"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp_out = "/dev/shm/output.avi"
    writer = cv2.VideoWriter(tmp_out, cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))

    prev_time = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ann = model(frame).image_overlay
        new_time = time.time()
        fps_text = f"FPS: {1/(new_time-prev_time):.0f}"
        prev_time = new_time
        cv2.putText(ann, fps_text, (20,30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0,255,0), 2)
        writer.write(ann)

    cap.release()
    writer.release()
    os.remove(tmp_in)

    mp4_path = "/dev/shm/output.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp_out,
        "-c:v", "libx264",
        "-profile:v", "baseline",
        "-preset", "veryfast",
        "-movflags", "+faststart",
        mp4_path
    ], check=True)
    os.remove(tmp_out)

    return FileResponse(
        mp4_path,
        media_type="video/mp4",
        filename="annotated.mp4"
    )
