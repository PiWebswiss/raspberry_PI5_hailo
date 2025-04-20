import cv2, time, tempfile, io, os
import numpy as np
from pathlib import Path
import degirum as dg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Degirum configuration
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ''
device_type = "HAILORT/HAILO8L"
model_name = "yolo11n_silu_coco--640x640_quant_hailort_hailo8l_1"

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


# HTML client interface
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# WebSocket for live webcam with AI inference
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Webcam initialization
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    prev_frame_time = time.time()

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame from webcam.")
                break

            # Run inference with Degirum
            inference_result = model(frame)
            annotated_frame = inference_result.image_overlay

            # Calculate FPS
            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time

            fps_text = f"FPS: {fps:.0f}"
            cv2.putText(annotated_frame, fps_text, (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Encode frame for sending
            success, encoded_image = cv2.imencode('.jpg', annotated_frame)
            if not success:
                continue

            await websocket.send_bytes(encoded_image.tobytes())

    except WebSocketDisconnect:
        pass
    finally:
        cap.release()

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Accepts an image **or** a video file, runs inference with Degirum,
    returns:
      • image  -> JPEG  (image/jpeg)
      • video  -> MP4   (video/mp4)
    """
    raw      = await file.read()
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
    # write uploaded bytes to a temp file so OpenCV can open it
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
        tmp_in.write(raw)
        tmp_in_path = tmp_in.name

    cap = cv2.VideoCapture(tmp_in_path)
    if not cap.isOpened():
        os.remove(tmp_in_path)
        return {"error": "Cannot open video file"}

    # prepare temp file for the output MP4
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tmp_out_path = tempfile.mktemp(suffix=".mp4")
    writer = cv2.VideoWriter(tmp_out_path, fourcc, fps, (width, height))

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        annotated = model(frame).image_overlay
        writer.write(annotated)

    cap.release()
    writer.release()
    os.remove(tmp_in_path)        # tidy up

    # stream the resulting MP4 back to the client
    def iterfile():
        with open(tmp_out_path, "rb") as f:
            yield from iter(lambda: f.read(8192), b"")
        os.remove(tmp_out_path)   # delete after sending

    return StreamingResponse(iterfile(), media_type="video/mp4")