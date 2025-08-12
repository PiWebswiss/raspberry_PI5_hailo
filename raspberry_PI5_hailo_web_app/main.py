# Modified code from https://github.com/PiWebswiss/raspberry_PI5_hailo/blob/web-app/WebSocket/main.py
import time
import cv2
import degirum as dg
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
import asyncio


# Load Hailo model
## 1. Load costume model
model = dg.load_model(
    model_name="my_yolov11n", # Model name
    inference_host_address="@local",
    zoo_url="hailo_model", # link to the custom model folder
    token="",
    device_type="HAILORT/HAILO8L",
)

## 2. Load Hailo model (yolo11n)
""" model = dg.load_model(
    model_name="yolo11n_coco--640x640_quant_hailort_multidevice_1", 
    inference_host_address="@local",
    zoo_url="degirum/hailo", 
    token="",
    device_type="HAILORT/HAILO8L",
) """

# FastAPI setup
# Help : https://chatgpt.com/c/683ebaec-e754-800e-b3db-77546297fbce
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "templates" / "static")),
    name="static",
)

# Routes for index page
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



# WebSocket endpoint for real-time video streaming with FPS
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Initialize camera
    cap = cv2.VideoCapture(0)

    # Check that the camera is accessible
    # Code from : https://chatgpt.com/share/683867a8-db8c-800e-ae13-1b2fcdfee4ee
    if not cap.isOpened():
        print("⚠️  No camera detected!")
        # Reject WebSocket with proper close code
        await websocket.close(code=1003)  # 1003 = unsupported data 
        return

    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    prev_frame_time = time.time()

    # Accept the WebSocket connection
    await websocket.accept()

    try:
        while True:
            # Read a frame from the camera in a background thread
            # Code from: https://chatgpt.com/share/683867a8-db8c-800e-ae13-1b2fcdfee4ee
            # off-load the heavy work, keep the server responsive, get the result when it’s ready
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                break  # Stop if the camera failed

            # Run inference on the frame (also off the main async thread)
            # off-load the heavy work, keep the server responsive, get the result when it’s ready
            inf = await asyncio.to_thread(model, frame)
            frm = inf.image_overlay

            # Calculate and draw FPS on the frame
            #  Get the current time
            now = time.time()
            # Compute the FPS (Frames Per Second)
            # 1) (now - prev_frame_time) = time elapsed between two frames (seconds)
            # 2) 1 / elapsed_time = number of frames processed per second
            fps = 1 / (now - prev_frame_time)
            # Store the current time for the next iteration
            prev_frame_time = now
            # Draw the FPS value on the image
            cv2.putText(frm, f"FPS: {fps:.0f}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0), 2, cv2.LINE_AA)

            # Code from: https://chatgpt.com/share/68383000-066c-800e-8ae4-a21eb074307d
            # Encode the annotated frame as JPEG
            success, jpg = cv2.imencode('.jpg', frm)
            if not success:
                continue  # Skip this frame if encoding fails

            # Try to send the JPEG over WebSocket
            # Code from: https://chatgpt.com/share/68383000-066c-800e-8ae4-a21eb074307d
            try:
                await websocket.send_bytes(jpg.tobytes())
            except Exception:
                # If the client disconnected or network error → exit loop
                print("Send stopped (client disconnected?)")
                break

    finally:
        # Always release the camera
        cap.release()

        # Gracefully close the WebSocket if it's still open
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
