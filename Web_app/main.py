import cv2, time, subprocess, io, os
import numpy as np
from pathlib import Path
import degirum as dg
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from aiortc.contrib.media import MediaRelay
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

### I use a WebRTC peer-to-peer (P2P) communication

# Removing warnning just use C for YUV→BGR conversion on the Pi 5
from av.logging import set_level, ERROR
set_level(ERROR)


# Degirum configuration
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ''
device_type = "HAILORT/HAILO8L"

## Models 
# - Object detection models
model_name = "yolo11n_silu_coco--640x640_quant_hailort_hailo8l_1"
# - Pose estimation model
#model_name = "yolov8n_relu6_coco_pose--640x640_quant_hailort_hailo8l_1"

# Load Degirum model
model = dg.load_model(
    model_name=model_name,
    inference_host_address=inference_host_address,
    zoo_url=zoo_url,
    token=token,
    device_type=device_type
)

BASE_DIR = Path(__file__).resolve().parent  # folder that has main.py

# Initialize FastAPI
app = FastAPI()
# Tells FastAPI that HTML file is folder called templates.
templates = Jinja2Templates(directory="templates")
# static/ folder is exposed at a URL that starts with /static/
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "templates" / "static"),
    name="static",
)

# Relay allows multiple consumers to access the same video stream without duplicating processing
relay = MediaRelay()
# Keeps track of all active peer connections for cleanup and management
pcs = set()


# Define class to run inference on the model and compute FPS.
class AITransformTrack(VideoStreamTrack):
    """
    Pulls frames from the incoming client video track,
    runs the model, and returns annotated frames.
    """
    def __init__(self, track):
        super().__init__()  
        self.track = relay.subscribe(track)
        self.track = relay.subscribe(track)
        self.last_time = time.time()
        self.fps = 0

    async def recv(self):
        frame = await self.track.recv()  # an av.VideoFrame
        img = frame.to_ndarray(format="bgr24")

        # Update FPS
        current_time = time.time()
        delta = current_time - self.last_time
        self.last_time = current_time
        self.fps = 1 / delta if delta > 0 else 0

        # Run model 
        annotated = model(img).image_overlay

        # Add FPS overlay
        text = f"FPS: {self.fps:.2f}"
        cv2.putText(annotated, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (0, 255, 0), 2, cv2.LINE_AA)

        new_frame = VideoFrame.from_ndarray(annotated, format="bgr24")
        # preserve timing
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame


# Route for main HTML client interface
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route that handel uncoming and ungoing video track
@app.post("/offer")
async def offer(request: Request):
    """
    Handle the SDP offer from the client, attach
    our AITransformTrack, and return the SDP answer.
    """
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            # wrap incoming track in our AI‑transform
            ai_track = AITransformTrack(track)
            pc.addTrack(ai_track)

    # set remote/ local descriptions
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


# Valide video format
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Route that run inference on the video of the image the use gave
@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Accepts an image **or** a video file, runs inference with Degirum,
    returns:
      • image  -> JPEG  (image/jpeg)
      • video  -> MP4   (video/mp4) 
    """
    raw = await file.read()
    name_lc  = file.filename.lower()

    # -------- case 1 :  IMAGE  ------------------------------------------
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

    # -------- case 2 :  VIDEO  ------------------------------------------
    # write uploaded bytes to a temp file in /dev/shm (RAM) so OpenCV can open it
    tmp_in_path = "/dev/shm/" + file.filename  # Directly use RAM disk for input
    with open(tmp_in_path, "wb") as tmp_in:
        tmp_in.write(raw)
    
    # Load video sent
    cap = cv2.VideoCapture(tmp_in_path)
 
    # Check is we can open it
    if not cap.isOpened():
        os.remove(tmp_in_path)
        return {"error": "Cannot open video file"}

    # Prepare temp file for the output MP4 in /dev/shm (RAM)
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tmp_out_path = "/dev/shm/" + "output.avi"  # Save output in RAM as well
    writer = cv2.VideoWriter(tmp_out_path, fourcc, fps, (width, height))
    
    # start FPS counter
    prev_frame_time = time.time()

    # Performe object detection 
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        annotated_frame = model(frame).image_overlay

        # Calculate FPS
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time

        fps_text = f"FPS: {fps:.0f}"
        cv2.putText(annotated_frame, fps_text, (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        writer.write(annotated_frame)

    cap.release()
    writer.release()
    os.remove(tmp_in_path)
    
    # Transcode AVI→MP4 with H.264 (baseline profile + faststart)
    mp4_path = "/dev/shm/" + "output.mp4"  # Output the MP4 to RAM
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tmp_out_path,
        "-c:v", "libx264",
        "-profile:v", "baseline",
        "-preset", "veryfast",
        "-movflags", "+faststart",
        mp4_path
    ], check=True)

    # Clean up the AVI
    os.remove(tmp_out_path)

    # Return the MP4 from RAM
    return FileResponse(
        mp4_path,
        media_type="video/mp4",
        filename="annotated.mp4"
    )