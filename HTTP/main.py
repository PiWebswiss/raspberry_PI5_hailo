import time
import cv2
import degirum as dg
import degirum_tools
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse


# 1. Set up your model
inference_host_address = "@local"
zoo_url = "degirum/hailo"
token = ''
device_type = "HAILORT/HAILO8L"
model_name = "yolov8n_relu6_coco--640x640_quant_hailort_hailo8l_1"

# Example video file
video_source = '../Ressources/example.mp4'

# Load the model
model = dg.load_model(
    model_name=model_name,
    inference_host_address=inference_host_address,
    zoo_url=zoo_url,
    token=token,
    device_type=device_type
)

# 2. FastAPI app
app = FastAPI()

# 3. Generator function: yields MJPEG frames and FPS
def gen_frames():
    """
    Loops over video frames, performs inference, adds FPS overlay, and yields frames as JPEG.
    """

    prev_frame_time = time.time()

    for inference_result in degirum_tools.predict_stream(model, video_source):
        frame = inference_result.image_overlay

        # Calculate FPS
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time

        # Overlay FPS text on frame
        fps_text = f"FPS: {fps:.0f}"
        cv2.putText(frame, fps_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2, cv2.LINE_AA)

        # Encode frame as JPEG
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            continue

        # Yield each frame in "multipart/x-mixed-replace" format
        frame = encoded_image.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



# 4. FastAPI routes
@app.get("/", response_class=HTMLResponse)
def index():
    """
    Simple HTML page that displays the streaming video in an <img> element.
    """
    return """
    <html>
      <head><title>AI Video Stream with HTTP using MJPEG </title></head>
      <body>
        <h1>AI Inference Stream with FPS</h1>
        <img src="/video_feed" width="640" />
      </body>
    </html>
    """
# 5. MJPEG stream with boundary box
@app.get("/video_feed")
def video_feed():
    """
    Returns an MJPEG stream with the AI inference overlay.
    """
    return StreamingResponse(gen_frames(), media_type='multipart/x-mixed-replace; boundary=frame')

