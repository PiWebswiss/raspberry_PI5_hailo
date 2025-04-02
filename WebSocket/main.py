import cv2
import time
import degirum as dg
import degirum_tools
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

# Model and video configuration
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ''
device_type = "HAILORT/HAILO8L"
model_name = "yolo11n_silu_coco--640x640_quant_hailort_hailo8l_1"
video_source = '../Ressources/road_trafifc.mp4'

# Load Degirum model
model = dg.load_model(
    model_name=model_name,
    inference_host_address=inference_host_address,
    zoo_url=zoo_url,
    token=token,
    device_type=device_type
)

# Create FastAPI app
app = FastAPI()

# HTML page with canvas to display WebSocket video stream
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
      <head><title>AI Video Stream via WebSocket with FPS</title></head>
      <body>
        <h1>AI Video Stream via WebSocket with FPS</h1>
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

# WebSocket endpoint for real-time video streaming with FPS
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    prev_frame_time = time.time()

    try:
        for inference_result in degirum_tools.predict_stream(model, video_source):
            frame = inference_result.image_overlay

            # Calculate and overlay FPS
            new_frame_time = time.time()
            fps = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time

            fps_text = f"FPS: {fps:.0f}"
            cv2.putText(frame, fps_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 0), 2, cv2.LINE_AA)

            # Encode frame to JPEG (you can switch to WebP by replacing '.jpg' with '.webp')
            success, encoded_image = cv2.imencode('.jpg', frame)
            if not success:
                continue

            await websocket.send_bytes(encoded_image.tobytes())

    except WebSocketDisconnect:
        pass
