# Aide de chat GPT pour le code  https://chatgpt.com/share/6835809b-d67c-800e-a25a-fb28e45122e4
import time
import cv2
import degirum as dg
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# 1. Load Hailo model
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ""
device_type = "HAILORT/HAILO8L"
model_name = "yolov8n_relu6_coco--640x640_quant_hailort_hailo8l_1"

model = dg.load_model(
    model_name=model_name,
    inference_host_address=inference_host_address,
    zoo_url=zoo_url,
    token=token,
    device_type=device_type
)

# 2. FastAPI setup
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "templates" / "static")),
    name="static",
)

# 3. MJPEG generator from USB camera
def gen_frames():
    """
    Captures from USB camera (index 0), runs inference,
    overlays on-frame FPS, and yields JPEG frames.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Run Hailo inference
        inference = model(frame)
        annotated = inference.image_overlay

        # Compute on‐frame FPS
        now = time.time()
        fps = 1.0 / (now - prev_time) if now != prev_time else 0.0
        prev_time = now
        cv2.putText(
            annotated,
            f"FPS: {fps:.0f}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        # Encode to JPEG
        ok, buffer = cv2.imencode(".jpg", annotated)
        if not ok:
            continue
        frame_bytes = buffer.tobytes()

        # Yield multipart frame
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

# 4. Routes
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
