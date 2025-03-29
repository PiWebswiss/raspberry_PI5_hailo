import cv2
import time
import degirum as dg
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

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

# Initialize FastAPI
app = FastAPI()

# HTML client interface
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
      <head><title>AI Webcam Stream with FPS</title></head>
      <body>
        <h1>AI Webcam Stream via WebSocket with FPS</h1>
        <canvas id="canvas" width="640" height="480"></canvas>
        <script>
          const canvas = document.getElementById("canvas");
          const ctx = canvas.getContext("2d");
          const socket = new WebSocket("ws://" + location.host + "/ws");
          socket.binaryType = "blob";

          socket.onmessage = async function(event) {
            const bitmap = await createImageBitmap(event.data);
            ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
          };

          socket.onclose = () => console.log("WebSocket closed.");
        </script>
      </body>
    </html>
    """

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
        print("WebSocket disconnected")
    finally:
        cap.release()
