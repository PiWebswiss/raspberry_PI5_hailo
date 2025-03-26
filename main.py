import os
import cv2
import asyncio
import degirum as dg
import degirum_tools
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

# Load the model
model = dg.load_model(
    model_name="yolov8n_relu6_coco--640x640_quant_hailort_hailo8l_1",
    inference_host_address="@local",
    zoo_url="degirum/hailo",
    token='',
    device_type="HAILORT/HAILO8L"
)

video_source = os.path.expanduser('~/Desktop/test-file/store-aisle-detection.mp4')
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
      <head><title>AI Video WebSocket</title></head>
      <body>
        <h1>AI Video Stream via WebSocket</h1>
        <canvas id="canvas" width="640" height="480"></canvas>
        <script>
          const canvas = document.getElementById("canvas");
          const ctx = canvas.getContext("2d");
          const socket = new WebSocket("ws://" + location.host + "/ws");

          socket.binaryType = "blob";

          socket.onmessage = async function(event) {
            const blob = event.data;
            const bitmap = await createImageBitmap(blob);
            ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
          };

          socket.onclose = () => {
            console.log("WebSocket closed.");
          };
        </script>
      </body>
    </html>
    """


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        for inference_result in degirum_tools.predict_stream(model, video_source):
            success, encoded_image = cv2.imencode('.jpg', inference_result.image_overlay)
            if not success:
                continue
            await websocket.send_bytes(encoded_image.tobytes())
    except WebSocketDisconnect:
        print("WebSocket disconnected")
